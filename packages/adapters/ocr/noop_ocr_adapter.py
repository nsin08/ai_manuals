from __future__ import annotations

from packages.ports.ocr_port import OcrPort


class NoopOcrAdapter(OcrPort):
    def extract_text(self, source_path: str, page_number: int) -> str:
        # Phase 1 scaffold: OCR integration will be upgraded in a later phase.
        _ = source_path
        _ = page_number
        return ''
