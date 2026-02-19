from __future__ import annotations

from packages.adapters.embeddings.noop_embedding_adapter import NoopEmbeddingAdapter
from packages.adapters.embeddings.ollama_embedding_adapter import OllamaEmbeddingAdapter
from packages.ports.embedding_port import EmbeddingPort


def create_embedding_adapter(
    *,
    provider: str,
    base_url: str,
    model: str,
) -> EmbeddingPort:
    normalized = provider.strip().lower()
    if normalized == 'ollama' and model.strip():
        return OllamaEmbeddingAdapter(base_url=base_url, model=model)
    return NoopEmbeddingAdapter()
