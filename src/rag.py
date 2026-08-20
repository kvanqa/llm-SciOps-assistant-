"""
rag.py

Ties ingestion, retrieval, and generation together.
"""

import os
from pathlib import Path
import sys
import yaml

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from chroma_backend import SKAChromaManager 
# from vector_store import build_backend, load_index, INDEX_PATH
from llm_provider import build_provider

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)

    # Create a tiny mock class
class MockChunkObject:
    def __init__(self, text, source, heading=None):
        self.text = text
        self.source = source
        self.heading = heading

class MockResultObject:
    def __init__(self, text, source, heading=None):
        # This replicates the exact structure 'r.chunk.source', 'r.chunk.text' etc.
        self.chunk = MockChunkObject(text, source, heading)

class RagPipeline:
    def __init__(self, config: dict | None = None):
        self.config = config or load_config()
        self.db = SKAChromaManager()
        self.provider = build_provider(self.config["mode"], self.config)
        self.top_k = self.config.get("retrieval", {}).get("top_k", 5)

    # Inside your RagPipeline Class:
    def ask(self, question: str, target_collection: str = "ops_docs") -> str:
        # 1. Query your isolated Chroma collection
        raw_results = self.db.query_collection(
            collection_name=target_collection,
            query_text=question,
            n_results=self.top_k
        )
        
        # 2. Build mock objects that match your old vector_store schema exactly
        legacy_formatted_results = []
        
        if raw_results and "documents" in raw_results and raw_results["documents"]:
            # Chroma nested arrays always wrap the elements inside an outer list [ [elements] ]
            documents_list = raw_results["documents"][0]  # Extract inner list
            metadatas_list = raw_results["metadatas"][0] if raw_results.get("metadatas") else []
            
            for i, chunk_text in enumerate(documents_list):
                meta = metadatas_list[i] if i < len(metadatas_list) else {}
                
                source_info = meta.get("source", "Unknown File")
                heading_info = meta.get("heading", None)  # Fallback gracefully if headings don't exist yet
                
                # Wrap the string in our mock result class
                mocked_r = MockResultObject(text=chunk_text, source=source_info, heading=heading_info)
                legacy_formatted_results.append(mocked_r)

        # 3. Pass the mocked object array right back into your existing provider layout
        return self.provider.answer(question, legacy_formatted_results)
