"""
draft_generator.py

Assembles a handover note draft from three real, structured sources:
  - the shift log (what the operator actually tagged/noted/ran)
  - JIRA tickets created during the shift window
  - calendar/maintenance events active on the shift date

Deliberately NOT an LLM-generated document. Given what we've seen testing
Tier 1 — the model can fabricate a plausible-sounding but wrong answer
(the SKARAB acronym) when context is partial or adjacent rather than
completely absent — a handover note is exactly the kind of document where
that failure mode is unacceptable: someone on the next shift may act on it.

So this module only does deterministic template assembly of real data.
Ticket-to-tag matching is a simple substring heuristic, and is explicitly
labeled "possible match" rather than stated as fact, so it can't be
mistaken for a verified link. If you want an LLM to help at all, the safe
place for that is tidying the operator's OWN free-text notes into cleaner
prose — never inventing links, facts, or citations. That's not wired in
here; keeping this module's output fully deterministic and auditable.
"""

from dataclasses import dataclass
from datetime import date as date_type, datetime, time, timezone
from pathlib import Path
from typing import List, Optional

from command_logger import ShiftLogger, LogEntry
from jira_client import build_jira_client, Ticket
from calendar_client import build_calendar_client, CalendarEvent

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "handover_drafts"


@dataclass
class IssueGroup:
    tag: str
    notes: List[str]
    commands: List[LogEntry]
    possible_tickets: List[Ticket]


def _group_entries_by_tag(entries: List[LogEntry]) -> List[IssueGroup]:
    """Groups notes/commands under each tag, in the order tags first appeared."""
    order: List[str] = []
    notes_by_tag: dict = {}
    commands_by_tag: dict = {}

    for entry in entries:
        if entry.entry_type == "tag":
            continue
        tag = entry.tag or "(untagged)"
        if tag not in order:
            order.append(tag)
            notes_by_tag[tag] = []
            commands_by_tag[tag] = []
        if entry.entry_type == "note":
            notes_by_tag[tag].append(entry.content)
        elif entry.entry_type == "command":
            commands_by_tag[tag].append(entry)

    return [
        IssueGroup(tag=tag, notes=notes_by_tag[tag], commands=commands_by_tag[tag], possible_tickets=[])
        for tag in order
    ]


def _match_tickets_to_tags(groups: List[IssueGroup], tickets: List[Ticket]) -> None:
    """
    Simple substring heuristic: a ticket is a "possible match" for a tag if
    they share a significant word. This is intentionally weak and clearly
    labeled — it's a prompt for the operator to check, not an asserted fact.
    """
    for group in groups:
        tag_words = {w.lower() for w in group.tag.split() if len(w) > 3}
        for ticket in tickets:
            summary_words = {w.lower() for w in ticket.summary.split() if len(w) > 3}
            if tag_words & summary_words:
                group.possible_tickets.append(ticket)


def _render_markdown(shift_date: date_type, groups: List[IssueGroup], all_tickets: List[Ticket],
                      maintenance_events: List[CalendarEvent], antennas_in_maintenance: List[str]) -> str:
    lines = []
    lines.append(f"# Handover Note — {shift_date.isoformat()}")
    lines.append("")
    lines.append("**DRAFT — auto-assembled from shift log, JIRA, and calendar data.**")
    lines.append("**Review every section before handing over. Nothing here has been")
    lines.append("generated or paraphrased by an LLM — this is a direct assembly of")
    lines.append("what was actually logged, fetched, and scheduled.**")
    lines.append("")

    lines.append("## Antenna Availability")
    if antennas_in_maintenance:
        lines.append(f"**In maintenance today:** {', '.join(antennas_in_maintenance)}")
    else:
        lines.append("**In maintenance today:** none recorded")
    lines.append("")
    if maintenance_events:
        for e in maintenance_events:
            lines.append(f"- {e.line()} {e.cite()}" + (f" — {e.notes}" if e.notes else ""))
    lines.append("")

    lines.append("## Issues This Shift")
    if not groups:
        lines.append("No tagged issues logged this shift.")
    for g in groups:
        lines.append(f"### {g.tag}")
        for note in g.notes:
            lines.append(f"- {note}")
        if g.commands:
            lines.append("")
            lines.append("**Commands run:**")
            for c in g.commands:
                status = "OK" if c.returncode == 0 else f"exit code {c.returncode}"
                lines.append(f"- `{c.content}` ({status})")
        if g.possible_tickets:
            lines.append("")
            lines.append("**Possibly related JIRA tickets (unverified — please confirm):**")
            for t in g.possible_tickets:
                lines.append(f"- {t.line()} {t.cite()}")
        lines.append("")

    lines.append("## All JIRA Tickets This Shift Window")
    if all_tickets:
        for t in all_tickets:
            lines.append(f"- {t.line()} {t.cite()}")
    else:
        lines.append("None fetched for this window.")
    lines.append("")

    lines.append("## Outstanding Items")
    lines.append("_(operator to fill in — not inferable from logged data)_")
    lines.append("")

    return "\n".join(lines)


def generate_draft(shift_date: date_type, jira_mode: str = "mock", calendar_mode: str = "mock",
                    jira_project_key: Optional[str] = None) -> str:
    logger = ShiftLogger()
    entries = logger.read_entries(date=shift_date.isoformat())
    groups = _group_entries_by_tag(entries)

    jira_client = build_jira_client(mode=jira_mode)
    since = datetime.combine(shift_date, time.min)  # naive, matches fixture/JIRA timestamp format
    tickets = jira_client.fetch_tickets(since=since, project_key=jira_project_key)
    _match_tickets_to_tags(groups, tickets)

    calendar_client = build_calendar_client(mode=calendar_mode)
    maintenance_events = calendar_client.fetch_events(on_date=shift_date, resource_type="antenna")
    antennas_in_maintenance = calendar_client.antennas_in_maintenance(on_date=shift_date)

    return _render_markdown(shift_date, groups, tickets, maintenance_events, antennas_in_maintenance)


def save_draft(shift_date: date_type, jira_mode: str = "mock", calendar_mode: str = "mock",
               jira_project_key: Optional[str] = None) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    content = generate_draft(shift_date, jira_mode, calendar_mode, jira_project_key)
    path = OUTPUT_DIR / f"handover_{shift_date.isoformat()}.md"
    path.write_text(content)
    return path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date_type.today().isoformat())
    parser.add_argument("--jira-mode", default="mock")
    parser.add_argument("--calendar-mode", default="mock")
    parser.add_argument("--jira-project", default=None)
    args = parser.parse_args()

    shift_date = date_type.fromisoformat(args.date)
    path = save_draft(shift_date, jira_mode=args.jira_mode, calendar_mode=args.calendar_mode,
                       jira_project_key=args.jira_project)
    print(f"Saved draft to {path}")
