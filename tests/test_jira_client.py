import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jira_client import MockJiraClient, build_jira_client


def test_mock_client_returns_dummy_tickets():
    client = MockJiraClient()
    tickets = client.fetch_tickets()
    assert len(tickets) == 3
    keys = {t.key for t in tickets}
    assert "OPS-6338" in keys


def test_mock_client_filters_by_project_key():
    client = MockJiraClient()
    tickets = client.fetch_tickets(project_key="OPS")
    assert all(t.key.startswith("OPS") for t in tickets)


def test_mock_client_filters_by_since():
    client = MockJiraClient()
    tickets = client.fetch_tickets(since=datetime(2026, 7, 20))
    assert all(datetime.fromisoformat(t.created) >= datetime(2026, 7, 20) for t in tickets)
    assert len(tickets) == 2  # excludes the 2026-07-18 ticket


def test_ticket_cite_and_line_formatting():
    client = MockJiraClient()
    ticket = client.fetch_tickets()[0]
    assert ticket.cite() == f"[{ticket.key}]"
    assert ticket.key in ticket.line()
    assert ticket.summary in ticket.line()


def test_build_jira_client_mock_mode():
    client = build_jira_client(mode="mock")
    assert isinstance(client, MockJiraClient)


def test_build_jira_client_live_mode_requires_credentials(monkeypatch):
    import pytest
    monkeypatch.delenv("JIRA_BASE_URL", raising=False)
    monkeypatch.delenv("JIRA_EMAIL", raising=False)
    monkeypatch.delenv("JIRA_API_TOKEN", raising=False)
    with pytest.raises(ValueError):
        build_jira_client(mode="live")
