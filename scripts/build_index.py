"""
build_index.py

Reads docs/, chunks them, builds the search backend, and saves it to disk.

Usage:
    python scripts/build_index.py
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import yaml
from ingest import build_chunks, DOCS_DIR
#from vector_store import build_backend, save_index, INDEX_PATH

# ADDED: Import new Chroma manager from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.chroma_backend import SKAChromaManager
CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"


def main():
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    chunk_cfg = config.get("chunking", {})
    # Note: embedding_backend config is now handled via the Ollama wrapper in chroma_backend

    # Define paths to your separated subfolders
    ops_dir = Path(DOCS_DIR) / "ops"
    icd_dir = Path(DOCS_DIR) / "icd"
    # print the number and the names of docs found in ops
    print(f"Found {len(list(ops_dir.glob('*.docx')))} operations docs: {[p.name for p in ops_dir.glob('*.docx')]}")
    #retrieval_cfg = config.get("retrieval", {})

    # Initialize your new ChromaDB backend manager
    db = SKAChromaManager()

    # --- 1. PROCESS OPERATIONS DOCUMENTS ---
    print(f"Loading Operations documents from {ops_dir} ...")
    if ops_dir.exists():
        ops_chunks = build_chunks(
            ops_dir,
            chunk_size=chunk_cfg.get("chunk_size", 800),
            overlap=chunk_cfg.get("chunk_overlap", 150),
        )
        print(f"Built {len(ops_chunks)} operations chunks.")
        
        # Format chunks into the structure Chroma expects
        # (Assuming your build_chunks returns objects with .text, .id, and .source attributes)
        chroma_ops_format = [
            {"id": getattr(c, "id", f"ops_{i}"), "text": c.text, "source": getattr(c, "source", "unknown")}
            for i, c in enumerate(ops_chunks)
        ]
 
        if chroma_ops_format:
            print("Ingesting into ops_docs collection...")
            db.ingest_documents("ops_docs", chroma_ops_format)
    else:
        print(f"Skipping ops: Directory {ops_dir} does not exist.")

    # --- 2. PROCESS ENGINEERING / ICD DOCUMENTS ---
    print(f"Loading Engineering/ICD documents from {icd_dir} ...")
    if icd_dir.exists():
        icd_chunks = build_chunks(
            icd_dir,
            chunk_size=chunk_cfg.get("chunk_size", 800),
            overlap=chunk_cfg.get("chunk_overlap", 150),
        )
        print(f"Built {len(icd_chunks)} engineering/ICD chunks.")
        
        chroma_icd_format = [
            {"id": getattr(c, "id", f"icd_{i}"), "text": c.text, "source": getattr(c, "source", "unknown")}
            for i, c in enumerate(icd_chunks)
        ]
        
        if chroma_icd_format:
            print("Ingesting into engineering_icd collection...")
            db.ingest_documents("engineering_icd", chroma_icd_format)
    else:
        print(f"Skipping ICD: Directory {icd_dir} does not exist.")

    print("\nChromaDB index build complete with rigid domain isolation!")


if __name__ == "__main__":
    main()
