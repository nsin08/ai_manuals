from __future__ import annotations

from packages.adapters.ocr.noop_ocr_adapter import NoopOcrAdapter
from packages.adapters.ocr.paddle_ocr_adapter import PaddleOcrAdapter
from packages.adapters.ocr.tesseract_ocr_adapter import TesseractOcrAdapter
from packages.ports.ocr_port import OcrPort


class FallbackOcrAdapter(OcrPort):
    def __init__(self, primary: OcrPort, fallback: OcrPort) -> None:
        self._primary = primary
        self._fallback = fallback

    def extract_text(self, source_path: str, page_number: int) -> str:
        text = ''
        try:
            text = self._primary.extract_text(source_path, page_number).strip()
        except Exception:
            text = ''

        if text:
            return text

        try:
            return self._fallback.extract_text(source_path, page_number).strip()
        except Exception:
            return ''



def create_ocr_adapter(engine: str, fallback_engine: str = 'noop') -> OcrPort:
    def build(name: str) -> OcrPort:
        normalized = name.strip().lower()
        if normalized == 'paddle':
            return PaddleOcrAdapter()
        if normalized == 'tesseract':
            return TesseractOcrAdapter()
        if normalized == 'noop':
            return NoopOcrAdapter()
        raise ValueError(f'Unsupported OCR engine: {name}')

    try:
        primary = build(engine)
    except Exception:
        primary = NoopOcrAdapter()

    try:
        fallback = build(fallback_engine)
    except Exception:
        fallback = NoopOcrAdapter()

    if isinstance(primary, NoopOcrAdapter):
        return fallback

    return FallbackOcrAdapter(primary=primary, fallback=fallback)
