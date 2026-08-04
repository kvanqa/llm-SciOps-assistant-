"""
vector_store.py

Builds a local search index over document chunks and retrieves the most
relevant ones for a query. Three backends, all fully local (no data leaves
the machine):

- tfidf: scikit-learn keyword matching. Zero setup, zero downloads.
- sentence_transformers: real embeddings via a small model, downloaded once
  from Hugging Face, then runs fully offline.
- ollama: real embeddings via a locally-running Ollama model (e.g.
  nomic-embed-text) — same approach as most local RAG examples you'll see
  (e.g. LangChain+Ollama+FAISS tutorials). Requires `ollama serve` running
  and the embedding model pulled (`ollama pull nomic-embed-text`). Nothing
  leaves the machine — the HTTP call is to localhost, not the internet.

`embedding_backend: auto` in config.yaml tries sentence_transformers first
and falls back to tfidf if it's not installed. Choose `ollama` explicitly
if you want that backend, since auto-detecting a running local service
isn't as safe to assume as a missing pip package.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List
import pickle

import numpy as np

from ingest import Chunk

INDEX_PATH = Path(__file__).resolve().parents[1] / "data" / "vector_store" / "index.pkl"


@dataclass
class SearchResult:
    chunk: Chunk
    score: float


class TfidfBackend:
    name = "tfidf"

    def __init__(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.matrix = None
        self.chunks: List[Chunk] = []

    def fit(self, chunks: List[Chunk]) -> None:
        self.chunks = chunks
        self.matrix = self.vectorizer.fit_transform([c.text for c in chunks])

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        from sklearn.metrics.pairwise import cosine_similarity
        q_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(q_vec, self.matrix)[0]
        top_idx = np.argsort(scores)[::-1][:top_k]
        return [SearchResult(self.chunks[i], float(scores[i])) for i in top_idx if scores[i] > 0]


class SentenceTransformerBackend:
    name = "sentence_transformers"

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
        self.embeddings = None
        self.chunks: List[Chunk] = []

    def fit(self, chunks: List[Chunk]) -> None:
        self.chunks = chunks
        self.embeddings = self.model.encode([c.text for c in chunks], normalize_embeddings=True)

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        q_emb = self.model.encode([query], normalize_embeddings=True)[0]
        scores = self.embeddings @ q_emb
        top_idx = np.argsort(scores)[::-1][:top_k]
        return [SearchResult(self.chunks[i], float(scores[i])) for i in top_idx]


class OllamaEmbeddingBackend:
    """
    Real embeddings via a locally-running Ollama model, e.g. nomic-embed-text.
    Requires `ollama serve` running (default http://localhost:11434) and the
    model pulled beforehand: `ollama pull nomic-embed-text`.
    """
    name = "ollama"

    def __init__(self, model_name: str = "nomic-embed-text", host: str = "http://localhost:11434"):
        self.model_name = model_name
        self.host = host
        self.embeddings = None
        self.chunks: List[Chunk] = []
        # fail fast with a clear message rather than a confusing connection
        # error mid-fit if Ollama isn't running
        self._check_available()

    def _check_available(self) -> None:
        import requests
        try:
            requests.get(f"{self.host}/api/tags", timeout=3)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(
                f"Could not reach Ollama at {self.host}. Is `ollama serve` running, "
                f"and have you run `ollama pull {self.model_name}`?"
            ) from e

    def _embed(self, text: str) -> np.ndarray:
        import requests
        resp = requests.post(
            f"{self.host}/api/embeddings",
            json={"model": self.model_name, "prompt": text},
            timeout=60,
        )
        resp.raise_for_status()
        vec = np.array(resp.json()["embedding"], dtype="float32")
        return vec / (np.linalg.norm(vec) + 1e-8)  # normalize for cosine similarity via dot product

    def fit(self, chunks: List[Chunk]) -> None:
        self.chunks = chunks
        self.embeddings = np.stack([self._embed(c.text) for c in chunks])

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        q_emb = self._embed(query)
        scores = self.embeddings @ q_emb
        top_idx = np.argsort(scores)[::-1][:top_k]
        return [SearchResult(self.chunks[i], float(scores[i])) for i in top_idx]


def build_backend(backend_choice: str = "auto", model_name: str = "all-MiniLM-L6-v2"):
    if backend_choice == "tfidf":
        return TfidfBackend()
    if backend_choice == "sentence_transformers":
        return SentenceTransformerBackend(model_name)
    if backend_choice == "ollama":
        return OllamaEmbeddingBackend(model_name)
    # auto
    try:
        return SentenceTransformerBackend(model_name)
    except ImportError:
        print("[info] sentence-transformers not installed, falling back to TF-IDF (fully local either way).")
        return TfidfBackend()


def save_index(backend, path: Path = INDEX_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(backend, f)


def load_index(path: Path = INDEX_PATH):
    with open(path, "rb") as f:
        return pickle.load(f)
    
    