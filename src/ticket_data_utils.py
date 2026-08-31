"""
ticket_date_utils.py

Deterministic date-range filtering and counting over an already-fetched
list of Ticket objects. Exists because small local LLMs are unreliable at
exact date-range arithmetic over prose, even with correct data and clear
instructions present (confirmed live: asked for tickets "between
2026-08-18 and 2026-08-21", got back one created 2026-08-22 as well).

Anything with a deterministic correct answer should be computed in code,
not asked of the model.
"""

from datetime import datetime
from typing import List


def parse_created(ticket) -> datetime:
    """Jira timestamps look like '2026-08-22T05:10:04.566+0200' — parse
    reliably regardless of the exact fractional-second/offset format."""
    raw = ticket.created
    # datetime.fromisoformat handles 'YYYY-MM-DDTHH:MM:SS.ffffff+HH:MM' in
    # Python 3.11+, but Jira's millisecond precision (3 digits, not 6) and
    # colon-less offset trip up older versions — normalize defensively.
    cleaned = raw
    if "." in cleaned:
        date_part, frac_and_offset = cleaned.split(".", 1)
        # keep only digits for the fractional part, then re-append offset
        i = 0
        while i < len(frac_and_offset) and frac_and_offset[i].isdigit():
            i += 1
        frac = frac_and_offset[:i].ljust(6, "0")[:6]
        offset = frac_and_offset[i:]
        cleaned = f"{date_part}.{frac}{offset}"
    return datetime.fromisoformat(cleaned)


def filter_by_date_range(tickets: List, start: datetime, end: datetime) -> List:
    """Returns only tickets with created timestamp in [start, end], inclusive.
    Naive/aware mismatch is handled by comparing dates only if either side
    lacks tzinfo, to avoid crashing on mixed naive/aware datetimes."""
    result = []
    for t in tickets:
        created = parse_created(t)
        s, e, c = start, end, created
        if created.tzinfo is None or start.tzinfo is None:
            s, e, c = start.replace(tzinfo=None), end.replace(tzinfo=None), created.replace(tzinfo=None)
        if s <= c <= e:
            result.append(t)
    return result


def summarize_fetch_window(tickets: List, since: datetime) -> str:
    """
    A short, explicit statement to anchor the model: exactly how many
    tickets are present and what date range they're guaranteed to span,
    since the model has repeatedly undercounted when asked to enumerate
    "all tickets in the past N days" from a text dump, even when every
    ticket present already satisfies that constraint by construction.
    """
    now = datetime.now(since.tzinfo) if since.tzinfo else datetime.now()
    return (
        f"FETCH WINDOW: exactly {len(tickets)} ticket(s) are present in the "
        f"context below. ALL of them were created between {since.isoformat()} "
        f"and {now.isoformat()} (the fetch window used) — if asked for "
        f"'tickets in the past N days' matching this window, the answer is "
        f"ALL {len(tickets)} of them, not a subset."
    )