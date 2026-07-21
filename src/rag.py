"""
rag.py

Ties ingestion, retrieval, and generation together.
"""

from pathlib import Path
import yaml

from vector_store import build_backend, load_index, INDEX_PATH
from llm_provider import build_provider

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


class RagPipeline:
    def __init__(self, config: dict | None = None):
        self.config = config or load_config()
        self.backend = load_index(INDEX_PATH)
        self.provider = build_provider(self.config["mode"], self.config)
        self.top_k = self.config.get("retrieval", {}).get("top_k", 5)

    def ask(self, question: str) -> str:
        results = self.backend.search(question, top_k=self.top_k)
        return self.provider.answer(question, results)
