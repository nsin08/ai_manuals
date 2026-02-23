"""Unit tests — answer_question tool.

Verifies that answer_question delegates to AnswerQuestionUseCase and that
confidence is a float, abstain flag is propagated, and citations are returned.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from packages.application.use_cases.answer_question import (
    AnswerCitationOutput,
    AnswerQuestionOutput,
)


def _citation(**overrides) -> AnswerCitationOutput:
    defaults = dict(
        doc_id='manual_a',
        page=7,
        section_path='Section 2.1',
        figure_id=None,
        table_id=None,
        label='[1]',
    )
    defaults.update(overrides)
    return AnswerCitationOutput(**defaults)


def _answer_output(**overrides) -> AnswerQuestionOutput:
    defaults = dict(
        query='What is the bearing preload?',
        intent='spec',
        status='ok',
        confidence=0.82,
        answer='The bearing preload is 0.05 mm.',
        follow_up_question=None,
        warnings=[],
        total_chunks_scanned=80,
        retrieved_chunk_ids=['c1'],
        citations=[_citation()],
        reasoning_summary=None,
        abstain=False,
    )
    defaults.update(overrides)
    return AnswerQuestionOutput(**defaults)


# ---------------------------------------------------------------------------
# Delegation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_answer_delegates_to_use_case():
    """answer_question calls answer_question_use_case exactly once."""
    with (
        patch(
            'apps.mcp.server.answer_question_use_case',
            return_value=_answer_output(),
        ) as mock_uc,
        patch('apps.mcp.server.FilesystemChunkQueryAdapter'),
        patch('apps.mcp.server.SimpleKeywordSearchAdapter'),
        patch('apps.mcp.server.HashVectorSearchAdapter'),
    ):
        from apps.mcp.server import _answer_question_impl

        await _answer_question_impl('What is the bearing preload?')

    mock_uc.assert_called_once()
    assert mock_uc.call_args[0][0].query == 'What is the bearing preload?'


# ---------------------------------------------------------------------------
# Confidence is float
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_answer_returns_confidence_float():
    """answer_question returns confidence as a float in 0.0..1.0 range."""
    with (
        patch('apps.mcp.server.answer_question_use_case', return_value=_answer_output(confidence=0.82)),
        patch('apps.mcp.server.FilesystemChunkQueryAdapter'),
        patch('apps.mcp.server.SimpleKeywordSearchAdapter'),
        patch('apps.mcp.server.HashVectorSearchAdapter'),
    ):
        from apps.mcp.server import _answer_question_impl

        result = await _answer_question_impl('query')

    assert isinstance(result['confidence'], float)
    assert 0.0 <= result['confidence'] <= 1.0


# ---------------------------------------------------------------------------
# Abstain flag
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_answer_propagates_abstain_true():
    """answer_question propagates abstain=True when use case sets it."""
    with (
        patch(
            'apps.mcp.server.answer_question_use_case',
            return_value=_answer_output(
                abstain=True,
                status='not_found',
                confidence=0.2,
            ),
        ),
        patch('apps.mcp.server.FilesystemChunkQueryAdapter'),
        patch('apps.mcp.server.SimpleKeywordSearchAdapter'),
        patch('apps.mcp.server.HashVectorSearchAdapter'),
    ):
        from apps.mcp.server import _answer_question_impl

        result = await _answer_question_impl('unknown query')

    assert result['abstain'] is True


@pytest.mark.asyncio
async def test_answer_propagates_abstain_false():
    """answer_question propagates abstain=False for a grounded answer."""
    with (
        patch('apps.mcp.server.answer_question_use_case', return_value=_answer_output(abstain=False)),
        patch('apps.mcp.server.FilesystemChunkQueryAdapter'),
        patch('apps.mcp.server.SimpleKeywordSearchAdapter'),
        patch('apps.mcp.server.HashVectorSearchAdapter'),
    ):
        from apps.mcp.server import _answer_question_impl

        result = await _answer_question_impl('query')

    assert result['abstain'] is False


# ---------------------------------------------------------------------------
# Citations
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_answer_returns_citations():
    """answer_question returns citations list with doc_id, page, section_path, label."""
    citations = [
        _citation(doc_id='timken_a', page=5, section_path='Sec 1', label='[1]'),
        _citation(doc_id='timken_a', page=9, section_path='Sec 2', label='[2]'),
    ]
    with (
        patch(
            'apps.mcp.server.answer_question_use_case',
            return_value=_answer_output(citations=citations),
        ),
        patch('apps.mcp.server.FilesystemChunkQueryAdapter'),
        patch('apps.mcp.server.SimpleKeywordSearchAdapter'),
        patch('apps.mcp.server.HashVectorSearchAdapter'),
    ):
        from apps.mcp.server import _answer_question_impl

        result = await _answer_question_impl('query')

    assert len(result['citations']) == 2
    c = result['citations'][0]
    assert c['doc_id'] == 'timken_a'
    assert c['page'] == 5
    assert c['section_path'] == 'Sec 1'
    assert c['label'] == '[1]'
