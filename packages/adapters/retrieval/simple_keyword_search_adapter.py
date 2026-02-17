from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

from packages.domain.models import Chunk
from packages.ports.keyword_search_port import KeywordSearchPort, ScoredChunk

_TOKEN_RE = re.compile(r'[a-z0-9]+')



def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or '').lower())


class SimpleKeywordSearchAdapter(KeywordSearchPort):
    """BM25-like lexical scoring over in-memory chunks."""

    def __init__(self, k1: float = 1.2, b: float = 0.75) -> None:
        self._k1 = k1
        self._b = b

    def search(self, query: str, chunks: list[Chunk], top_k: int) -> list[ScoredChunk]:
        if not chunks or not query.strip() or top_k <= 0:
            return []

        q_terms = _tokens(query)
        if not q_terms:
            return []

        docs_tokens = [_tokens(ch.content_text) for ch in chunks]
        doc_lens = [len(toks) for toks in docs_tokens]
        avg_len = sum(doc_lens) / max(len(doc_lens), 1)

        df: dict[str, int] = defaultdict(int)
        for toks in docs_tokens:
            for term in set(toks):
                df[term] += 1

        n_docs = len(chunks)
        scored: list[ScoredChunk] = []

        for chunk, toks, doc_len in zip(chunks, docs_tokens, doc_lens):
            tf = Counter(toks)
            score = 0.0

            for term in q_terms:
                if term not in tf:
                    continue

                # Smoothed IDF.
                idf = math.log(1 + (n_docs - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5))
                num = tf[term] * (self._k1 + 1)
                den = tf[term] + self._k1 * (1 - self._b + self._b * (doc_len / max(avg_len, 1e-9)))
                score += idf * (num / max(den, 1e-9))

            if score > 0:
                scored.append(ScoredChunk(chunk=chunk, score=score, source='keyword'))

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]
