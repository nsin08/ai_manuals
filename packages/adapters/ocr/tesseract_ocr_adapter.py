from __future__ import annotations

from packages.ports.ocr_port import OcrPort


class TesseractOcrAdapter(OcrPort):
    """OCR adapter using PyMuPDF page rendering + pytesseract recognition."""

    def __init__(self, dpi_scale: float = 2.0) -> None:
        self._dpi_scale = dpi_scale

    def extract_text(self, source_path: str, page_number: int) -> str:
        try:
            import fitz  # type: ignore
            import pytesseract  # type: ignore
            from PIL import Image
        except Exception as exc:  # pragma: no cover - optional dependency path
            raise RuntimeError(
                'Tesseract OCR dependencies are not installed: PyMuPDF + pytesseract'
            ) from exc

        try:
            doc = fitz.open(source_path)
            if page_number < 1 or page_number > doc.page_count:
                return ''

            page = doc.load_page(page_number - 1)
            matrix = fitz.Matrix(self._dpi_scale, self._dpi_scale)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            image = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)

            text = pytesseract.image_to_string(image)
            return (text or '').strip()
        except FileNotFoundError:
            # tesseract binary not installed in runtime environment
            return ''
        except Exception:
            return ''
