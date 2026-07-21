import sys
from pathlib import Path

import pytest

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


def test_docx_reads_table_content(tmp_path):
    docx = pytest.importorskip("docx")
    from ingest import _read_docx

    path = tmp_path / "sample.docx"
    d = docx.Document()
    d.add_paragraph("Intro paragraph.")
    table = d.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Resource"
    table.rows[0].cells[1].text = "URL"
    row = table.add_row()
    row.cells[0].text = "Notice Board"
    row.cells[1].text = "https://internal.example/notice"
    d.save(path)

    text = _read_docx(path)
    assert "Intro paragraph." in text
    assert "Notice Board" in text
    assert "https://internal.example/notice" in text
