from __future__ import annotations

from packages.domain.models import Answer, Citation
from packages.domain.policies import has_minimum_citation_fields, is_answer_grounded



def test_answer_is_grounded_when_citations_present() -> None:
    answer = Answer(
        text='Sample answer',
        citations=[Citation(doc_id='doc-1', page=10)],
    )

    assert is_answer_grounded(answer)
    assert has_minimum_citation_fields(answer)



def test_answer_is_not_grounded_without_citations() -> None:
    answer = Answer(text='No evidence answer')

    assert not is_answer_grounded(answer)



def test_minimum_citation_fields_requires_positive_page() -> None:
    answer = Answer(
        text='Bad citation',
        citations=[Citation(doc_id='doc-1', page=0)],
    )

    assert not has_minimum_citation_fields(answer)
