"""Tests for _extract_figure_regions and _bbox_from_text_block in visual_artifact_generation (Phase 1 #3)."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from packages.adapters.data_contracts.visual_artifact_generation import (
    _bbox_from_text_block,
    _extract_figure_regions,
    build_visual_artifacts_from_chunks,
)


# ---------------------------------------------------------------------------
# Helpers to build fake fitz-like objects without requiring PyMuPDF installed
# ---------------------------------------------------------------------------

def _make_fake_page(blocks: list[dict[str, Any]], width: float = 595.0, height: float = 842.0) -> MagicMock:
    """Build a MagicMock that behaves like a fitz.Page for testing."""
    page = MagicMock()
    page.rect = MagicMock()
    page.rect.width = width
    page.rect.height = height
    page.get_text.return_value = {'blocks': blocks}
    return page


def _image_block(bbox: tuple[float, float, float, float]) -> dict[str, Any]:
    return {'type': 1, 'bbox': bbox}


def _text_block(bbox: tuple[float, float, float, float]) -> dict[str, Any]:
    return {'type': 0, 'bbox': bbox}


# ---------------------------------------------------------------------------
# Tests for _extract_figure_regions
# ---------------------------------------------------------------------------

class TestExtractFigureRegions:
    def test_returns_figure_id_and_bbox(self) -> None:
        page = _make_fake_page([_image_block((0, 0, 297.5, 421))])
        with patch('packages.adapters.data_contracts.visual_artifact_generation._FITZ_AVAILABLE', True):
            regions = _extract_figure_regions(page, doc_id='doc1', page_num=1)
        assert len(regions) == 1
        r = regions[0]
        assert 'figure_id' in r
        assert 'bbox' in r
        assert r['page_number'] == 1

    def test_bbox_is_list_of_4_floats(self) -> None:
        page = _make_fake_page([_image_block((100, 200, 400, 600))])
        with patch('packages.adapters.data_contracts.visual_artifact_generation._FITZ_AVAILABLE', True):
            regions = _extract_figure_regions(page, doc_id='doc1', page_num=2)
        bbox = regions[0]['bbox']
        assert isinstance(bbox, list)
        assert len(bbox) == 4
        assert all(isinstance(v, float) for v in bbox)

    def test_bbox_normalized_to_0_1(self) -> None:
        """Bbox values must be in [0, 1] after normalization."""
        # Page: 595 x 842; block fills full page
        page = _make_fake_page([_image_block((0.0, 0.0, 595.0, 842.0))], width=595.0, height=842.0)
        with patch('packages.adapters.data_contracts.visual_artifact_generation._FITZ_AVAILABLE', True):
            regions = _extract_figure_regions(page, doc_id='doc1', page_num=1)
        bbox = regions[0]['bbox']
        assert bbox[0] == pytest.approx(0.0)
        assert bbox[1] == pytest.approx(0.0)
        assert bbox[2] == pytest.approx(1.0)
        assert bbox[3] == pytest.approx(1.0)

    def test_bbox_partial_region_normalized(self) -> None:
        # Block occupies top-left quarter
        page = _make_fake_page([_image_block((0.0, 0.0, 297.5, 421.0))], width=595.0, height=842.0)
        with patch('packages.adapters.data_contracts.visual_artifact_generation._FITZ_AVAILABLE', True):
            regions = _extract_figure_regions(page, doc_id='doc1', page_num=1)
        bbox = regions[0]['bbox']
        assert bbox[0] == pytest.approx(0.0)
        assert bbox[1] == pytest.approx(0.0)
        assert bbox[2] == pytest.approx(0.5)
        assert bbox[3] == pytest.approx(0.5)

    def test_text_blocks_ignored(self) -> None:
        """type==0 (text) blocks must be ignored; only type==1 (raster image) returned."""
        page = _make_fake_page([
            _text_block((0, 0, 100, 50)),
            _image_block((0, 100, 200, 300)),
        ])
        with patch('packages.adapters.data_contracts.visual_artifact_generation._FITZ_AVAILABLE', True):
            regions = _extract_figure_regions(page, doc_id='doc1', page_num=1)
        assert len(regions) == 1

    def test_multiple_image_blocks_all_returned(self) -> None:
        page = _make_fake_page([
            _image_block((0, 0, 100, 100)),
            _text_block((0, 100, 100, 120)),
            _image_block((0, 200, 100, 300)),
        ])
        with patch('packages.adapters.data_contracts.visual_artifact_generation._FITZ_AVAILABLE', True):
            regions = _extract_figure_regions(page, doc_id='doc1', page_num=3)
        assert len(regions) == 2

    def test_figure_id_includes_doc_id_and_page(self) -> None:
        page = _make_fake_page([_image_block((0, 0, 100, 100))])
        with patch('packages.adapters.data_contracts.visual_artifact_generation._FITZ_AVAILABLE', True):
            regions = _extract_figure_regions(page, doc_id='siemens_g120', page_num=5)
        assert 'siemens_g120' in regions[0]['figure_id']
        assert 'p0005' in regions[0]['figure_id']

    def test_empty_page_returns_empty_list(self) -> None:
        page = _make_fake_page([])
        with patch('packages.adapters.data_contracts.visual_artifact_generation._FITZ_AVAILABLE', True):
            regions = _extract_figure_regions(page, doc_id='doc1', page_num=1)
        assert regions == []

    def test_returns_empty_when_fitz_not_available(self) -> None:
        """When fitz is unavailable, should return [] gracefully."""
        with patch('packages.adapters.data_contracts.visual_artifact_generation._FITZ_AVAILABLE', False):
            page = MagicMock()
            regions = _extract_figure_regions(page, doc_id='doc1', page_num=1)
            assert regions == []


# ---------------------------------------------------------------------------
# Tests for _bbox_from_text_block
# ---------------------------------------------------------------------------

class TestBboxFromTextBlock:
    def test_returns_4_normalized_floats(self) -> None:
        page = _make_fake_page([], width=595.0, height=842.0)
        block = {'type': 0, 'bbox': (59.5, 84.2, 297.5, 421.0)}
        result = _bbox_from_text_block(block, page)
        assert isinstance(result, list)
        assert len(result) == 4
        assert all(isinstance(v, float) for v in result)

    def test_normalization_correct(self) -> None:
        page = _make_fake_page([], width=595.0, height=842.0)
        # Block exactly half the page (x) and quarter (y)
        block = {'type': 0, 'bbox': (0.0, 0.0, 297.5, 210.5)}
        result = _bbox_from_text_block(block, page)
        assert result[0] == pytest.approx(0.0)
        assert result[1] == pytest.approx(0.0)
        assert result[2] == pytest.approx(0.5)
        assert result[3] == pytest.approx(0.25, abs=0.01)


# ---------------------------------------------------------------------------
# Tests for visual artifact metadata.bbox passthrough
# ---------------------------------------------------------------------------

class TestBuildVisualArtifactsBboxPassthrough:
    def test_uses_metadata_bbox_when_present(self) -> None:
        """build_visual_artifacts_from_chunks must use metadata.bbox if available."""
        chunk = {
            'chunk_id': 'c1',
            'doc_id': 'doc1',
            'content_type': 'table_row',
            'page_start': 1,
            'page_end': 1,
            'content_text': 'Col1 | A',
            'table_id': 'tbl_doc1_1_000',
            'figure_id': None,
            'caption': None,
            'metadata': {'bbox': [0.1, 0.2, 0.8, 0.9], 'table_id': 'tbl_doc1_1_000', 'row_index': 0},
        }
        visual_rows, _, _ = build_visual_artifacts_from_chunks('doc1', [chunk])
        assert len(visual_rows) == 1
        assert visual_rows[0]['bbox'] == [0.1, 0.2, 0.8, 0.9]

    def test_falls_back_to_full_page_bbox_when_no_metadata_bbox(self) -> None:
        chunk = {
            'chunk_id': 'c2',
            'doc_id': 'doc1',
            'content_type': 'table_row',
            'page_start': 2,
            'page_end': 2,
            'content_text': 'x',
            'table_id': 'tbl_doc1_2_000',
            'figure_id': None,
            'caption': None,
            'metadata': {},
        }
        visual_rows, _, _ = build_visual_artifacts_from_chunks('doc1', [chunk])
        assert len(visual_rows) == 1
        assert visual_rows[0]['bbox'] == [0, 0, 1, 1]

    def test_table_row_chunk_included_in_visual_artifacts(self) -> None:
        """table_row content_type must be included (not filtered out)."""
        chunk = {
            'chunk_id': 'c3',
            'doc_id': 'doc1',
            'content_type': 'table_row',
            'page_start': 1,
            'page_end': 1,
            'content_text': 'some row',
            'table_id': 'tbl_doc1_1_000',
            'figure_id': None,
            'caption': None,
            'metadata': {},
        }
        visual_rows, _, _ = build_visual_artifacts_from_chunks('doc1', [chunk])
        assert any(r.get('modality') == 'table' for r in visual_rows), \
            "table_row chunks should produce modality='table' visual artifacts"

    def test_figure_chunk_has_bbox_keys(self) -> None:
        chunk = {
            'chunk_id': 'c4',
            'doc_id': 'doc1',
            'content_type': 'figure_ocr',
            'page_start': 1,
            'page_end': 1,
            'content_text': 'figure text',
            'figure_id': 'fig_doc1_p0001_000',
            'table_id': None,
            'caption': None,
            'metadata': {'bbox': [0.0, 0.1, 0.5, 0.6]},
        }
        visual_rows, _, _ = build_visual_artifacts_from_chunks('doc1', [chunk])
        assert len(visual_rows) == 1
        assert len(visual_rows[0]['bbox']) == 4
        assert visual_rows[0]['bbox'] == [0.0, 0.1, 0.5, 0.6]
