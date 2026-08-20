"""
jira_client.py

Fetches tickets created within a specific shift window (for handover
citation).

IMPORTANT — API migration (fixed after hitting this live):
Atlassian permanently removed GET /rest/api/3/search (returns 410 Gone,
fully shut down by end of October 2025). The replacement is
GET /rest/api/3/search/jql, which also changed the pagination model:
no more startAt/total — instead each response returns a nextPageToken
(opaque string) and an isLast boolean. Critically, nextPageToken must be
OMITTED ENTIRELY on the first request — passing it as null/empty causes
an "invalid or expired token" error. Only include it once you have a
real token from a previous response.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import json
import os

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "example_docs" / "dummy_jira_tickets.json"


@dataclass
class Ticket:
    key: str
    summary: str
    status: str
    created: str
    description: str = ""
    reporter: str = ""
    comments: List[str] = None  # <-- 1. Add this slot (default to None)
    url: str = ""


    def __post_init__(self):
        if self.comments is None:
            self.comments = []

    def line(self) -> str:
        # Format the comments into a clean list for Llama 3.2
        formatted_comments = "\n".join([f"    - Comment: {c}" for c in self.comments]) if self.comments else "    - No comments logged yet."
        
        return (f"{self.key} ({self.status}) | Reporter: {self.reporter}\n"
                f"  Summary: {self.summary}\n"
                f"  Description: {self.description}\n"
                f"  Activity History:\n{formatted_comments}\n")
    def cite(self) -> str:
        return f"[{self.key}]"


class MockJiraClient:
    def __init__(self, fixture_path: Path = FIXTURE_PATH):
        self.fixture_path = fixture_path

    def fetch_tickets(self, since: Optional[datetime] = None, project_key: Optional[str] = None,
                       reporter: Optional[str] = None) -> List[Ticket]:
        with open(self.fixture_path) as f:
            raw = json.load(f)
        tickets = [Ticket(**t) for t in raw]
        if project_key:
            tickets = [t for t in tickets if t.key.startswith(project_key)]
        if since:
            tickets = [t for t in tickets if datetime.fromisoformat(t.created) >= since]
        return tickets


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

    def _fetch_page(self, jql: str, page_size: int, next_page_token: Optional[str],
                     fields: str) -> dict:
        import requests
        params = {
            "jql": jql,
            "maxResults": page_size,
            "fields": fields,
        }
        # Deliberately omit nextPageToken entirely on the first request —
        # passing it as null/empty causes "invalid or expired token".
        if next_page_token is not None:
            params["nextPageToken"] = next_page_token

        resp = requests.get(
            f"{self.base_url}/rest/api/3/search/jql",
            params=params,
            auth=(self.email, self.api_token),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def fetch_tickets(self, since: Optional[datetime] = None, project_key: Optional[str] = None,
                       reporter: Optional[str] = None, max_results: int = 1000,
                       page_size: int = 50) -> List[Ticket]:
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
            data = self._fetch_page(jql, page_size, next_page_token, fields="summary,status,created")
            issues = data.get("issues", [])
            if not issues:
                break

            for issue in issues:
                fields = issue.get("fields", {})
                tickets.append(Ticket(
                    key=issue["key"],
                    summary=fields.get("summary", ""),
                    status=(fields.get("status") or {}).get("name", ""),
                    created=fields.get("created", ""),
                    url=f"{self.base_url}/browse/{issue['key']}",
                ))

            if data.get("isLast", True):
                break
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break  # defensive: isLast was false but no token given, stop rather than loop forever

        return tickets[:max_results]


def build_jira_client(mode: str = "mock", **kwargs):
    if mode == "mock":
        return MockJiraClient(**kwargs)
    if mode == "live":
        return LiveJiraClient(**kwargs)
    raise ValueError(f"Unknown jira mode: {mode}")


