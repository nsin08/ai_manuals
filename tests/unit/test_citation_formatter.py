from __future__ import annotations

from packages.domain.citation_formatter import format_citation
from packages.domain.models import Citation


def test_format_citation_minimum_fields() -> None:
    citation = Citation(doc_id='rockwell_powerflex_40', page=73)
    assert format_citation(citation) == 'rockwell_powerflex_40 p.73'


def test_format_citation_includes_optional_fields() -> None:
    citation = Citation(
        doc_id='rockwell_powerflex_40',
        page=73,
        section_path='chapter-3/faults',
        figure_id='fig-2',
        table_id='tbl-5',
    )

    label = format_citation(citation)
    assert 'rockwell_powerflex_40 p.73' in label
    assert 'section chapter-3/faults' in label
    assert 'figure fig-2' in label
    assert 'table tbl-5' in label
