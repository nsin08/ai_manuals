"""Unit tests for AnswerQuestionOutput.confidence (float) and abstain — Phase 2."""
from __future__ import annotations

import packages.application.use_cases.answer_question as answer_question_module
from packages.adapters.retrieval.hash_vector_search_adapter import HashVectorSearchAdapter
from packages.adapters.retrieval.simple_keyword_search_adapter import SimpleKeywordSearchAdapter
from packages.application.use_cases.answer_question import (
    AnswerQuestionInput,
    AnswerQuestionOutput,
    answer_question_use_case,
)
from packages.application.use_cases.search_evidence import (
    EvidenceHit,
    SearchEvidenceInput,
    SearchEvidenceOutput,
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


def _make_chunk(chunk_id: str, content: str, doc_id: str = "d1") -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        doc_id=doc_id,
        content_type="text",
        page_start=1,
        page_end=1,
        content_text=content,
    )


def _make_evidence_output(coverage: float, snippets: list[str] | None = None) -> SearchEvidenceOutput:
    """Helper to build a controlled SearchEvidenceOutput for monkeypatching."""
    hits: list[EvidenceHit] = []
    for i, snippet in enumerate(snippets or []):
        hits.append(
            EvidenceHit(
                chunk_id=f"c{i}",
                doc_id="d1",
                content_type="text",
                page_start=1,
                page_end=1,
                section_path=None,
                figure_id=None,
                table_id=None,
                score=0.8,
                keyword_score=0.8,
                vector_score=0.8,
                snippet=snippet,
            )
        )
    return SearchEvidenceOutput(
        query="test query",
        intent="general",
        total_chunks_scanned=10,
        hits=hits,
        coverage_score=coverage,
        modality_hit_counts={"text": len(hits)},
    )


# ── confidence type ───────────────────────────────────────────────────────────
def test_confidence_is_float() -> None:
    """AnswerQuestionOutput.confidence must be a float in [0, 1]."""
    chunks = [_make_chunk("c1", "Motor torque specification is 45 Nm at rated load.")]
    output = answer_question_use_case(
        AnswerQuestionInput(query="What is the torque specification?", doc_id="d1"),
        chunk_query=_InMemoryChunkQuery(chunks),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
    )
    assert isinstance(output.confidence, float), (
        f"confidence should be float, got {type(output.confidence).__name__}"
    )
    assert 0.0 <= output.confidence <= 1.0


# ── abstain on low coverage ───────────────────────────────────────────────────
def test_abstain_on_low_coverage(monkeypatch) -> None:
    """abstain=True and confidence < 0.50 when evidence coverage is below threshold."""

    def _stub_search(*args, **kwargs):
        return _make_evidence_output(coverage=0.10, snippets=["some unrelated content here"])

    monkeypatch.setattr(answer_question_module, "search_evidence_use_case", _stub_search)

    output = answer_question_use_case(
        AnswerQuestionInput(query="gyroscope calibration frequency range", doc_id="d1"),
        chunk_query=_InMemoryChunkQuery([_make_chunk("c1", "unrelated text")]),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
    )

    assert output.abstain is True, "abstain should be True for coverage=0.10"
    assert output.confidence < 0.50, f"confidence {output.confidence} should be < 0.50"
    assert output.status == "not_found"
    assert any("Insufficient evidence" in w for w in output.warnings)


# ── no abstain on sufficient coverage ────────────────────────────────────────
def test_no_abstain_on_sufficient_coverage(monkeypatch) -> None:
    """abstain=False when coverage >= 0.50."""

    def _stub_search(*args, **kwargs):
        return _make_evidence_output(
            coverage=0.85,
            snippets=["torque specification is 45 Nm for this motor drive unit"],
        )

    monkeypatch.setattr(answer_question_module, "search_evidence_use_case", _stub_search)

    output = answer_question_use_case(
        AnswerQuestionInput(query="torque specification", doc_id="d1"),
        chunk_query=_InMemoryChunkQuery([_make_chunk("c1", "torque specification 45 Nm")]),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
    )

    assert output.abstain is False
    assert output.confidence >= 0.50


# ── confidence boundary at exactly 0.50 ──────────────────────────────────────
def test_abstain_boundary_at_0_50(monkeypatch) -> None:
    """Coverage of exactly 0.50 is sufficient (threshold is >=)."""

    def _stub_search(*args, **kwargs):
        return _make_evidence_output(
            coverage=0.50,
            snippets=["motor torque data here"],
        )

    monkeypatch.setattr(answer_question_module, "search_evidence_use_case", _stub_search)

    output = answer_question_use_case(
        AnswerQuestionInput(query="motor torque", doc_id="d1"),
        chunk_query=_InMemoryChunkQuery([_make_chunk("c1", "motor torque")]),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
    )

    assert output.abstain is False
    assert output.confidence == 0.50


# ── confidence reflects coverage_score linearly ───────────────────────────────
def test_confidence_maps_coverage_directly(monkeypatch) -> None:
    """confidence == coverage_score (clamped to [0,1], rounded to 4dp)."""
    target_coverage = 0.7321

    def _stub_search(*args, **kwargs):
        return _make_evidence_output(coverage=target_coverage, snippets=["motor torque spec"])

    monkeypatch.setattr(answer_question_module, "search_evidence_use_case", _stub_search)

    output = answer_question_use_case(
        AnswerQuestionInput(query="torque spec", doc_id="d1"),
        chunk_query=_InMemoryChunkQuery([_make_chunk("c1", "torque spec motor")]),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
    )

    assert output.confidence == round(target_coverage, 4)
