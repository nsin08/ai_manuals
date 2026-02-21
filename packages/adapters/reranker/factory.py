from __future__ import annotations

from packages.adapters.reranker.noop_reranker_adapter import NoopRerankerAdapter
from packages.adapters.reranker.ollama_reranker_adapter import OllamaRerankerAdapter
from packages.ports.reranker_port import RerankerPort


def create_reranker_adapter(
    *,
    provider: str,
    base_url: str,
    model: str,
) -> RerankerPort:
    normalized = provider.strip().lower()
    if normalized in {'ollama', 'local'} and model.strip():
        return OllamaRerankerAdapter(base_url=base_url, model=model)
    return NoopRerankerAdapter()
