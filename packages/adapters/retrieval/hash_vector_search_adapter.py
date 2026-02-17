from __future__ import annotations

import math
import re

from packages.domain.models import Chunk
from packages.ports.keyword_search_port import ScoredChunk
from packages.ports.vector_search_port import VectorSearchPort

_TOKEN_RE = re.compile(r'[a-z0-9]+')



def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or '').lower())



def _hashed_embedding(text: str, dim: int) -> list[float]:
    vec = [0.0] * dim
    for token in _tokens(text):
        idx = hash(token) % dim
        vec[idx] += 1.0

    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec

    return [v / norm for v in vec]



def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    return sum(x * y for x, y in zip(a, b))


class HashVectorSearchAdapter(VectorSearchPort):
    """Local vector-like retrieval using hashed bag-of-words embeddings.

    This is a lightweight fallback until external embedding models are integrated.
    """

    def __init__(self, dim: int = 384) -> None:
        self._dim = dim

    def search(self, query: str, chunks: list[Chunk], top_k: int) -> list[ScoredChunk]:
        if not chunks or not query.strip() or top_k <= 0:
            return []

        q_vec = _hashed_embedding(query, self._dim)
        scored: list[ScoredChunk] = []

        for chunk in chunks:
            c_vec = _hashed_embedding(chunk.content_text, self._dim)
            score = _cosine(q_vec, c_vec)
            if score > 0:
                scored.append(ScoredChunk(chunk=chunk, score=score, source='vector'))

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]
