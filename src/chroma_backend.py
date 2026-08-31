# src/chroma_backend.py
import chromadb
import requests
from chromadb.api.types import Documents, Embeddings

class OllamaEmbeddingFunction(chromadb.EmbeddingFunction):
    def __init__(self, model_name: str = "nomic-embed-text", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = f"{base_url.rstrip('/')}/api/embeddings"

    def _get_embedding(self, text: str) -> list[float]:
        try:
            response = requests.post(
                self.base_url, 
                json={"model": self.model_name, "prompt": text},
                timeout=60
            )
            response.raise_for_status()
            return response.json()["embedding"]
        except Exception as e:
            raise RuntimeError(f"Ollama connection failed: {e}")

    def __call__(self, input: Documents) -> Embeddings:
        return [self._get_embedding(text) for text in input]

class SKAChromaManager:
    def __init__(self, db_path: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=db_path)
        self.embedding_function = OllamaEmbeddingFunction()
        self.ops_collection = self._get_or_create_collection("ops_docs")
        self.icd_collection = self._get_or_create_collection("engineering_icd")

    def _get_or_create_collection(self, name: str):
        return self.client.get_or_create_collection(
            name=name,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}
        )

    def ingest_documents(self, collection_name: str, chunks: list[dict]):
        collection = self.ops_collection if collection_name == "ops_docs" else self.icd_collection
        ids = [chunk["id"] for chunk in chunks]
        documents = [chunk["text"] for chunk in chunks]
        metadatas = [{"source": chunk["source"]} for chunk in chunks]
        
        if ids:
            try:
                collection.delete(ids=ids)
            except Exception:
                pass 
            collection.add(ids=ids, documents=documents, metadatas=metadatas)

    def query_collection(self, collection_name: str, query_text: str, n_results: int = 3) -> dict:
        collection = self.ops_collection if collection_name == "ops_docs" else self.icd_collection
        return collection.query(query_texts=[query_text], n_results=n_results)
