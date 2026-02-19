from __future__ import annotations

import json
import urllib.error
import urllib.request

from packages.ports.embedding_port import EmbeddingPort


class OllamaEmbeddingAdapter(EmbeddingPort):
    def __init__(self, *, base_url: str, model: str, timeout_seconds: int = 30) -> None:
        self._base_url = base_url.rstrip('/')
        self._model = model
        self._timeout_seconds = timeout_seconds

    def _post_json(self, endpoint: str, payload: dict[str, object]) -> dict[str, object]:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            f'{self._base_url}{endpoint}',
            data=data,
            method='POST',
            headers={'Content-Type': 'application/json'},
        )
        with urllib.request.urlopen(req, timeout=self._timeout_seconds) as response:
            return json.loads(response.read().decode('utf-8'))

    def embed_text(self, text: str) -> list[float]:
        value = (text or '').strip()
        if not value:
            return []

        try:
            # Backward-compatible endpoint.
            body = self._post_json('/api/embeddings', {'model': self._model, 'prompt': value})
            embedding = body.get('embedding', [])
            if isinstance(embedding, list):
                return [float(x) for x in embedding]
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
            pass

        try:
            # Newer endpoint.
            body = self._post_json('/api/embed', {'model': self._model, 'input': value})
            embeddings = body.get('embeddings', [])
            if isinstance(embeddings, list) and embeddings:
                first = embeddings[0]
                if isinstance(first, list):
                    return [float(x) for x in first]
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
            pass

        return []
