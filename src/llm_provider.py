from typing import List
from vector_store import SearchResult


class RetrievalOnlyProvider:
    def answer(self, question: str, results: List[SearchResult]) -> str:
        if not results:
            return "No relevant passages found in the indexed documents."
        lines = [f'Top passages for: "{question}"\n']
        for r in results:
            loc = f"{r.chunk.source}" + (f" — {r.chunk.heading}" if r.chunk.heading else "")
            lines.append(f"[{loc}] (score {r.score:.2f})\n{r.chunk.text}\n")
        return "\n".join(lines)


class OllamaProvider:
    """
    Local generation via Ollama. Requires `ollama serve` running locally.

    temperature defaults low (0.1) rather than Ollama's usual chat default
    (~0.7-0.8). For grounded factual QA over retrieved documents, a high
    temperature increases the chance the model wanders from the actual
    retrieved text and fills gaps with plausible-sounding invention —
    exactly the failure mode that produced the fabricated SKARAB acronym
    expansion. Low temperature trades away creative phrasing (not needed
    here) for staying closer to the source material (needed here).
    """

    def __init__(self, model: str = "qwen3:14b", host: str = "http://localhost:11434",
                 temperature: float = 0.1):
        self.model = model
        self.host = host
        self.temperature = temperature

    def answer(self, question: str, results: List[SearchResult]) -> str:
        import requests

        context = "\n\n".join(
            f"[Source: {r.chunk.source}{' — ' + r.chunk.heading if r.chunk.heading else ''}]\n{r.chunk.text}"
            for r in results
        )
        prompt = (
            "You are an assistant for MeerKAT telescope operators. Answer the "
            "question using ONLY the context below. Cite the source file for "
            "each claim. If the context doesn't contain the answer, say so.\n\n"
            f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
        )
        resp = requests.post(
            f"{self.host}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": self.temperature},
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()


class ApiLlmProvider:
    def __init__(self, provider: str = None, model: str = None):
        if not provider or not model:
            raise ValueError(
                "api_llm mode requires provider/model to be set in config.yaml, "
                "and requires data-governance sign-off first — see README."
            )
        self.provider = provider
        self.model = model

    def answer(self, question: str, results: List[SearchResult]) -> str:
        raise NotImplementedError(
            "api_llm backend is intentionally not implemented until you've "
            "confirmed it's cleared to send document content externally."
        )


def build_provider(mode: str, config: dict):
    if mode == "retrieval":
        return RetrievalOnlyProvider()
    if mode == "local_llm":
        cfg = config.get("local_llm", {})
        return OllamaProvider(
            model=cfg.get("model", "qwen3:14b"),
            host=cfg.get("host", "http://localhost:11434"),
            temperature=cfg.get("temperature", 0.1),
        )
    if mode == "api_llm":
        cfg = config.get("api_llm", {})
        return ApiLlmProvider(cfg.get("provider"), cfg.get("model"))
    raise ValueError(f"Unknown mode: {mode}")
