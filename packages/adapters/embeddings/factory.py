from __future__ import annotations

from packages.adapters.embeddings.noop_embedding_adapter import NoopEmbeddingAdapter
from packages.adapters.embeddings.ollama_embedding_adapter import OllamaEmbeddingAdapter
from packages.ports.embedding_port import EmbeddingPort


def create_embedding_adapter(
    *,
    provider: str,
    base_url: str,
    model: str,
    timeout_seconds: int = 90,
    max_retries: int = 2,
    retry_backoff_seconds: float = 1.0,
) -> EmbeddingPort:
    normalized = provider.strip().lower()
    if normalized in {'ollama', 'local'} and model.strip():
        return OllamaEmbeddingAdapter(
            base_url=base_url,
            model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
        )
    return NoopEmbeddingAdapter()
