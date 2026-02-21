from __future__ import annotations

from packages.domain.models import Citation


def format_citation(citation: Citation) -> str:
    parts = [f'{citation.doc_id} p.{citation.page}']
    if citation.section_path:
        parts.append(f'section {citation.section_path}')
    if citation.figure_id:
        parts.append(f'figure {citation.figure_id}')
    if citation.table_id:
        parts.append(f'table {citation.table_id}')
    return ' | '.join(parts)
