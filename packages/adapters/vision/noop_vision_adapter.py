from __future__ import annotations

from packages.ports.vision_port import VisionPort


class NoopVisionAdapter(VisionPort):
    def extract_page_insights(self, *, pdf_path: str, page_number: int) -> str:
        _ = pdf_path, page_number
        return ''
