"""Unit tests for _compute_evidence_coverage() — Phase 2."""
from __future__ import annotations

import pytest

from packages.application.use_cases.search_evidence import (
    EvidenceHit,
    _compute_evidence_coverage,
)


def _make_hit(snippet: str, content_type: str = "text") -> EvidenceHit:
    return EvidenceHit(
        chunk_id="c1",
        doc_id="d1",
        content_type=content_type,
        page_start=1,
        page_end=1,
        section_path=None,
        figure_id=None,
        table_id=None,
        score=1.0,
        keyword_score=1.0,
        vector_score=1.0,
        snippet=snippet,
    )


# ── basic cases ───────────────────────────────────────────────────────────────
def test_coverage_zero_for_empty_hits() -> None:
    result = _compute_evidence_coverage("torque specification", [])
    assert result == 0.0


def test_coverage_one_when_all_tokens_covered() -> None:
    hits = [_make_hit("the motor torque specification is 45 Nm")]
    result = _compute_evidence_coverage("torque specification", hits)
    assert result == 1.0


def test_coverage_partial_when_some_tokens_missing() -> None:
    hits = [_make_hit("torque value is listed here")]
    # tokens after stop-word removal: {"torque", "specification"}
    # "specification" is not in snippet → covered = 1/2 = 0.5
    result = _compute_evidence_coverage("torque specification", hits)
    assert result == 0.5


def test_coverage_returns_float() -> None:
    hits = [_make_hit("some content about the drive")]
    result = _compute_evidence_coverage("drive parameters", hits)
    assert isinstance(result, float)


def test_coverage_in_unit_range() -> None:
    hits = [_make_hit("motor speed rpm value")]
    result = _compute_evidence_coverage("motor speed rpm", hits)
    assert 0.0 <= result <= 1.0


def test_coverage_zero_for_trivial_stop_word_only_query() -> None:
    """Query that reduces to empty after stop-word removal should return 0.0.

    Returning 0.0 (not 1.0) prevents trivial queries from producing
    misleadingly high confidence via has_sufficient_evidence().
    """
    hits = [_make_hit("some content")]
    result = _compute_evidence_coverage("what is the", hits)
    assert result == 0.0


def test_coverage_aggregates_across_multiple_hits() -> None:
    """Tokens can appear in different hits; any hit contribution counts."""
    hits = [
        _make_hit("torque rating here"),
        _make_hit("specification sheet value"),
    ]
    result = _compute_evidence_coverage("torque specification", hits)
    assert result == 1.0


# ── rounding ──────────────────────────────────────────────────────────────────
def test_coverage_rounded_to_four_decimal_places() -> None:
    # 1/3 = 0.3333... rounded to 0.3333
    hits = [_make_hit("alpha content")]
    result = _compute_evidence_coverage("alpha beta gamma", hits)
    assert result == round(1 / 3, 4)


# ── word-boundary matching ────────────────────────────────────────────────────
def test_coverage_uses_word_boundary_not_substring() -> None:
    """Token 'ram' must not be counted as covered by a snippet containing 'program'."""
    hits = [_make_hit("program settings listed here")]
    # 'ram' is a word-token of 'program' via substring, but NOT a discrete word
    result = _compute_evidence_coverage("ram capacity", hits)
    # Neither 'ram' nor 'capacity' appears as a standalone word → 0.0
    assert result == 0.0


def test_coverage_exact_word_match_counts() -> None:
    """Token 'ram' is covered when it appears as a standalone word in the snippet."""
    hits = [_make_hit("total ram capacity is 512 mb")]
    result = _compute_evidence_coverage("ram capacity", hits)
    assert result == 1.0
