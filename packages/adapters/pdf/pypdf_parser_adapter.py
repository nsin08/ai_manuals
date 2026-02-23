from __future__ import annotations

import warnings

from pypdf import PdfReader
from pypdf.errors import PdfReadWarning

from packages.ports.pdf_parser_port import ParsedPdfPage, PdfParserPort


class PypdfParserAdapter(PdfParserPort):
    def parse(self, pdf_path: str) -> list[ParsedPdfPage]:
        reader = PdfReader(pdf_path)
        pages: list[ParsedPdfPage] = []

        for idx, page in enumerate(reader.pages, start=1):
            # extraction_mode='layout' preserves 2+ space column gaps so that
            # multi-column tables (e.g. FANUC heat/weight table) are split
            # correctly by _split_row instead of collapsing to single-space blobs.
            # Fallback to default extraction on any error (e.g. encrypted page).
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', PdfReadWarning)
                    text = page.extract_text(extraction_mode='layout') or ''
            except Exception:
                text = page.extract_text() or ''
            pages.append(ParsedPdfPage(page_number=idx, text=text.strip()))

        return pages
