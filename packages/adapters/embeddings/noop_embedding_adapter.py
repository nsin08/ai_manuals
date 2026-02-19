from __future__ import annotations

from packages.ports.embedding_port import EmbeddingPort


class NoopEmbeddingAdapter(EmbeddingPort):
    def embed_text(self, text: str) -> list[float]:
        _ = text
        return []
