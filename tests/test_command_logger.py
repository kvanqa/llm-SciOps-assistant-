import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from command_logger import ShiftLogger


def test_set_tag_and_log_note(tmp_path):
    logger = ShiftLogger(log_dir=tmp_path)
    logger.set_tag("M030 pointing drift")
    logger.log_note("Confirmed encoder drift, not mechanical")

    entries = logger.read_entries()
    assert len(entries) == 2
    assert entries[0].entry_type == "tag"
    assert entries[1].entry_type == "note"
    assert entries[1].tag == "M030 pointing drift"


def test_log_command_captures_output_and_returncode(tmp_path):
    logger = ShiftLogger(log_dir=tmp_path)
    logger.set_tag("test issue")
    rc = logger.log_command(["echo", "hello from test"])

    assert rc == 0
    entries = logger.read_entries()
    command_entries = [e for e in entries if e.entry_type == "command"]
    assert len(command_entries) == 1
    assert "hello from test" in command_entries[0].output
    assert command_entries[0].returncode == 0
    assert command_entries[0].tag == "test issue"


def test_log_command_nonzero_exit_code_captured(tmp_path):
    logger = ShiftLogger(log_dir=tmp_path)
    rc = logger.log_command(["python3", "-c", "import sys; sys.exit(3)"])

    assert rc == 3
    entries = logger.read_entries()
    assert entries[-1].returncode == 3


def test_entries_persist_across_logger_instances(tmp_path):
    ShiftLogger(log_dir=tmp_path).log_note("first note")
    logger2 = ShiftLogger(log_dir=tmp_path)
    logger2.log_note("second note")

    entries = logger2.read_entries()
    assert len(entries) == 2
    assert entries[0].content == "first note"
    assert entries[1].content == "second note"


def test_tag_persists_across_separate_cli_invocations(tmp_path):
    """Regression test: each CLI call is a new process/new ShiftLogger
    instance, so the tag must be restored from the log, not just held
    in memory, or subsequent notes/commands silently lose their context."""
    ShiftLogger(log_dir=tmp_path).set_tag("M030 pointing drift")

    logger2 = ShiftLogger(log_dir=tmp_path)  # simulates the next CLI call
    logger2.log_note("Confirmed encoder drift, not mechanical")

    entries = logger2.read_entries()
    note_entry = [e for e in entries if e.entry_type == "note"][0]
    assert note_entry.tag == "M030 pointing drift"
