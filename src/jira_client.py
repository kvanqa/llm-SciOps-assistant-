"""
jira_client.py

Fetches Jira tickets for citing in handover notes / weekly summaries.

Two modes:
- mock (default): returns canned dummy tickets from a local fixture file,
  no network calls at all. Use this to build and test everything before
  Jira access + data governance are sorted out.
- live: queries a real Jira instance via REST API. Requires JIRA_BASE_URL,
  JIRA_EMAIL, JIRA_API_TOKEN (a Jira API token, not your password) set as
  environment variables — see .env.example. Never commit real credentials.
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
    url: str = ""

    def cite(self) -> str:
        """Short citation form for embedding in a handover note, e.g. [OPS-6338]."""
        return f"[{self.key}]"

    def line(self) -> str:
        return f"{self.key} ({self.status}): {self.summary}"


class MockJiraClient:
    """Returns canned tickets from a local JSON fixture. No network calls."""

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
    """Queries a real Jira Cloud instance. Requires credentials as env vars."""

    def __init__(self, base_url: Optional[str] = None, email: Optional[str] = None,
                 api_token: Optional[str] = None):
        self.base_url = base_url or os.environ.get("JIRA_BASE_URL")
        self.email = email or os.environ.get("JIRA_EMAIL")
        self.api_token = api_token or os.environ.get("JIRA_API_TOKEN")
        if not all([self.base_url, self.email, self.api_token]):
            raise ValueError(
                "Live Jira mode requires JIRA_BASE_URL, JIRA_EMAIL, and "
                "JIRA_API_TOKEN set as environment variables. See .env.example. "
                "Do not enable live mode until this is cleared for your data."
            )

    def fetch_tickets(self, since: Optional[datetime] = None, project_key: Optional[str] = None,
                       reporter: Optional[str] = None) -> List[Ticket]:
        import requests

        jql_parts = []
        if project_key:
            jql_parts.append(f'project = "{project_key}"')
        if reporter:
            jql_parts.append(f'reporter = "{reporter}"')
        if since:
            jql_parts.append(f'created >= "{since.strftime("%Y-%m-%d %H:%M")}"')
        jql = " AND ".join(jql_parts) if jql_parts else "created >= -1d"

        resp = requests.get(
            f"{self.base_url}/rest/api/3/search",
            params={"jql": jql, "fields": "summary,status,created"},
            auth=(self.email, self.api_token),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            Ticket(
                key=issue["key"],
                summary=issue["fields"]["summary"],
                status=issue["fields"]["status"]["name"],
                created=issue["fields"]["created"],
                url=f"{self.base_url}/browse/{issue['key']}",
            )
            for issue in data.get("issues", [])
        ]


def build_jira_client(mode: str = "mock", **kwargs):
    if mode == "mock":
        return MockJiraClient(**kwargs)
    if mode == "live":
        return LiveJiraClient(**kwargs)
    raise ValueError(f"Unknown jira mode: {mode}")
