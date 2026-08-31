"""
jira_client.py

Fetches tickets for handover citation and live Q&A context.

Ticket now carries reporter, status, assignee, description, summary, and comments —
earlier versions only had key/status/summary/created, which silently
broke any question about who reported/is-assigned-to a ticket, or what
a ticket's description/comments actually say. The raw Jira API already
returns this data when asked for via `fields=`; it just wasn't being
requested or parsed.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import re
from datetime import datetime, timedelta
import json
import os

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "example_docs" / "dummy_jira_tickets.json"


def _adf_to_text(node) -> str:
    """Flattens Atlassian Document Format (description/comment bodies) to plain text."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    parts = []

    def walk(n):
        if not isinstance(n, dict):
            return
        if n.get("type") == "text":
            parts.append(n.get("text", ""))
        for child in n.get("content", []) or []:
            walk(child)
        if n.get("type") in ("paragraph", "heading", "listItem"):
            parts.append("\n")

    walk(node)
    return "".join(parts).strip()


@dataclass
class Ticket:
    key: str
    summary: str
    status: str
    created: str
    reporter: str = ""
    assignee: str = ""
    description: str = ""
    comments: List[str] = field(default_factory=list)  # "Author: text"
    url: str = ""

    def cite(self) -> str:
        return f"[{self.key}]"

    def line(self) -> str:
        """Short one-liner — fine for a compact list, NOT enough context for
        questions about reporter/assignee/description/comments."""
        return f"{self.key} ({self.status}): {self.summary}"

    def to_context_text(self) -> str:
        """Full detail — use this (not line()) when feeding a ticket into an
        LLM prompt for Q&A, since that's the only version with reporter/
        assignee/description/comments actually present."""
        parts = [
            f"{self.key} ({self.status})",
            f"  Reporter/Creator: {self.reporter or 'Unknown'}",
            f"  Assigned To: {self.assignee or 'Unassigned'}",
            f"  Created: {self.created}",
            f"  URL: {self.url}",
            f"  Status: {self.status}",
            f"  Summary: {self.summary}",
        ]
        if self.description:
            parts.append(f"  Description: {self.description}")
        if self.comments:
            parts.append("  Activity History:")
            for c in self.comments:
                parts.append(f"    - Comment: {c}")
        return "\n".join(parts)


# class MockJiraClient:
#     def __init__(self, fixture_path: Path = FIXTURE_PATH):
#         self.fixture_path = fixture_path

#     def fetch_tickets(self, since: Optional[datetime] = None, project_key: Optional[str] = None,
#                        reporter: Optional[str] = None) -> List[Ticket]:
#         with open(self.fixture_path) as f:
#             raw = json.load(f)
#         tickets = [Ticket(**t) for t in raw]
#         if project_key:
#             tickets = [t for t in tickets if t.key.startswith(project_key)]
#         if since:
#             tickets = [t for t in tickets if datetime.fromisoformat(t.created) >= since]
#         return tickets

class LiveJiraClient:
    def __init__(self, base_url: Optional[str] = None, email: Optional[str] = None,
                 api_token: Optional[str] = None):
        self.base_url = base_url or os.environ.get("JIRA_BASE_URL")
        self.email = email or os.environ.get("JIRA_EMAIL")
        self.api_token = api_token or os.environ.get("JIRA_API_TOKEN")
        if not all([self.base_url, self.email, self.api_token]):
            raise ValueError(
                "Live Jira mode requires JIRA_BASE_URL, JIRA_EMAIL, and "
                "JIRA_API_TOKEN set as environment variables."
            )

    def _fetch_page(self, jql: str, page_size: int, next_page_token: Optional[str]) -> dict:
        import requests
        params = {
            "jql": jql,
            "maxResults": page_size,
            "fields": "summary,status,created,reporter,assignee,description,comment",
        }
        if next_page_token is not None:
            params["nextPageToken"] = next_page_token

        resp = requests.get(
            f"{self.base_url}/rest/api/3/search/jql",
            params=params,
            auth=(self.email, self.api_token),
            timeout=30,
        )
        # print("JIRA STATUS:", resp.status_code)
        # print("JIRA CONTENT-TYPE:", resp.headers.get("Content-Type"))
        # print("JIRA RESPONSE:", repr(resp.text[:1000]))

        resp.raise_for_status()
        return resp.json()

    def fetch_tickets(self, since: Optional[datetime] = None, project_key: Optional[str] = None,
                       reporter: Optional[str] = None, max_results: int = 200,
                       page_size: int = 100) -> List[Ticket]:
        jql_parts = []
        if project_key:
            jql_parts.append(f'project = "{project_key}"')
        if reporter:
            jql_parts.append(f'reporter = "{reporter}"')
        if since:
            jql_parts.append(f'created >= "{since.strftime("%Y-%m-%d %H:%M")}"')
        jql = " AND ".join(jql_parts) if jql_parts else "created >= -1d"

        tickets: List[Ticket] = []
        next_page_token: Optional[str] = None

        while len(tickets) < max_results:
            data = self._fetch_page(jql, page_size, next_page_token)
            issues = data.get("issues", [])
            if not issues:
                break

            for issue in issues:
                f_ = issue.get("fields", {})
                comment_field = f_.get("comment", {}) or {}
                comments = [
                    f"{(c.get('author') or {}).get('displayName', 'Unknown')}: {_adf_to_text(c.get('body'))}"
                    for c in comment_field.get("comments", [])
                    if _adf_to_text(c.get("body"))
                ]
                tickets.append(Ticket(
                    key=issue["key"],
                    summary=f_.get("summary", ""),
                    status=(f_.get("status") or {}).get("name", ""),
                    created=f_.get("created", ""),
                    reporter=(f_.get("reporter") or {}).get("displayName", ""),
                    assignee=(f_.get("assignee") or {}).get("displayName", ""),
                    description=_adf_to_text(f_.get("description")),
                    comments=comments,
                    url=f"{self.base_url}/browse/{issue['key']}",
                ))

            if data.get("isLast", True):
                break
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

        return tickets[:max_results]
    # def fetch_tickets(self, jql_query: Optional[str] = None, max_results: int = 20, page_size: int = 20) -> List[Ticket]:
    #     """
    #     Fetches tickets directly using an intelligent, user-targeted JQL query.
    #     Defaults to a defensive fallback if no specific query is provided.
    #     """
    #     # # 1. Base rule: If the LLM failed to make a query, fall back entirely
    #     # if not jql_query:
    #     #     jql = 'project = "OPS" AND created >= -2d ORDER BY created DESC'
    #     # else:
    #     #     jql = jql_query
            
    #     # # 2. THE FIX: Force append the 2-day window if it isn't already specified in the string
    #     # if "created >=" not in jql.lower() and "updated >=" not in jql.lower():
    #     #     # Safely inject the condition to prevent digging up old 2023 tickets
    #     #     jql = f"({jql}) AND created >= -2d"

    #     # # 3. Always ensure results are consistently sorted from newest to oldest
    #     # if "order by" not in jql.lower():
    #     #     jql += " ORDER BY created DESC"

    #     # # DEBUG: Let you verify the final stitched JQL in your server logs
    #     # print(f"[FINAL JQL SENT TO JIRA] {jql}")

    #     # If no targeted query is passed, default to a safe window to prevent accidental massive fetches
    #     jql = jql_query if jql_query else 'project = "OPS" AND created >= -3d ORDER BY created DESC'

    #     tickets: List[Ticket] = []
    #     next_page_token: Optional[str] = None

    #     while len(tickets) < max_results:
    #         data = self._fetch_page(jql, page_size, next_page_token)
    #         issues = data.get("issues", [])
    #         if not issues:
    #             break

    #         for issue in issues:
    #             f_ = issue.get("fields", {})
    #             comment_field = f_.get("comment", {}) or {}
    #             comments = [
    #                 f"{(c.get('author') or {}).get('displayName', 'Unknown')}: {_adf_to_text(c.get('body'))}"
    #                 for c in comment_field.get("comments", [])
    #                 if _adf_to_text(c.get("body"))
    #             ]
    #             tickets.append(Ticket(
    #                 key=issue["key"],
    #                 summary=f_.get("summary", ""),
    #                 status=(f_.get("status") or {}).get("name", ""),
    #                 created=f_.get("created", ""),
    #                 reporter=(f_.get("reporter") or {}).get("displayName", ""),
    #                 assignee=(f_.get("assignee") or {}).get("displayName", ""),
    #                 description=_adf_to_text(f_.get("description")),
    #                 comments=comments,
    #                 url=f"{self.base_url}/browse/{issue['key']}",
    #             ))

    #         if data.get("isLast", True):
    #             break
    #         next_page_token = data.get("nextPageToken")
    #         if not next_page_token:
    #             break

    #     return tickets[:max_results]



def build_jira_client(mode: str = "mock", **kwargs):
    # if mode == "mock":
    #     return MockJiraClient(**kwargs)
    if mode == "live":
        return LiveJiraClient(**kwargs)
    raise ValueError(f"Unknown jira mode: {mode}")

# def build_jira_query(question: str):
#     """
#     Translates natural language questions about telescope logs and dates 
#     into a structured Jira JQL query string.
#     """
#     q_lower = question.lower()
#     jql_parts = ['project = "OPS"']
    
#     # 1. HANDLE RELATIVE TIMELINES (e.g., "2 days ago")
#     relative_match = re.search(r"(\d+)\s*days?\s*ago", q_lower)
#     if relative_match:
#         days_ago = int(relative_match.group(1))
#         target_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
#         jql_parts.append(f"created >= '{target_date}'")
#         return " AND ".join(jql_parts), f"Fetching tickets created since {days_ago} days ago."

#     # 2. HANDLE ABSOLUTE DATE RANGES (e.g., "18th August 2026 to 21st August 2026")
#     # This regex catches year formats, month words, and day digits safely
#     date_matches = re.findall(r"(\d{1,2})(?:st|nd|rd|th)?\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*(\d{4})", q_lower)
    
#     if len(date_matches) >= 2:
#         # Map english month fragments to integers
#         months = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
        
#         # Parse Start Date
#         d1, m1, y1 = date_matches[0]
#         start_dt = f"{y1}-{months[m1]:02d}-{int(d1):02d}"
        
#         # Parse End Date
#         d2, m2, y2 = date_matches[1]
#         end_dt = f"{y2}-{months[m2]:02d}-{int(d2):02d}"
        
#         # In Jira, to capture the full end day completely, extend it to the start of the next day
#         end_dt_plus_one = (datetime.strptime(end_dt, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        
#         jql_parts.append(f"created >= '{start_dt}' AND created <= '{end_dt_plus_one}'")
#         return " AND ".join(jql_parts), f"Fetching tickets created between {start_dt} and {end_dt}."

#     # Fallback to standard 7-day view if no explicit dates are caught
#     jql_parts.append("created >= '-7d'")
#     return " AND ".join(jql_parts), "Fetching recent tickets from the past week."
