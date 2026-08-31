"""
cli.py

Interactive Q&A loop.

Usage (run from the project root):
    python src/cli.py
"""

from rag import RagPipeline
from jira_client import build_jira_client

def main():
    print("MeerKAT Ops Assistant — Tier 1 (RAG Q&A)")
    print("Type a question, or 'quit' to exit.\n")

    pipeline = RagPipeline()
    jira = build_jira_client(mode="live")
    while True:
        question = input("> ").strip()
        if question.lower() in ("quit", "exit"):
            break
        if not question:
            continue
        print()
        print(pipeline.ask(question))
        jira.fetch_tickets()
        print()


if __name__ == "__main__":
    main()


