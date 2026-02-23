"""Unit tests for modality diversity enforcement and modality_hit_counts — Phase 2."""
from __future__ import annotations

from packages.adapters.retrieval.hash_vector_search_adapter import HashVectorSearchAdapter
from packages.adapters.retrieval.simple_keyword_search_adapter import SimpleKeywordSearchAdapter
from packages.application.use_cases.search_evidence import (
    SearchEvidenceInput,
    search_evidence_use_case,
)
from packages.domain.models import Chunk
from packages.ports.chunk_query_port import ChunkQueryPort


class _InMemoryChunkQuery(ChunkQueryPort):
    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks

    def list_chunks(self, doc_id: str | None = None) -> list[Chunk]:
        if doc_id is None:
            return list(self._chunks)
        return [c for c in self._chunks if c.doc_id == doc_id]


def _make_chunk(
    chunk_id: str,
    content: str,
    content_type: str = "text",
    doc_id: str = "d1",
    page: int = 1,
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        doc_id=doc_id,
        content_type=content_type,
        page_start=page,
        page_end=page,
        content_text=content,
    )


def _mixed_pool() -> list[Chunk]:
    """Six chunks: 4 text + 2 table, all containing overlapping terms so they score."""
    base = "motor rated load specification torque value parameter"
    return [
        _make_chunk("t1", f"text chunk one {base}", content_type="text", page=1),
        _make_chunk("t2", f"text chunk two {base}", content_type="text", page=2),
        _make_chunk("t3", f"text chunk three {base}", content_type="text", page=3),
        _make_chunk("t4", f"text chunk four {base}", content_type="text", page=4),
        _make_chunk("tb1", f"table row one {base}", content_type="table", page=5),
        _make_chunk("tb2", f"table row two {base}", content_type="table", page=6),
    ]


# ── modality_hit_counts field ─────────────────────────────────────────────────
def test_search_output_has_modality_counts() -> None:
    """SearchEvidenceOutput.modality_hit_counts must be a dict with content_type keys."""
    chunks = _mixed_pool()
    result = search_evidence_use_case(
        SearchEvidenceInput(query="motor torque parameter", top_n=4),
        chunk_query=_InMemoryChunkQuery(chunks),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
    )

    assert isinstance(result.modality_hit_counts, dict), "modality_hit_counts must be a dict"
    assert len(result.modality_hit_counts) > 0, "modality_hit_counts must not be empty when hits exist"
    # Keys must be content_type strings not modality buckets
    for key in result.modality_hit_counts:
        assert isinstance(key, str)
    # Values must be positive ints
    for val in result.modality_hit_counts.values():
        assert isinstance(val, int) and val > 0


def test_modality_hit_counts_sum_equals_returned_hits() -> None:
    """Sum of modality_hit_counts values must equal len(hits)."""
    chunks = _mixed_pool()
    result = search_evidence_use_case(
        SearchEvidenceInput(query="motor torque parameter", top_n=5),
        chunk_query=_InMemoryChunkQuery(chunks),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
    )

    assert sum(result.modality_hit_counts.values()) == len(result.hits)


# ── diversity enforcement ─────────────────────────────────────────────────────
def test_top5_has_diverse_modalities_when_pool_allows() -> None:
    """When pool has ≥2 content_types, the returned top results must contain ≥2 types."""
    chunks = _mixed_pool()
    result = search_evidence_use_case(
        SearchEvidenceInput(query="motor torque parameter specification", top_n=5),
        chunk_query=_InMemoryChunkQuery(chunks),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
    )

    if len(result.hits) >= 2:
        content_types_in_result = {h.content_type for h in result.hits}
        assert len(content_types_in_result) >= 2, (
            f"Expected ≥2 distinct content_types in top results, got: {content_types_in_result}"
        )


def test_diversity_not_enforced_below_5_hits() -> None:
    """With fewer than 5 hits in pool, diversity promotion does not fire — no error raised."""
    chunks = [
        _make_chunk("t1", "motor parameter value", content_type="text"),
        _make_chunk("t2", "motor specification", content_type="text"),
    ]
    result = search_evidence_use_case(
        SearchEvidenceInput(query="motor parameter", top_n=5),
        chunk_query=_InMemoryChunkQuery(chunks),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
    )
    # No assertion on diversity — just ensure no error and valid output structure
    assert isinstance(result.modality_hit_counts, dict)


def test_diversity_not_enforced_for_procedure_intent() -> None:
    """Procedure intent bypasses diversity enforcement — text-only result is acceptable."""
    chunks = [
        _make_chunk(f"t{i}", f"install steps commissioning startup setup procedure chunk {i}", content_type="text")
        for i in range(6)
    ]
    result = search_evidence_use_case(
        SearchEvidenceInput(query="how to install and commissioning steps", top_n=5),
        chunk_query=_InMemoryChunkQuery(chunks),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
    )

    assert result.intent == "procedure"
    # No diversity constraint for procedure — all text is fine
    assert isinstance(result.modality_hit_counts, dict)


# ── coverage_score field ──────────────────────────────────────────────────────
def test_coverage_score_present_in_output() -> None:
    """SearchEvidenceOutput must expose coverage_score as float in [0, 1]."""
    chunks = [_make_chunk("c1", "motor torque is 45 Nm at rated load")]
    result = search_evidence_use_case(
        SearchEvidenceInput(query="motor torque", top_n=3),
        chunk_query=_InMemoryChunkQuery(chunks),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
    )

    assert isinstance(result.coverage_score, float)
    assert 0.0 <= result.coverage_score <= 1.0


def test_empty_query_returns_zero_coverage() -> None:
    """Empty query must return 0.0 coverage and empty modality_hit_counts."""
    result = search_evidence_use_case(
        SearchEvidenceInput(query="   ", top_n=5),
        chunk_query=_InMemoryChunkQuery([]),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
    )

    assert result.coverage_score == 0.0
    assert result.modality_hit_counts == {}
