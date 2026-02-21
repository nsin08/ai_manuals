from __future__ import annotations

from packages.ports.planner_port import PlanStep, PlannerPort


class NoopPlannerAdapter(PlannerPort):
    def create_plan(
        self,
        *,
        query: str,
        intent: str,
        doc_id: str | None,
        max_steps: int,
    ) -> list[PlanStep]:
        _ = intent, doc_id
        budget = max(max_steps, 1)
        lower = query.lower()
        is_comparison = any(token in lower for token in ('compare', 'difference', ' versus ', ' vs '))
        wants_visual = any(
            token in lower
            for token in (
                'diagram',
                'figure',
                'image',
                'callout',
                'visual',
                'multimodal',
            )
        )
        wants_table = any(token in lower for token in ('table', 'spec', 'parameter', 'setting'))

        steps: list[PlanStep] = [
            PlanStep(
                step_id='step_1',
                tool_name='search_evidence',
                objective='Retrieve top evidence for the query.',
            )
        ]

        if budget >= len(steps) + 1 and (wants_visual or wants_table):
            focus = 'visual and table evidence' if wants_visual and wants_table else (
                'visual evidence' if wants_visual else 'table evidence'
            )
            steps.append(
                PlanStep(
                    step_id=f'step_{len(steps) + 1}',
                    tool_name='search_evidence',
                    objective=f'Run a focused retrieval pass for {focus}.',
                )
            )

        if budget >= len(steps) + 1 and is_comparison:
            steps.append(
                PlanStep(
                    step_id=f'step_{len(steps) + 1}',
                    tool_name='search_evidence',
                    objective='Run a second retrieval pass to improve comparison coverage.',
                )
            )

        if budget >= len(steps) + 1:
            steps.append(
                PlanStep(
                    step_id=f'step_{len(steps) + 1}',
                    tool_name='draft_answer',
                    objective='Draft grounded answer from retrieved evidence.',
                )
            )

        return steps[:budget]
