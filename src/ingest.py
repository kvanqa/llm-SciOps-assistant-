"""
ingest.py

Loads documents from docs/ (.md, .txt, .pdf, .docx) and splits them into
overlapping chunks for retrieval. Each chunk keeps track of its source file
and a rough section/position so answers can cite where they came from.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List

DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"


@dataclass
class Chunk:
    text: str
    source: str        # filename
    chunk_index: int    # position within the source file
    heading: str = ""   # nearest preceding markdown heading, if any


def _read_txt_or_md(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise ImportError("Install pypdf to read PDF files: pip install pypdf") from e
    reader = PdfReader(str(path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def _read_docx(path: Path) -> str:
    try:
        import docx
    except ImportError as e:
        raise ImportError("Install python-docx to read .docx files: pip install python-docx") from e
    d = docx.Document(str(path))
    return "\n\n".join(p.text for p in d.paragraphs)


READERS = {
    ".md": _read_txt_or_md,
    ".txt": _read_txt_or_md,
    ".pdf": _read_pdf,
    ".docx": _read_docx,
}


def load_documents(docs_dir: Path = DOCS_DIR) -> List[tuple[str, str]]:
    """Returns list of (filename, full_text) for every supported file in docs_dir."""
    results = []
    for path in sorted(docs_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in READERS:
            try:
                text = READERS[path.suffix.lower()](path)
                if text.strip():
                    results.append((path.name, text))
            except Exception as e:
                print(f"[warn] skipping {path.name}: {e}")
    return results


def _nearest_heading(text_before: str) -> str:
    """Find the last markdown heading appearing before this point in the text."""
    lines = [l for l in text_before.splitlines() if l.strip().startswith("#")]
    return lines[-1].lstrip("#").strip() if lines else ""


def chunk_text(text: str, source: str, chunk_size: int = 800, overlap: int = 150) -> List[Chunk]:
    """Simple sliding-window chunking over characters, with heading tracking."""
    chunks = []
    start = 0
    idx = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        piece = text[start:end].strip()
        if piece:
            heading = _nearest_heading(text[:start])
            chunks.append(Chunk(text=piece, source=source, chunk_index=idx, heading=heading))
            idx += 1
        start += chunk_size - overlap
    return chunks


def build_chunks(docs_dir: Path = DOCS_DIR, chunk_size: int = 800, overlap: int = 150) -> List[Chunk]:
    all_chunks: List[Chunk] = []
    for filename, text in load_documents(docs_dir):
        all_chunks.extend(chunk_text(text, filename, chunk_size, overlap))
    return all_chunks


if __name__ == "__main__":
    chunks = build_chunks()
    print(f"Loaded {len(chunks)} chunks from {DOCS_DIR}")
    for c in chunks[:3]:
        print(f"--- {c.source} [{c.heading}] chunk {c.chunk_index} ---")
        print(c.text[:200], "...\n")
