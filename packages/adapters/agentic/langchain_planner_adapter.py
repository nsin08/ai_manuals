from __future__ import annotations

import json
from typing import Any

from packages.adapters.agentic.noop_planner_adapter import NoopPlannerAdapter
from packages.ports.planner_port import PlanStep, PlannerPort


class LangChainPlannerAdapter(PlannerPort):
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
    ) -> None:
        self._base_url = base_url
        self._model = model
        self._fallback = NoopPlannerAdapter()
        self._chat_model = self._build_chat_model(base_url=base_url, model=model)

    def _build_chat_model(self, *, base_url: str, model: str) -> Any | None:
        try:
            from langchain_ollama import ChatOllama  # type: ignore

            return ChatOllama(
                base_url=base_url,
                model=model,
                temperature=0,
            )
        except Exception:
            return None

    @staticmethod
    def _extract_first_json_array(text: str) -> list[dict[str, Any]] | None:
        start = text.find('[')
        end = text.rfind(']')
        if start < 0 or end <= start:
            return None
        raw = text[start : end + 1]
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, list):
            return None
        out: list[dict[str, Any]] = []
        for row in parsed:
            if isinstance(row, dict):
                out.append(row)
        return out

    @staticmethod
    def _as_plan_steps(rows: list[dict[str, Any]], max_steps: int) -> list[PlanStep]:
        out: list[PlanStep] = []
        for idx, row in enumerate(rows, start=1):
            tool_name = str(row.get('tool_name') or '').strip()
            if not tool_name:
                continue
            objective = str(row.get('objective') or '').strip() or f'Run {tool_name}'
            step_id = str(row.get('step_id') or f'step_{idx}')
            out.append(PlanStep(step_id=step_id, tool_name=tool_name, objective=objective))
            if len(out) >= max_steps:
                break
        return out

    def create_plan(
        self,
        *,
        query: str,
        intent: str,
        doc_id: str | None,
        max_steps: int,
    ) -> list[PlanStep]:
        budget = max(max_steps, 1)
        if self._chat_model is None:
            return self._fallback.create_plan(
                query=query,
                intent=intent,
                doc_id=doc_id,
                max_steps=budget,
            )

        prompt = (
            'You are a planning component for a manual QA agent.\n'
            'Return ONLY a JSON array of steps.\n'
            'Each step object must have: step_id, tool_name, objective.\n'
            'Allowed tool_name values: search_evidence, draft_answer.\n'
            f'Max steps: {budget}.\n'
            f'Intent: {intent}.\n'
            f'Doc filter: {doc_id or "none"}.\n'
            f'Question: {query}\n'
        )

        try:
            response = self._chat_model.invoke(prompt)
            text = str(getattr(response, 'content', response))
            rows = self._extract_first_json_array(text)
            if rows is None:
                return self._fallback.create_plan(
                    query=query,
                    intent=intent,
                    doc_id=doc_id,
                    max_steps=budget,
                )
            parsed = self._as_plan_steps(rows, budget)
            if parsed:
                return parsed
        except Exception:
            pass

        return self._fallback.create_plan(
            query=query,
            intent=intent,
            doc_id=doc_id,
            max_steps=budget,
        )
