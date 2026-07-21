import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingest import chunk_text


def test_chunk_text_basic():
    text = "A" * 2000
    chunks = chunk_text(text, source="test.md", chunk_size=800, overlap=150)
    assert len(chunks) > 1
    assert all(len(c.text) <= 800 for c in chunks)
    assert chunks[0].source == "test.md"


def test_chunk_text_heading_tracking():
    text = "# Section One\n\n" + ("x" * 900) + "\n\n# Section Two\n\n" + ("y" * 900)
    chunks = chunk_text(text, source="test.md", chunk_size=800, overlap=100)
    headings = {c.heading for c in chunks}
    assert "Section One" in headings
