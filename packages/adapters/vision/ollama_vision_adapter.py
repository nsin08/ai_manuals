from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request

from packages.ports.vision_port import VisionPort


class OllamaVisionAdapter(VisionPort):
    def __init__(self, *, base_url: str, model: str, timeout_seconds: int = 120) -> None:
        self._base_url = base_url.rstrip('/')
        self._model = model
        self._timeout_seconds = timeout_seconds

    def _render_page_image_base64(self, *, pdf_path: str, page_number: int) -> str:
        try:
            import fitz
        except ModuleNotFoundError:
            return ''

        doc = fitz.open(pdf_path)
        try:
            if page_number < 1 or page_number > doc.page_count:
                return ''
            page = doc.load_page(page_number - 1)
            rect = page.rect
            max_dim = 1600.0
            zoom = min(max_dim / max(rect.width, 1.0), max_dim / max(rect.height, 1.0), 2.0)
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            raw = pix.tobytes('png')
            return base64.b64encode(raw).decode('ascii')
        finally:
            doc.close()

    def _prompt(self, page_number: int) -> str:
        return (
            f'Analyze this manual page image (page {page_number}). '
            'Extract actionable technical content only as plain text lines:\n'
            '- parameter names and meanings\n'
            '- procedures and ordered steps\n'
            '- troubleshooting rows (symptom -> cause -> remedy)\n'
            '- terminal/wiring mappings\n'
            '- warnings/cautions\n'
            'Do not invent values. Keep concise and factual.'
        )

    def extract_page_insights(self, *, pdf_path: str, page_number: int) -> str:
        image_b64 = self._render_page_image_base64(pdf_path=pdf_path, page_number=page_number)
        if not image_b64:
            return ''

        payload = {
            'model': self._model,
            'stream': False,
            'messages': [
                {
                    'role': 'user',
                    'content': self._prompt(page_number),
                    'images': [image_b64],
                }
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
            return str(content).strip()
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return ''
