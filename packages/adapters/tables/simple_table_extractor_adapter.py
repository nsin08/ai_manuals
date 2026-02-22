from __future__ import annotations

import re

from packages.ports.table_extractor_port import ExtractedTable, ExtractedTableRow, TableExtractorPort

# Regex to match a unit string like "(rpm)", "(V)", "(Hz)", "(m/s^2)"
_UNIT_PATTERN = re.compile(r'\(([^)]{1,20})\)')


class SimpleTableExtractorAdapter(TableExtractorPort):
    """Heuristic table extractor for mixed PDF/manual text.

    Detects table-like blocks using:
    - pipe delimiters (``|``)
    - multi-column spacing (2+ spaces)
    - key-value rows with units/numbers (``label: value``)

    Emits structured ExtractedTableRow objects (one per row) with:
    - headers: detected from first row when >= 50% are non-numeric short strings
    - row_cells: split on ``|`` or 2+ spaces
    - units: extracted from ``(unit)`` patterns per cell
    """

    _KEY_VALUE_PATTERN = re.compile(
        r'^[A-Za-z][A-Za-z0-9\-/()\s]{2,}:\s*[-+]?\d+(?:\.\d+)?\s*(?:[A-Za-z%/^]+)?$'
    )

    def extract(self, page_text: str, page_number: int, doc_id: str = '') -> list[ExtractedTable]:
        lines = [line.rstrip() for line in page_text.splitlines() if line.strip()]
        if not lines:
            return []

        # --- detect tabular line groups ---
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
        for table_idx, group in enumerate(groups):
            table_id = (
                f'tbl_{doc_id}_{page_number}_{table_idx:03d}'
                if doc_id
                else f'table-p{page_number:04d}-{table_idx:03d}'
            )
            rows = self._parse_rows(group, table_id=table_id, page_number=page_number)
            # Reconstruct raw_text from parsed rows with | separators (if rows exist)
            # Fallback to original group text if no rows.
            if rows:
                raw_lines = []
                for row in rows:
                    if row.headers:
                        # Include headers on first row
                        raw_lines.append(' | '.join(row.headers) + ' || ' + ' | '.join(row.row_cells))
                    else:
                        raw_lines.append(' | '.join(row.row_cells))
                raw_text = '\n'.join(raw_lines)
            else:
                raw_text = '\n'.join(group)
            tables.append(
                ExtractedTable(
                    table_id=table_id,
                    page_number=page_number,
                    rows=rows,
                    raw_text=raw_text,
                )
            )
        return tables

    # ------------------------------------------------------------------ helpers

    def _parse_rows(
        self,
        raw_lines: list[str],
        table_id: str,
        page_number: int,
    ) -> list[ExtractedTableRow]:
        """Parse raw lines into ExtractedTableRow objects."""
        if not raw_lines:
            return []

        split_lines = [self._split_row(line) for line in raw_lines]

        # Detect key-value tables: >= 80% of rows were split on a colon
        # (i.e. `key: value` pattern).  Use raw_lines to verify colon origin so
        # that regular 2-column tab/space tables are NOT mistaken for KV tables.
        def _is_colon_split(raw: str, cells: list[str]) -> bool:
            return (
                len(cells) == 2
                and ':' in raw
                and '://' not in raw
                and raw.split(':', 1)[0].strip() == cells[0]
            )

        kv_row_count = sum(
            1 for raw, cells in zip(raw_lines, split_lines) if _is_colon_split(raw, cells)
        )
        is_kv_table = len(split_lines) > 0 and kv_row_count / len(split_lines) >= 0.8

        # Header detection: first row is header when >= 50% of cells are
        # non-numeric strings shorter than 30 chars.
        headers: list[str] = []
        data_start = 0
        if split_lines and not is_kv_table:
            candidate = split_lines[0]
            non_numeric = sum(
                1 for c in candidate
                if c
                and not re.fullmatch(r'[-+]?\d+(?:\.\d+)?\s*(?:[A-Za-z%/^]*)', c.strip())
                and len(c.strip()) < 30
            )
            if len(candidate) > 0 and non_numeric / max(len(candidate), 1) >= 0.5:
                headers = [c.strip() for c in candidate]
                data_start = 1

        rows: list[ExtractedTableRow] = []
        for row_idx, cells in enumerate(split_lines[data_start:]):
            stripped = [c.strip() for c in cells]
            # Extract unit strings per cell
            units = [
                (m.group(1) if (m := _UNIT_PATTERN.search(cell)) else '')
                for cell in stripped
            ]
            rows.append(
                ExtractedTableRow(
                    table_id=table_id,
                    page_number=page_number,
                    row_index=row_idx,
                    headers=headers,
                    row_cells=stripped,
                    units=units,
                    raw_text=raw_lines[data_start + row_idx],
                )
            )

        # Fallback: if parsing produced no usable rows emit a single row
        if not rows:
            raw = '\n'.join(raw_lines)
            rows = [
                ExtractedTableRow(
                    table_id=table_id,
                    page_number=page_number,
                    row_index=0,
                    headers=[],
                    row_cells=[raw],
                    units=[''],
                    raw_text=raw,
                )
            ]

        return rows

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
        numeric_tokens = re.findall(r'[-+]?\d+(?:\.\d+)?', s)
        alpha_tokens = re.findall(r'[A-Za-z]{2,}', s)
        return len(numeric_tokens) >= 2 and len(alpha_tokens) >= 1

    @staticmethod
    def _split_row(line: str) -> list[str]:
        """Split a row on pipe, colon (key-value), or 2+ spaces."""
        if '|' in line:
            return [c.strip() for c in line.split('|') if c.strip()]
        # Split on colon for key-value pairs
        if ':' in line and '://' not in line:  # avoid splitting on URLs/paths
            parts = line.split(':', 1)
            if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                return [parts[0].strip(), parts[1].strip()]
        cols = re.split(r'\s{2,}', line)
        return [c.strip() for c in cols if c.strip()] or [line]
