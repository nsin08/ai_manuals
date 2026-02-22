"""Tests for table_row chunk emission in ingest_document._process_single_page (Phase 1 #3).

Uses unit-level mocking so no database or PDF file is required.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from packages.adapters.tables.simple_table_extractor_adapter import SimpleTableExtractorAdapter
from packages.ports.table_extractor_port import ExtractedTable, ExtractedTableRow
from packages.application.use_cases.ingest_document import _process_single_page
from packages.ports.pdf_parser_port import ParsedPdfPage


def _make_page(text: str, number: int = 1) -> ParsedPdfPage:
    return ParsedPdfPage(page_number=number, text=text)


def _make_row(table_id: str, page: int, idx: int, headers: list[str], cells: list[str]) -> ExtractedTableRow:
    units = ['' for _ in cells]
    return ExtractedTableRow(
        table_id=table_id,
        page_number=page,
        row_index=idx,
        headers=headers,
        row_cells=cells,
        units=units,
        raw_text=' | '.join(cells),
    )


def _make_table_with_rows(table_id: str, page: int, n_rows: int) -> ExtractedTable:
    headers = ['Col1', 'Col2']
    rows = [_make_row(table_id, page, i, headers, [f'A{i}', f'B{i}']) for i in range(n_rows)]
    return ExtractedTable(table_id=table_id, page_number=page, rows=rows, raw_text='')


@pytest.fixture()
def mock_ocr_adapter() -> MagicMock:
    adapter = MagicMock()
    adapter.extract_text.return_value = ''
    return adapter


@pytest.fixture()
def mock_vision_budget() -> dict[str, int]:
    return {'remaining': 0}


class TestTableRowChunkEmission:
    def test_emits_table_row_content_type(
        self,
        mock_ocr_adapter: MagicMock,
        mock_vision_budget: dict[str, int],
    ) -> None:
        """Ingestion must emit content_type='table_row', NOT 'table'."""
        table_text = "Parameter  Value  Unit\nSpeed      1450   rpm\nVoltage    400    V"
        page = _make_page(table_text, number=1)

        table_extractor = SimpleTableExtractorAdapter()
        from threading import Lock

        output = _process_single_page(
            doc_id='doc1',
            pdf_path=Path('/fake/doc1.pdf'),
            page=page,
            ocr_adapter=mock_ocr_adapter,
            table_extractor=table_extractor,
            vision_adapter=None,
            vision_budget=mock_vision_budget,
            vision_budget_lock=Lock(),
        )

        content_types = [c.content_type for c in output.chunks]
        assert 'table_row' in content_types, f"Expected 'table_row' in types, got: {content_types}"
        assert 'table' not in content_types, "'table' content_type must not be emitted (removed in Phase 1)"

    def test_emits_one_chunk_per_table_row(
        self,
        mock_ocr_adapter: MagicMock,
        mock_vision_budget: dict[str, int],
    ) -> None:
        """Number of table_row chunks must equal total data rows across all tables."""
        # 3-row table (1 header + 2 data rows)
        table_text = "Header1  Header2\nRow1A    Row1B\nRow2A    Row2B"
        page = _make_page(table_text, number=2)

        table_extractor = SimpleTableExtractorAdapter()
        from threading import Lock

        output = _process_single_page(
            doc_id='doc1',
            pdf_path=Path('/fake/doc1.pdf'),
            page=page,
            ocr_adapter=mock_ocr_adapter,
            table_extractor=table_extractor,
            vision_adapter=None,
            vision_budget=mock_vision_budget,
            vision_budget_lock=Lock(),
        )

        row_chunks = [c for c in output.chunks if c.content_type == 'table_row']
        # The adapter should parse 2 data rows
        assert len(row_chunks) == 2, f"Expected 2 table_row chunks, got {len(row_chunks)}"

    def test_table_row_metadata_complete(
        self,
        mock_ocr_adapter: MagicMock,
        mock_vision_budget: dict[str, int],
    ) -> None:
        """Each table_row chunk must carry table_id, row_index, headers, units in metadata."""
        table_text = "Parameter  Value  Unit\nSpeed      1450   rpm"
        page = _make_page(table_text, number=1)

        table_extractor = SimpleTableExtractorAdapter()
        from threading import Lock

        output = _process_single_page(
            doc_id='doc1',
            pdf_path=Path('/fake/doc1.pdf'),
            page=page,
            ocr_adapter=mock_ocr_adapter,
            table_extractor=table_extractor,
            vision_adapter=None,
            vision_budget=mock_vision_budget,
            vision_budget_lock=Lock(),
        )

        row_chunks = [c for c in output.chunks if c.content_type == 'table_row']
        assert row_chunks, "No table_row chunks emitted"

        for chunk in row_chunks:
            assert chunk.table_id is not None, "table_id must be set on chunk"
            assert chunk.metadata.get('table_id') is not None, "metadata.table_id must be set"
            assert chunk.metadata.get('row_index') is not None, "metadata.row_index must be set"
            assert 'headers' in chunk.metadata, "metadata.headers must be present"
            assert 'units' in chunk.metadata, "metadata.units must be present"

    def test_table_row_row_index_sequential(
        self,
        mock_ocr_adapter: MagicMock,
        mock_vision_budget: dict[str, int],
    ) -> None:
        """row_index should be sequential starting from 0."""
        table_text = "Col1  Col2\nA     B\nC     D\nE     F"
        page = _make_page(table_text, number=1)

        table_extractor = SimpleTableExtractorAdapter()
        from threading import Lock

        output = _process_single_page(
            doc_id='doc1',
            pdf_path=Path('/fake/doc1.pdf'),
            page=page,
            ocr_adapter=mock_ocr_adapter,
            table_extractor=table_extractor,
            vision_adapter=None,
            vision_budget=mock_vision_budget,
            vision_budget_lock=Lock(),
        )

        row_chunks = [c for c in output.chunks if c.content_type == 'table_row']
        indices = [c.metadata.get('row_index') for c in row_chunks]
        assert indices == list(range(len(row_chunks))), f"Expected sequential indices, got: {indices}"
