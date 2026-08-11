import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from command_logger import LogEntry
from jira_client import Ticket
from draft_generator import _group_entries_by_tag, _match_tickets_to_tags, _render_markdown
from datetime import date


def make_entries():
    return [
        LogEntry(timestamp="t1", entry_type="tag", tag="M030 pointing drift", content="Context set"),
        LogEntry(timestamp="t2", entry_type="note", tag="M030 pointing drift", content="Confirmed encoder drift"),
        LogEntry(timestamp="t3", entry_type="command", tag="M030 pointing drift", content="check_status.py",
                  output="drift 0.3deg", returncode=0),
        LogEntry(timestamp="t4", entry_type="tag", tag="SDP blank panel", content="Context set"),
        LogEntry(timestamp="t5", entry_type="note", tag="SDP blank panel", content="Restarted service"),
    ]


def test_group_entries_by_tag_preserves_order_and_content():
    groups = _group_entries_by_tag(make_entries())
    assert [g.tag for g in groups] == ["M030 pointing drift", "SDP blank panel"]
    assert groups[0].notes == ["Confirmed encoder drift"]
    assert len(groups[0].commands) == 1
    assert groups[0].commands[0].returncode == 0
    assert groups[1].notes == ["Restarted service"]


def test_group_entries_untagged_bucket():
    entries = [LogEntry(timestamp="t1", entry_type="note", tag="", content="no tag set")]
    groups = _group_entries_by_tag(entries)
    assert groups[0].tag == "(untagged)"


def test_match_tickets_to_tags_finds_word_overlap():
    groups = _group_entries_by_tag(make_entries())
    tickets = [
        Ticket(key="OPS-1", summary="SDP signal display intermittent blank panel", status="Open", created="2026-01-01"),
        Ticket(key="OPS-2", summary="Unrelated network switch replacement", status="Open", created="2026-01-01"),
    ]
    _match_tickets_to_tags(groups, tickets)
    sdp_group = [g for g in groups if g.tag == "SDP blank panel"][0]
    m030_group = [g for g in groups if g.tag == "M030 pointing drift"][0]
    assert len(sdp_group.possible_tickets) == 1
    assert sdp_group.possible_tickets[0].key == "OPS-1"
    assert len(m030_group.possible_tickets) == 0  # no word overlap, correctly no false match


def test_render_markdown_contains_draft_warning_and_sections():
    groups = _group_entries_by_tag(make_entries())
    md = _render_markdown(date(2026, 7, 22), groups, [], [], [])
    assert "DRAFT" in md
    assert "not been" not in md  # sanity: didn't accidentally break the disclaimer wording
    assert "## Antenna Availability" in md
    assert "## Issues This Shift" in md
    assert "## Outstanding Items" in md
    assert "M030 pointing drift" in md
