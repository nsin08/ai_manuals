from __future__ import annotations

import re

from packages.ports.table_extractor_port import ExtractedTable, TableExtractorPort


class SimpleTableExtractorAdapter(TableExtractorPort):
    """Heuristic table extractor for Phase 1.

    Detects lines that look tabular:
    - contains pipe delimiters, or
    - has 3+ columns separated by 2+ spaces.
    """

    def extract(self, page_text: str, page_number: int) -> list[ExtractedTable]:
        lines = [line.strip() for line in page_text.splitlines() if line.strip()]
        table_lines: list[str] = []

        for line in lines:
            if '|' in line:
                table_lines.append(line)
                continue

            cols = re.split(r'\s{2,}', line)
            if len([c for c in cols if c]) >= 3:
                table_lines.append(line)

        if not table_lines:
            return []

        return [
            ExtractedTable(
                table_id=f'table-p{page_number:04d}-001',
                page_number=page_number,
                text='\n'.join(table_lines),
            )
        ]
