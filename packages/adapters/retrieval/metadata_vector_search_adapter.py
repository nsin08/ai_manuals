from __future__ import annotations

import math

from packages.domain.models import Chunk
from packages.ports.embedding_port import EmbeddingPort
from packages.ports.keyword_search_port import ScoredChunk
from packages.ports.vector_search_port import VectorSearchPort


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def _normalize(vec: list[float]) -> list[float]:
    if not vec:
        return []
    norm = math.sqrt(sum(v * v for v in vec))
    if norm <= 0:
        return []
    return [v / norm for v in vec]


class MetadataVectorSearchAdapter(VectorSearchPort):
    """Vector search using embeddings stored in chunk metadata.

    Expected metadata format:
      chunk.metadata['embedding'] -> list[float]
    """

    def __init__(self, embedding_adapter: EmbeddingPort) -> None:
        self._embedding_adapter = embedding_adapter

    def search(self, query: str, chunks: list[Chunk], top_k: int) -> list[ScoredChunk]:
        if not query.strip() or not chunks or top_k <= 0:
            return []

        q_vec = _normalize(self._embedding_adapter.embed_text(query))
        if not q_vec:
            return []

        scored: list[ScoredChunk] = []
        for chunk in chunks:
            embedding = chunk.metadata.get('embedding') if isinstance(chunk.metadata, dict) else None
            if not isinstance(embedding, list) or not embedding:
                continue
            try:
                c_vec = _normalize([float(x) for x in embedding])
            except (TypeError, ValueError):
                continue
            if not c_vec:
                continue
            score = _cosine(q_vec, c_vec)
            if score > 0:
                scored.append(ScoredChunk(chunk=chunk, score=score, source='vector'))

        scored.sort(key=lambda row: row.score, reverse=True)
        return scored[:top_k]
