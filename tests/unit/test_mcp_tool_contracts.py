"""Unit tests — MCP tool contract schemas.

Verifies that each tool returns the correct dict schema per the issue #12
Evidence Mapping.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_evidence_hit(**overrides):
    from packages.application.use_cases.search_evidence import EvidenceHit

    defaults = dict(
        chunk_id='chunk-1',
        doc_id='manual_a',
        content_type='text',
        page_start=3,
        page_end=3,
        section_path='Section 1',
        figure_id=None,
        table_id=None,
        score=0.85,
        keyword_score=0.8,
        vector_score=0.9,
        snippet='Bearing preload must be set to 0.05 mm.',
        rerank_score=0.0,
    )
    defaults.update(overrides)
    return EvidenceHit(**defaults)


def _make_search_output(hits=None):
    from packages.application.use_cases.search_evidence import SearchEvidenceOutput

    return SearchEvidenceOutput(
        query='test query',
        intent='general',
        total_chunks_scanned=50,
        hits=hits or [_make_evidence_hit()],
        coverage_score=0.7,
        modality_hit_counts={'text': 1},
    )


def _make_citation_output(**overrides):
    from packages.application.use_cases.answer_question import AnswerCitationOutput

    defaults = dict(
        doc_id='manual_a',
        page=3,
        section_path='Section 1',
        figure_id=None,
        table_id=None,
        label='[1]',
    )
    defaults.update(overrides)
    return AnswerCitationOutput(**defaults)


def _make_answer_output(**overrides):
    from packages.application.use_cases.answer_question import AnswerQuestionOutput

    defaults = dict(
        query='test query',
        intent='general',
        status='ok',
        confidence=0.75,
        answer='The bearing preload is 0.05 mm.',
        follow_up_question=None,
        warnings=[],
        total_chunks_scanned=50,
        retrieved_chunk_ids=['chunk-1'],
        citations=[_make_citation_output()],
        reasoning_summary=None,
        abstain=False,
    )
    defaults.update(overrides)
    return AnswerQuestionOutput(**defaults)


def _make_catalog_record(**overrides):
    from packages.ports.document_catalog_port import DocumentCatalogRecord

    defaults = dict(
        doc_id='manual_a',
        title='Timken Bearing Manual',
        filename='timken.pdf',
        status='present',
    )
    defaults.update(overrides)
    return DocumentCatalogRecord(**defaults)


# ---------------------------------------------------------------------------
# search_manuals schema
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_manuals_schema():
    """search_manuals returns list of dicts with doc_id, page, content, type keys."""
    mock_output = _make_search_output()

    with (
        patch('apps.mcp.server.search_evidence_use_case', return_value=mock_output),
        patch('apps.mcp.server.FilesystemChunkQueryAdapter'),
        patch('apps.mcp.server.SimpleKeywordSearchAdapter'),
        patch('apps.mcp.server.HashVectorSearchAdapter'),
    ):
        from apps.mcp.server import _search_manuals_impl

        result = await _search_manuals_impl('test query')

    assert isinstance(result, list)
    assert len(result) == 1
    item = result[0]
    assert 'content' in item
    assert 'doc_id' in item
    assert 'page' in item
    assert 'type' in item


# ---------------------------------------------------------------------------
# answer_question schema
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_answer_question_schema():
    """answer_question returns dict with answer, confidence, abstain, citations keys."""
    mock_output = _make_answer_output()

    with (
        patch('apps.mcp.server.answer_question_use_case', return_value=mock_output),
        patch('apps.mcp.server.FilesystemChunkQueryAdapter'),
        patch('apps.mcp.server.SimpleKeywordSearchAdapter'),
        patch('apps.mcp.server.HashVectorSearchAdapter'),
    ):
        from apps.mcp.server import _answer_question_impl

        result = await _answer_question_impl('test query')

    assert isinstance(result, dict)
    assert 'answer' in result
    assert 'confidence' in result
    assert 'abstain' in result
    assert 'citations' in result


# ---------------------------------------------------------------------------
# list_manuals schema
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_manuals_schema():
    """list_manuals returns list with doc_id, title, status keys."""
    mock_record = _make_catalog_record()
    mock_catalog = MagicMock()
    mock_catalog.list_documents.return_value = [mock_record]

    with patch('apps.mcp.server.YamlDocumentCatalogAdapter', return_value=mock_catalog):
        from apps.mcp.server import _list_manuals_impl

        result = await _list_manuals_impl()

    assert isinstance(result, list)
    assert len(result) == 1
    item = result[0]
    assert 'doc_id' in item
    assert 'title' in item
    assert 'status' in item
    assert item['doc_id'] == 'manual_a'
    assert item['title'] == 'Timken Bearing Manual'
    assert item['status'] == 'present'
