from __future__ import annotations

import re

from packages.ports.table_extractor_port import ExtractedTable, TableExtractorPort


class SimpleTableExtractorAdapter(TableExtractorPort):
    """Heuristic table extractor for mixed PDF/manual text.

    Detects table-like blocks using:
    - pipe delimiters (`|`)
    - multi-column spacing (2+ spaces)
    - key-value rows with units/numbers (`label: value`)
    """

    _KEY_VALUE_PATTERN = re.compile(
        r'^[A-Za-z][A-Za-z0-9\-/()\s]{2,}:\s*[-+]?\d+(?:\.\d+)?\s*(?:[A-Za-z%/]+)?$'
    )

    def extract(self, page_text: str, page_number: int) -> list[ExtractedTable]:
        lines = [line.rstrip() for line in page_text.splitlines() if line.strip()]
        if not lines:
            return []

        groups: list[list[str]] = []
        current: list[str] = []

        for line in lines:
            if self._looks_tabular(line):
                current.append(line.strip())
            else:
                if len(current) >= 2:
                    groups.append(current)
                current = []

        if len(current) >= 2:
            groups.append(current)

        tables: list[ExtractedTable] = []
        for idx, group in enumerate(groups, start=1):
            table_text = self._normalize_group(group)
            tables.append(
                ExtractedTable(
                    table_id=f'table-p{page_number:04d}-{idx:03d}',
                    page_number=page_number,
                    text=table_text,
                )
            )

        return tables

    def _looks_tabular(self, line: str) -> bool:
        s = line.strip()
        if not s:
            return False
        if '|' in s:
            return True
        if self._KEY_VALUE_PATTERN.match(s):
            return True

        cols = [c for c in re.split(r'\s{2,}', s) if c]
        if len(cols) >= 3:
            return True

        # Numeric-heavy rows often indicate parameter tables.
        numeric_tokens = re.findall(r'[-+]?\d+(?:\.\d+)?', s)
        alpha_tokens = re.findall(r'[A-Za-z]{2,}', s)
        return len(numeric_tokens) >= 2 and len(alpha_tokens) >= 1

    def _normalize_group(self, lines: list[str]) -> str:
        normalized: list[str] = []
        for line in lines:
            if '|' in line:
                normalized.append(line)
                continue

            if ':' in line and self._KEY_VALUE_PATTERN.match(line):
                label, value = line.split(':', 1)
                normalized.append(f'{label.strip()} | {value.strip()}')
                continue

            cols = [c.strip() for c in re.split(r'\s{2,}', line) if c.strip()]
            if len(cols) >= 3:
                normalized.append(' | '.join(cols))
            else:
                normalized.append(line.strip())

        return '\n'.join(normalized)
