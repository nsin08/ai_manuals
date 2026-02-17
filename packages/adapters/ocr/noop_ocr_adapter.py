from __future__ import annotations

from packages.ports.ocr_port import OcrPort


class NoopOcrAdapter(OcrPort):
    def extract_text(self, source_path: str, page_number: int) -> str:
        _ = source_path
        _ = page_number
        return ''
