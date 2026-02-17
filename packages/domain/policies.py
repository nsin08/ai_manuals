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
