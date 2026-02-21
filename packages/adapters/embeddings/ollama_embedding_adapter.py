from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from packages.ports.embedding_port import EmbeddingPort


class OllamaEmbeddingAdapter(EmbeddingPort):
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: int = 90,
        max_retries: int = 2,
        retry_backoff_seconds: float = 1.0,
    ) -> None:
        self._base_url = base_url.rstrip('/')
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_retries = max(0, int(max_retries))
        self._retry_backoff_seconds = max(0.0, float(retry_backoff_seconds))
        self._last_error: str | None = None

    @property
    def last_error(self) -> str | None:
        return self._last_error

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
            self._last_error = 'empty-input'
            return []

        self._last_error = None
        attempts = self._max_retries + 1
        for attempt in range(attempts):
            legacy_error: str | None = None
            try:
                # Backward-compatible endpoint.
                body = self._post_json('/api/embeddings', {'model': self._model, 'prompt': value})
                embedding = body.get('embedding', [])
                if isinstance(embedding, list):
                    parsed = [float(x) for x in embedding]
                    if parsed:
                        self._last_error = None
                        return parsed
                legacy_error = 'legacy-endpoint-empty-embedding'
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
                legacy_error = f'legacy-endpoint-error: {exc}'

            current_error: str | None = None
            try:
                # Newer endpoint.
                body = self._post_json('/api/embed', {'model': self._model, 'input': value})
                embeddings = body.get('embeddings', [])
                if isinstance(embeddings, list) and embeddings:
                    first = embeddings[0]
                    if isinstance(first, list):
                        parsed = [float(x) for x in first]
                        if parsed:
                            self._last_error = None
                            return parsed
                current_error = 'current-endpoint-empty-embedding'
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
                current_error = f'current-endpoint-error: {exc}'

            if current_error and legacy_error:
                self._last_error = f'{legacy_error}; {current_error}'
            else:
                self._last_error = current_error or legacy_error or 'unknown-embedding-error'

            if attempt < attempts - 1 and self._retry_backoff_seconds > 0:
                time.sleep(self._retry_backoff_seconds * (2 ** attempt))

        return []
