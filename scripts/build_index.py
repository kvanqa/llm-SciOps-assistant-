"""
build_index.py

Reads docs/, chunks them, builds the search backend, and saves it to disk.

Usage:
    python scripts/build_index.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import yaml
from ingest import build_chunks, DOCS_DIR
from vector_store import build_backend, save_index, INDEX_PATH

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"


def main():
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    chunk_cfg = config.get("chunking", {})
    retrieval_cfg = config.get("retrieval", {})

    print(f"Loading documents from {DOCS_DIR} ...")
    chunks = build_chunks(
        DOCS_DIR,
        chunk_size=chunk_cfg.get("chunk_size", 800),
        overlap=chunk_cfg.get("chunk_overlap", 150),
    )
    print(f"Built {len(chunks)} chunks.")

    if not chunks:
        print(f"No documents found in {DOCS_DIR}. Add .md/.txt/.pdf/.docx files and re-run.")
        return

    backend = build_backend(
        retrieval_cfg.get("embedding_backend", "auto"),
        retrieval_cfg.get("embedding_model", "all-MiniLM-L6-v2"),
    )
    print(f"Fitting {backend.name} index ...")
    backend.fit(chunks)

    save_index(backend, INDEX_PATH)
    print(f"Saved index to {INDEX_PATH}")


if __name__ == "__main__":
    main()
