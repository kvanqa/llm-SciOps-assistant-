"""
oplog.py

Command-line entry point for the shift logger.

Usage (run from the project root):
    python src/oplog.py tag "M030 pointing drift"
    python src/oplog.py note "Confirmed encoder drift, not mechanical"
    python src/oplog.py run -- python check_status.py --antenna m030
    python src/oplog.py show
"""

import argparse
import sys

from command_logger import ShiftLogger


def main():
    parser = argparse.ArgumentParser(prog="oplog")
    sub = parser.add_subparsers(dest="action", required=True)

    tag_p = sub.add_parser("tag", help="Set the current issue context")
    tag_p.add_argument("text")

    note_p = sub.add_parser("note", help="Log a free-text note")
    note_p.add_argument("text")

    run_p = sub.add_parser("run", help="Run and log a command")
    run_p.add_argument("command", nargs=argparse.REMAINDER)

    sub.add_parser("show", help="Print today's log entries")

    args = parser.parse_args()
    logger = ShiftLogger()

    if args.action == "tag":
        logger.set_tag(args.text)
        print(f"[oplog] context set: {args.text}")
    elif args.action == "note":
        logger.log_note(args.text)
        print("[oplog] note logged")
    elif args.action == "run":
        command = args.command
        if command and command[0] == "--":
            command = command[1:]
        if not command:
            print("Usage: oplog run -- <command>", file=sys.stderr)
            sys.exit(1)
        rc = logger.log_command(command)
        sys.exit(rc)
    elif args.action == "show":
        entries = logger.read_entries()
        if not entries:
            print("No entries logged today.")
        for entry in entries:
            tag_str = f"[{entry.tag}] " if entry.tag else ""
            print(f"{entry.timestamp} {tag_str}({entry.entry_type}) {entry.content}")


if __name__ == "__main__":
    main()
