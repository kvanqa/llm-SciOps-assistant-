"""
vector_store.py

Builds a local search index over document chunks and retrieves the most
relevant ones for a query. Two backends, both fully local (no network calls,
no data leaves the machine):

- sentence_transformers + cosine similarity (better quality, needs the
  optional dependency and a one-time model download from Hugging Face)
- tfidf via scikit-learn (zero extra downloads, works out of the box,
  weaker on paraphrased queries but fine for keyword-heavy ops queries like
  "global sync procedure" or "indexer reset")

`embedding_backend: auto` in config.yaml tries sentence_transformers first
and falls back to tfidf if it's not installed.
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


def build_backend(backend_choice: str = "auto", model_name: str = "all-MiniLM-L6-v2"):
    if backend_choice == "tfidf":
        return TfidfBackend()
    if backend_choice == "sentence_transformers":
        return SentenceTransformerBackend(model_name)
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
