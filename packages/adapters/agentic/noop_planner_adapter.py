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

        steps: list[PlanStep] = [
            PlanStep(
                step_id='step_1',
                tool_name='search_evidence',
                objective='Retrieve top evidence for the query.',
            )
        ]

        if budget >= 3 and any(token in lower for token in ('compare', 'difference', ' versus ', ' vs ')):
            steps.append(
                PlanStep(
                    step_id='step_2',
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
