from __future__ import annotations

from packages.domain.models import Answer



def is_answer_grounded(answer: Answer) -> bool:
    """Grounding policy: answer is grounded only if at least one citation is present."""
    return len(answer.citations) > 0



def has_minimum_citation_fields(answer: Answer) -> bool:
    """Every citation must include document id and positive page number."""
    for citation in answer.citations:
        if not citation.doc_id:
            return False
        if citation.page <= 0:
            return False
    return True


def _coverage_threshold_for_intent(intent: str | None) -> float:
    normalized = (intent or 'general').strip().lower()
    if normalized in {'table', 'diagram'}:
        return 0.35
    return 0.50


def has_sufficient_evidence(
    *,
    coverage: float,
    intent: str | None = None,
    has_citations: bool = False,
    best_hit_score: float = 0.0,
    best_keyword_score: float = 0.0,
) -> bool:
    """Evidence sufficiency policy used by abstain gating.

    Primary gate is coverage threshold by intent. For sparse table/diagram
    lookups and multi-facet prompts, allow a guarded rescue path when retrieval
    is strong and grounded citations exist.
    """
    threshold = _coverage_threshold_for_intent(intent)
    if coverage >= threshold:
        return True

    strong_retrieval = best_hit_score >= 0.55 or (
        best_hit_score >= 0.45 and best_keyword_score >= 0.45
    )
    if has_citations and strong_retrieval and coverage >= max(0.20, threshold - 0.20):
        return True
    return False
