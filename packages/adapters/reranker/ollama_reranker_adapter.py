from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from packages.ports.reranker_port import RankedCandidate, RerankCandidate, RerankerPort

_WORD_RE = re.compile(r'[a-z0-9]+')


def _overlap_score(query: str, text: str) -> float:
    q = set(_WORD_RE.findall(query.lower()))
    t = set(_WORD_RE.findall(text.lower()))
    if not q or not t:
        return 0.0
    return len(q.intersection(t)) / max(len(q), 1)


class OllamaRerankerAdapter(RerankerPort):
    def __init__(self, *, base_url: str, model: str, timeout_seconds: int = 90) -> None:
        self._base_url = base_url.rstrip('/')
        self._model = model
        self._timeout_seconds = timeout_seconds

    def _prompt(self, query: str, candidates: list[RerankCandidate]) -> str:
        lines: list[str] = [
            'Re-rank candidate passages by relevance to the query.',
            'Return JSON only in this format:',
            '{"scores":[{"chunk_id":"...","score":0.0}]}',
            'Score range is 0.0 to 1.0.',
            f'Query: {query}',
            'Candidates:',
        ]
        for row in candidates:
            text = row.text.replace('\n', ' ').strip()
            lines.append(
                f'- chunk_id={row.chunk_id} doc={row.doc_id} page={row.page_start} '
                f'type={row.content_type} text={text[:420]}'
            )
        return '\n'.join(lines)

    def rerank(
        self,
        *,
        query: str,
        candidates: list[RerankCandidate],
        top_k: int,
    ) -> list[RankedCandidate]:
        if not query.strip() or not candidates or top_k <= 0:
            return []

        payload = {
            'model': self._model,
            'stream': False,
            'messages': [
                {'role': 'system', 'content': 'You are a strict ranking engine. Output JSON only.'},
                {'role': 'user', 'content': self._prompt(query, candidates)},
            ],
        }

        req = urllib.request.Request(
            f'{self._base_url}/api/chat',
            data=json.dumps(payload).encode('utf-8'),
            method='POST',
            headers={'Content-Type': 'application/json'},
        )

        try:
            with urllib.request.urlopen(req, timeout=self._timeout_seconds) as response:
                body = json.loads(response.read().decode('utf-8'))
            message = body.get('message', {})
            content = message.get('content', '') if isinstance(message, dict) else ''
            parsed = json.loads(content)
            rows = parsed.get('scores') if isinstance(parsed, dict) else None
            if not isinstance(rows, list):
                raise ValueError('missing scores')

            out: list[RankedCandidate] = []
            valid_ids = {row.chunk_id for row in candidates}
            for row in rows:
                if not isinstance(row, dict):
                    continue
                cid = str(row.get('chunk_id') or '')
                if cid not in valid_ids:
                    continue
                try:
                    score = float(row.get('score', 0.0))
                except (TypeError, ValueError):
                    score = 0.0
                out.append(RankedCandidate(chunk_id=cid, score=max(0.0, min(1.0, score))))

            if out:
                out.sort(key=lambda item: item.score, reverse=True)
                return out[:top_k]
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
            pass

        # Fallback to lexical overlap ranking if LLM rerank is unavailable.
        fallback = sorted(
            candidates,
            key=lambda row: (_overlap_score(query, row.text), row.base_score),
            reverse=True,
        )
        return [
            RankedCandidate(
                chunk_id=row.chunk_id,
                score=round(0.6 * _overlap_score(query, row.text) + 0.4 * row.base_score, 6),
            )
            for row in fallback[:top_k]
        ]
