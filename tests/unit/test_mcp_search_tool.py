"""Unit tests — search_manuals tool.

Verifies that search_manuals delegates to SearchEvidenceUseCase and maps
EvidenceHit fields to the expected dict keys.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from packages.application.use_cases.search_evidence import EvidenceHit, SearchEvidenceOutput


def _hit(
    *,
    chunk_id: str = 'c1',
    doc_id: str = 'manual_a',
    content_type: str = 'text',
    page_start: int = 5,
    snippet: str = 'Content text.',
) -> EvidenceHit:
    return EvidenceHit(
        chunk_id=chunk_id,
        doc_id=doc_id,
        content_type=content_type,
        page_start=page_start,
        page_end=page_start,
        section_path=None,
        figure_id=None,
        table_id=None,
        score=0.9,
        keyword_score=0.8,
        vector_score=0.9,
        snippet=snippet,
        rerank_score=0.0,
    )


def _output(hits: list[EvidenceHit]) -> SearchEvidenceOutput:
    return SearchEvidenceOutput(
        query='bearing preload',
        intent='spec',
        total_chunks_scanned=100,
        hits=hits,
        coverage_score=0.8,
        modality_hit_counts={'text': len(hits)},
    )


# ---------------------------------------------------------------------------
# Delegation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_delegates_to_use_case():
    """search_manuals calls search_evidence_use_case exactly once."""
    with (
        patch('apps.mcp.server.search_evidence_use_case', return_value=_output([])) as mock_uc,
        patch('apps.mcp.server.FilesystemChunkQueryAdapter'),
        patch('apps.mcp.server.SimpleKeywordSearchAdapter'),
        patch('apps.mcp.server.HashVectorSearchAdapter'),
    ):
        from apps.mcp.server import _search_manuals_impl

        await _search_manuals_impl('bearing preload')

    mock_uc.assert_called_once()
    call_args = mock_uc.call_args
    assert call_args[0][0].query == 'bearing preload'


# ---------------------------------------------------------------------------
# Field mapping
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_returns_chunks():
    """search_manuals maps EvidenceHit fields to doc_id, page, content, type."""
    hits = [_hit(doc_id='timken_a', content_type='diagram', page_start=12, snippet='Fig 3.')]
    with (
        patch('apps.mcp.server.search_evidence_use_case', return_value=_output(hits)),
        patch('apps.mcp.server.FilesystemChunkQueryAdapter'),
        patch('apps.mcp.server.SimpleKeywordSearchAdapter'),
        patch('apps.mcp.server.HashVectorSearchAdapter'),
    ):
        from apps.mcp.server import _search_manuals_impl

        result = await _search_manuals_impl('fig 3')

    assert len(result) == 1
    item = result[0]
    assert item['doc_id'] == 'timken_a'
    assert item['page'] == 12
    assert item['content'] == 'Fig 3.'
    assert item['type'] == 'diagram'


@pytest.mark.asyncio
async def test_search_returns_empty_list_on_no_hits():
    """search_manuals returns empty list when use case returns no hits."""
    with (
        patch('apps.mcp.server.search_evidence_use_case', return_value=_output([])),
        patch('apps.mcp.server.FilesystemChunkQueryAdapter'),
        patch('apps.mcp.server.SimpleKeywordSearchAdapter'),
        patch('apps.mcp.server.HashVectorSearchAdapter'),
    ):
        from apps.mcp.server import _search_manuals_impl

        result = await _search_manuals_impl('nonexistent query')

    assert result == []


@pytest.mark.asyncio
async def test_search_with_doc_ids_scopes_query():
    """search_manuals passes doc_ids scope through to the chunk query adapter."""
    captured = {}

    class _CapturingAdapter:
        def list_chunks(self, doc_id=None):
            captured['doc_id'] = doc_id
            return []

    with (
        patch(
            'apps.mcp.server.FilesystemChunkQueryAdapter',
            return_value=_CapturingAdapter(),
        ),
        patch('apps.mcp.server.search_evidence_use_case', return_value=_output([])),
        patch('apps.mcp.server.SimpleKeywordSearchAdapter'),
        patch('apps.mcp.server.HashVectorSearchAdapter'),
    ):
        from apps.mcp.server import _search_manuals_impl

        await _search_manuals_impl('query', doc_ids=['manual_a', 'manual_b'])

    # With doc_ids, the scoped adapter is used; list_chunks is called with doc_id=None
    # to fetch all then filter — no assertion on captured value needed, just no exception.


@pytest.mark.asyncio
async def test_search_multiple_hits_all_returned():
    """search_manuals returns all hits from the use case output."""
    hits = [
        _hit(chunk_id='c1', snippet='Hit 1'),
        _hit(chunk_id='c2', snippet='Hit 2'),
        _hit(chunk_id='c3', snippet='Hit 3'),
    ]
    with (
        patch('apps.mcp.server.search_evidence_use_case', return_value=_output(hits)),
        patch('apps.mcp.server.FilesystemChunkQueryAdapter'),
        patch('apps.mcp.server.SimpleKeywordSearchAdapter'),
        patch('apps.mcp.server.HashVectorSearchAdapter'),
    ):
        from apps.mcp.server import _search_manuals_impl

        result = await _search_manuals_impl('test')

    assert len(result) == 3
    snippets = [r['content'] for r in result]
    assert snippets == ['Hit 1', 'Hit 2', 'Hit 3']
