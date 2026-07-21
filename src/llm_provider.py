"""
llm_provider.py

Pluggable answer-generation backend. The default is retrieval-only — no LLM
call, just the ranked passages. This keeps everything local and safe to use
before any data-governance sign-off. Two opt-in backends exist for later:

- local_llm: calls a locally-running Ollama model. Nothing leaves the machine.
- api_llm: calls an external API. Intentionally requires an explicit,
  non-default config change plus filling in real provider/model values —
  see config.yaml and the README's "Data governance" section before using.
"""

from typing import List
from vector_store import SearchResult


class RetrievalOnlyProvider:
    """No generation — just formats the retrieved passages with citations."""

    def answer(self, question: str, results: List[SearchResult]) -> str:
        if not results:
            return "No relevant passages found in the indexed documents."
        lines = [f'Top passages for: "{question}"\n']
        for r in results:
            loc = f"{r.chunk.source}" + (f" — {r.chunk.heading}" if r.chunk.heading else "")
            lines.append(f"[{loc}] (score {r.score:.2f})\n{r.chunk.text}\n")
        return "\n".join(lines)


class OllamaProvider:
    """Local generation via Ollama. Requires `ollama serve` running locally."""

    def __init__(self, model: str = "llama3", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host

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
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()


class ApiLlmProvider:
    """
    External API generation. Disabled unless explicitly configured.
    Do not point this at any provider until data governance has confirmed
    that document content may leave the local machine.
    """

    def __init__(self, provider: str | None, model: str | None):
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
        return OllamaProvider(model=cfg.get("model", "llama3"), host=cfg.get("host", "http://localhost:11434"))
    if mode == "api_llm":
        cfg = config.get("api_llm", {})
        return ApiLlmProvider(cfg.get("provider"), cfg.get("model"))
    raise ValueError(f"Unknown mode: {mode}")
