"""
command_logger.py

Lightweight shift logger: lets an operator tag what issue they're working on,
log free-text notes, and log commands (with captured output) run while
troubleshooting. Writes timestamped JSONL entries to a local per-day log
file — nothing leaves the machine, nothing is sent to any API.

Use via the CLI (see src/oplog.py) or import ShiftLogger directly.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import json
import subprocess
import sys

LOG_DIR = Path(__file__).resolve().parents[1] / "data" / "shift_logs"


@dataclass
class LogEntry:
    timestamp: str
    entry_type: str        # "tag" | "note" | "command"
    tag: str                 # current issue context at time of entry
    content: str               # note text, or command string
    output: str = ""           # captured stdout/stderr for command entries
    returncode: Optional[int] = None


class ShiftLogger:
    def __init__(self, log_dir: Path = LOG_DIR):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_tag = self._restore_current_tag()

    def _restore_current_tag(self) -> str:
        """Each CLI invocation is a separate process, so the in-memory tag
        set by a previous `oplog tag ...` call is gone by the time the next
        `oplog note ...` call runs. Restore it from the most recent 'tag'
        entry already written to today's log."""
        for entry in reversed(self.read_entries()):
            if entry.entry_type == "tag":
                return entry.tag
        return ""

    def _log_path(self) -> Path:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.log_dir / f"{today}.jsonl"

    def _write(self, entry: LogEntry) -> None:
        with open(self._log_path(), "a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")

    def set_tag(self, tag: str) -> None:
        """Sets the current issue context. Subsequent notes/commands are
        tagged with this until changed again — this is what lets the draft
        generator group commands under the issue they relate to."""
        self.current_tag = tag
        self._write(LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            entry_type="tag", tag=tag, content=f"Context set to: {tag}",
        ))

    def log_note(self, text: str) -> None:
        self._write(LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            entry_type="note", tag=self.current_tag, content=text,
        ))

    def log_command(self, command: List[str]) -> int:
        """Runs `command`, streams its output to the terminal as normal,
        and also captures it into the shift log. Returns the exit code."""
        proc = subprocess.run(command, capture_output=True, text=True)

        if proc.stdout:
            print(proc.stdout, end="")
        if proc.stderr:
            print(proc.stderr, end="", file=sys.stderr)

        self._write(LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            entry_type="command", tag=self.current_tag,
            content=" ".join(command),
            output=(proc.stdout + proc.stderr)[-2000:],  # cap stored output size
            returncode=proc.returncode,
        ))
        return proc.returncode

    def read_entries(self, date: Optional[str] = None) -> List[LogEntry]:
        path = (self.log_dir / f"{date}.jsonl") if date else self._log_path()
        if not path.exists():
            return []
        entries = []
        with open(path) as f:
            for line in f:
                if line.strip():
                    entries.append(LogEntry(**json.loads(line)))
        return entries
