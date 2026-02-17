from __future__ import annotations

from pypdf import PdfReader

from packages.ports.pdf_parser_port import ParsedPdfPage, PdfParserPort


class PypdfParserAdapter(PdfParserPort):
    def parse(self, pdf_path: str) -> list[ParsedPdfPage]:
        reader = PdfReader(pdf_path)
        pages: list[ParsedPdfPage] = []

        for idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ''
            pages.append(ParsedPdfPage(page_number=idx, text=text.strip()))

        return pages
