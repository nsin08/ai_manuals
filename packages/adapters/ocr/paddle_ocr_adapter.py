from __future__ import annotations

from packages.ports.ocr_port import OcrPort


class PaddleOcrAdapter(OcrPort):
    """OCR adapter using PaddleOCR.

    This adapter is optional and activates only if paddleocr is installed.
    """

    def __init__(self, use_angle_cls: bool = True, lang: str = 'en', dpi_scale: float = 2.0) -> None:
        self._use_angle_cls = use_angle_cls
        self._lang = lang
        self._dpi_scale = dpi_scale
        self._ocr = None

    def _ensure_ocr(self):
        if self._ocr is not None:
            return self._ocr

        try:
            from paddleocr import PaddleOCR  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency path
            raise RuntimeError('PaddleOCR is not installed') from exc

        self._ocr = PaddleOCR(use_angle_cls=self._use_angle_cls, lang=self._lang)
        return self._ocr

    def extract_text(self, source_path: str, page_number: int) -> str:
        try:
            import fitz  # type: ignore
            import numpy as np
        except Exception as exc:  # pragma: no cover
            raise RuntimeError('Paddle OCR dependencies are not installed: PyMuPDF + numpy') from exc

        try:
            ocr = self._ensure_ocr()
            doc = fitz.open(source_path)
            if page_number < 1 or page_number > doc.page_count:
                return ''

            page = doc.load_page(page_number - 1)
            matrix = fitz.Matrix(self._dpi_scale, self._dpi_scale)
            pix = page.get_pixmap(matrix=matrix, alpha=False)

            image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            result = ocr.ocr(image, cls=self._use_angle_cls)

            lines: list[str] = []
            for block in result or []:
                for item in block or []:
                    if len(item) >= 2 and item[1]:
                        text = item[1][0]
                        if text:
                            lines.append(str(text).strip())

            return '\n'.join(line for line in lines if line)
        except Exception:
            return ''
