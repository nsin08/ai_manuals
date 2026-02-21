from __future__ import annotations

from packages.adapters.agentic.noop_planner_adapter import NoopPlannerAdapter


def test_noop_planner_adds_modality_focused_step_for_multimodal_query() -> None:
    planner = NoopPlannerAdapter()
    steps = planner.create_plan(
        query='Use figure callouts and table values to explain wiring setup',
        intent='general',
        doc_id='doc-x',
        max_steps=4,
    )
    assert len(steps) >= 3
    assert steps[0].tool_name == 'search_evidence'
    assert any('focused retrieval pass' in step.objective for step in steps if step.tool_name == 'search_evidence')
    assert steps[-1].tool_name == 'draft_answer'


def test_noop_planner_respects_budget() -> None:
    planner = NoopPlannerAdapter()
    steps = planner.create_plan(
        query='compare figure and table results',
        intent='general',
        doc_id=None,
        max_steps=2,
    )
    assert len(steps) == 2
    assert steps[0].tool_name == 'search_evidence'
    assert steps[1].tool_name in {'search_evidence', 'draft_answer'}
