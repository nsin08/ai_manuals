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


class TestFigureBboxWiring:
    """Unit tests for figure_regions -> chunk metadata wiring added in Phase 1 review cycle."""

    def test_figure_caption_chunk_gets_bbox_when_figure_regions_provided(
        self,
        mock_ocr_adapter: MagicMock,
        mock_vision_budget: dict[str, int],
    ) -> None:
        """When figure_regions contains a bbox entry, figure_caption chunk metadata must include it."""
        from threading import Lock

        # A line matching _extract_figure_captions regex: starts with 'Figure N'
        text = "Figure 1 Pressure relief valve cross-section"
        page = _make_page(text, number=3)
        expected_bbox = [10.0, 20.0, 300.0, 200.0]
        figure_regions = [
            {'bbox': expected_bbox, 'type': 'figure', 'doc_id': 'doc1', 'page_number': 3}
        ]

        output = _process_single_page(
            doc_id='doc1',
            pdf_path=Path('/fake/doc1.pdf'),
            page=page,
            ocr_adapter=mock_ocr_adapter,
            table_extractor=SimpleTableExtractorAdapter(),
            vision_adapter=None,
            vision_budget=mock_vision_budget,
            vision_budget_lock=Lock(),
            figure_regions=figure_regions,
        )

        caption_chunks = [c for c in output.chunks if c.content_type == 'figure_caption']
        assert caption_chunks, "Expected at least one figure_caption chunk"
        chunk = caption_chunks[0]
        assert chunk.metadata is not None, "figure_caption chunk must carry metadata when bbox is available"
        assert chunk.metadata.get('bbox') == expected_bbox, (
            f"metadata['bbox'] must equal figure_regions[0]['bbox'], got {chunk.metadata}"
        )

    def test_figure_ocr_chunk_gets_bbox_when_figure_regions_provided(
        self,
        mock_ocr_adapter: MagicMock,
        mock_vision_budget: dict[str, int],
    ) -> None:
        """figure_ocr chunks must also receive the bbox metadata from figure_regions."""
        from threading import Lock

        # Use a long caption text (>=80 chars) so _should_attempt_ocr returns False,
        # preventing spontaneous page-level figure_ocr creation. The captioned path
        # will then call extract_text per-figure and use the mock's return value.
        text = (
            "Figure 2 Terminal block layout showing the complete field wiring and "
            "terminal numbering for all I/O connections on the main board assembly."
        )
        page = _make_page(text, number=4)
        expected_bbox = [5.0, 15.0, 250.0, 180.0]
        figure_regions = [{'bbox': expected_bbox, 'type': 'figure', 'doc_id': 'doc1', 'page_number': 4}]

        # Mock OCR to return text for the per-figure call inside the captions loop
        mock_ocr_adapter.extract_text.return_value = 'terminal block ocr text'

        output = _process_single_page(
            doc_id='doc1',
            pdf_path=Path('/fake/doc1.pdf'),
            page=page,
            ocr_adapter=mock_ocr_adapter,
            table_extractor=SimpleTableExtractorAdapter(),
            vision_adapter=None,
            vision_budget=mock_vision_budget,
            vision_budget_lock=Lock(),
            figure_regions=figure_regions,
        )

        # Only figure_ocr chunks tied to a figure_id carry the bbox from figure_regions
        captioned_ocr_chunks = [
            c for c in output.chunks
            if c.content_type == 'figure_ocr' and c.figure_id is not None
        ]
        assert captioned_ocr_chunks, "Expected figure_ocr chunk with figure_id when OCR returns text"
        chunk = captioned_ocr_chunks[0]
        assert chunk.metadata is not None, "figure_ocr chunk must carry metadata when bbox is available"
        assert chunk.metadata.get('bbox') == expected_bbox

    def test_figure_caption_chunk_has_no_metadata_when_figure_regions_is_none(
        self,
        mock_ocr_adapter: MagicMock,
        mock_vision_budget: dict[str, int],
    ) -> None:
        """When figure_regions is None (fitz unavailable), chunk metadata must be None."""
        from threading import Lock

        text = "Figure 3 Fan blade assembly"
        page = _make_page(text, number=5)

        output = _process_single_page(
            doc_id='doc1',
            pdf_path=Path('/fake/doc1.pdf'),
            page=page,
            ocr_adapter=mock_ocr_adapter,
            table_extractor=SimpleTableExtractorAdapter(),
            vision_adapter=None,
            vision_budget=mock_vision_budget,
            vision_budget_lock=Lock(),
            figure_regions=None,
        )

        caption_chunks = [c for c in output.chunks if c.content_type == 'figure_caption']
        assert caption_chunks, "Expected figure_caption chunk for Figure 3"
        for chunk in caption_chunks:
            assert chunk.metadata is None, (
                f"metadata must be None when figure_regions=None, got {chunk.metadata}"
            )

    def test_figure_caption_chunk_has_no_bbox_when_figure_regions_empty_list(
        self,
        mock_ocr_adapter: MagicMock,
        mock_vision_budget: dict[str, int],
    ) -> None:
        """When figure_regions is an empty list (page had no detected figures), metadata is None."""
        from threading import Lock

        # Two captions: only the first index is checked, empty list means no bbox for either
        text = "Figure 4 Wiring harness"
        page = _make_page(text, number=6)

        output = _process_single_page(
            doc_id='doc1',
            pdf_path=Path('/fake/doc1.pdf'),
            page=page,
            ocr_adapter=mock_ocr_adapter,
            table_extractor=SimpleTableExtractorAdapter(),
            vision_adapter=None,
            vision_budget=mock_vision_budget,
            vision_budget_lock=Lock(),
            figure_regions=[],
        )

        caption_chunks = [c for c in output.chunks if c.content_type == 'figure_caption']
        assert caption_chunks, "Expected figure_caption chunk for Figure 4"
        for chunk in caption_chunks:
            assert chunk.metadata is None, (
                f"metadata must be None when figure_regions=[], got {chunk.metadata}"
            )

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
