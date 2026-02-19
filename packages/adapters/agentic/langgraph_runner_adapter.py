from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from packages.ports.agent_trace_port import AgentTracePort
from packages.ports.llm_port import LlmEvidence, LlmPort
from packages.ports.planner_port import PlanStep, PlannerPort
from packages.ports.state_graph_runner_port import GraphRunLimits, GraphRunOutput, StateGraphRunnerPort
from packages.ports.tool_executor_port import ToolExecutionResult, ToolExecutorPort


class LangGraphRunnerAdapter(StateGraphRunnerPort):
    def run(
        self,
        *,
        initial_state: dict[str, Any],
        limits: GraphRunLimits,
        planner: PlannerPort,
        tool_executor: ToolExecutorPort,
        llm: LlmPort | None,
        trace_logger: AgentTracePort | None = None,
    ) -> GraphRunOutput:
        prepared = self._prepare_state(initial_state)
        start_monotonic = time.monotonic()

        try:
            return self._run_with_langgraph(
                initial_state=prepared,
                limits=limits,
                planner=planner,
                tool_executor=tool_executor,
                llm=llm,
                trace_logger=trace_logger,
                start_monotonic=start_monotonic,
            )
        except Exception:
            return self._run_without_langgraph(
                initial_state=prepared,
                limits=limits,
                planner=planner,
                tool_executor=tool_executor,
                llm=llm,
                trace_logger=trace_logger,
                start_monotonic=start_monotonic,
            )

    @staticmethod
    def _prepare_state(payload: dict[str, Any]) -> dict[str, Any]:
        state = dict(payload)
        state.setdefault('query', '')
        state.setdefault('doc_id', None)
        state.setdefault('intent', 'general')
        state.setdefault('top_n', 6)
        state.setdefault('top_k_keyword', 20)
        state.setdefault('top_k_vector', 20)
        state.setdefault('rerank_pool_size', 24)
        state.setdefault('plan_steps', [])
        state.setdefault('tool_calls', [])
        state.setdefault('evidence_hits', [])
        state.setdefault('retrieved_chunk_ids', [])
        state.setdefault('warnings', [])
        state.setdefault('errors', [])
        state.setdefault('answer_draft', '')
        state.setdefault('reasoning_summary', None)
        state.setdefault('status', 'ok')
        state.setdefault('total_chunks_scanned', 0)
        state.setdefault('_done', False)
        state.setdefault('_iterations', 0)
        state.setdefault('_tool_calls', 0)
        state.setdefault('_plan_index', 0)
        state.setdefault('_terminated_reason', 'completed')
        return state

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).isoformat()

    def _log_trace(
        self,
        *,
        trace_logger: AgentTracePort | None,
        event: str,
        payload: dict[str, Any],
    ) -> None:
        if trace_logger is None:
            return
        trace_logger.log(
            {
                'ts': self._now_iso(),
                'event': event,
                **payload,
            }
        )

    def _run_with_langgraph(
        self,
        *,
        initial_state: dict[str, Any],
        limits: GraphRunLimits,
        planner: PlannerPort,
        tool_executor: ToolExecutorPort,
        llm: LlmPort | None,
        trace_logger: AgentTracePort | None,
        start_monotonic: float,
    ) -> GraphRunOutput:
        from langgraph.graph import END, StateGraph  # type: ignore
        timer = {'start': start_monotonic}

        def plan_node(state: dict[str, Any]) -> dict[str, Any]:
            planned = self._apply_plan(
                state=state,
                planner=planner,
                limits=limits,
                trace_logger=trace_logger,
            )
            # Timeout budget applies to execution loop; planner latency should not force instant timeout.
            timer['start'] = time.monotonic()
            return planned

        def execute_node(state: dict[str, Any]) -> dict[str, Any]:
            return self._execute_step(
                state=state,
                limits=limits,
                tool_executor=tool_executor,
                trace_logger=trace_logger,
                start_monotonic=timer['start'],
            )

        def route_after_execute(state: dict[str, Any]) -> str:
            return 'finalize' if bool(state.get('_done')) else 'execute'

        def finalize_node(state: dict[str, Any]) -> dict[str, Any]:
            return self._finalize_state(state=state, llm=llm, trace_logger=trace_logger)

        graph = StateGraph(dict)
        graph.add_node('plan', plan_node)
        graph.add_node('execute', execute_node)
        graph.add_node('finalize', finalize_node)
        graph.set_entry_point('plan')
        graph.add_edge('plan', 'execute')
        graph.add_conditional_edges(
            'execute',
            route_after_execute,
            {
                'execute': 'execute',
                'finalize': 'finalize',
            },
        )
        graph.add_edge('finalize', END)

        compiled = graph.compile()
        final_state = dict(compiled.invoke(initial_state))
        return self._as_output(final_state)

    def _run_without_langgraph(
        self,
        *,
        initial_state: dict[str, Any],
        limits: GraphRunLimits,
        planner: PlannerPort,
        tool_executor: ToolExecutorPort,
        llm: LlmPort | None,
        trace_logger: AgentTracePort | None,
        start_monotonic: float,
    ) -> GraphRunOutput:
        state = self._apply_plan(
            state=initial_state,
            planner=planner,
            limits=limits,
            trace_logger=trace_logger,
        )
        execution_start = time.monotonic()

        while not bool(state.get('_done')):
            state = self._execute_step(
                state=state,
                limits=limits,
                tool_executor=tool_executor,
                trace_logger=trace_logger,
                start_monotonic=execution_start,
            )

        state = self._finalize_state(state=state, llm=llm, trace_logger=trace_logger)
        return self._as_output(state)

    def _apply_plan(
        self,
        *,
        state: dict[str, Any],
        planner: PlannerPort,
        limits: GraphRunLimits,
        trace_logger: AgentTracePort | None,
    ) -> dict[str, Any]:
        out = dict(state)
        max_steps = max(1, min(limits.max_iterations, limits.max_tool_calls))
        plan = planner.create_plan(
            query=str(out.get('query') or ''),
            intent=str(out.get('intent') or 'general'),
            doc_id=out.get('doc_id'),
            max_steps=max_steps,
        )
        if not any(row.tool_name == 'search_evidence' for row in plan):
            # Retrieval must happen before drafting to keep grounded behavior reliable.
            plan = [
                PlanStep(
                    step_id='auto_search',
                    tool_name='search_evidence',
                    objective='Retrieve evidence before drafting the answer.',
                ),
                *plan,
            ]
            plan = plan[:max_steps]
        out['plan_steps'] = [
            {
                'step_id': row.step_id,
                'tool_name': row.tool_name,
                'objective': row.objective,
            }
            for row in plan
        ]
        out['_plan_index'] = 0
        out['_done'] = not bool(out['plan_steps'])
        if out['_done']:
            out['_terminated_reason'] = 'empty_plan'

        self._log_trace(
            trace_logger=trace_logger,
            event='plan_generated',
            payload={
                'query': out.get('query'),
                'doc_id': out.get('doc_id'),
                'plan_steps': out['plan_steps'],
            },
        )
        return out

    @staticmethod
    def _remaining_seconds(*, limits: GraphRunLimits, start_monotonic: float) -> float:
        elapsed = time.monotonic() - start_monotonic
        return limits.timeout_seconds - elapsed

    def _build_tool_args(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            'query': state.get('query'),
            'doc_id': state.get('doc_id'),
            'top_n': state.get('top_n'),
            'top_k_keyword': state.get('top_k_keyword'),
            'top_k_vector': state.get('top_k_vector'),
            'rerank_pool_size': state.get('rerank_pool_size'),
        }

    @staticmethod
    def _merge_hits(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_chunk: dict[str, dict[str, Any]] = {}

        def _score(row: dict[str, Any]) -> float:
            value = row.get('score')
            try:
                return float(value)
            except Exception:
                return 0.0

        for row in existing:
            chunk_id = str(row.get('chunk_id') or '')
            if not chunk_id:
                continue
            by_chunk[chunk_id] = dict(row)

        for row in incoming:
            chunk_id = str(row.get('chunk_id') or '')
            if not chunk_id:
                continue
            current = by_chunk.get(chunk_id)
            if current is None or _score(row) > _score(current):
                by_chunk[chunk_id] = dict(row)

        merged = list(by_chunk.values())
        merged.sort(key=_score, reverse=True)
        return merged

    def _handle_tool_result(
        self,
        *,
        state: dict[str, Any],
        result: ToolExecutionResult,
    ) -> dict[str, Any]:
        out = dict(state)
        call_record = {
            'tool_name': result.tool_name,
            'success': result.success,
            'error': result.error,
            'payload_keys': sorted(result.payload.keys()) if result.payload else [],
        }
        out['tool_calls'] = list(out.get('tool_calls') or []) + [call_record]

        if not result.success:
            out['errors'] = list(out.get('errors') or []) + [result.error or f'{result.tool_name} failed']
            detail = result.error or 'unknown error'
            out['warnings'] = list(out.get('warnings') or []) + [
                f'Tool failed: {result.tool_name}: {detail}'
            ]
            return out

        if result.tool_name == 'search_evidence':
            payload = result.payload
            hits = payload.get('hits') if isinstance(payload.get('hits'), list) else []
            merged = self._merge_hits(
                list(out.get('evidence_hits') or []),
                [row for row in hits if isinstance(row, dict)],
            )
            top_n = int(out.get('top_n') or 6)
            out['evidence_hits'] = merged[: max(top_n * 2, top_n)]
            out['retrieved_chunk_ids'] = [str(row.get('chunk_id')) for row in out['evidence_hits'] if row.get('chunk_id')]
            out['total_chunks_scanned'] = max(
                int(out.get('total_chunks_scanned') or 0),
                int(payload.get('total_chunks_scanned') or 0),
            )
            if payload.get('intent'):
                out['intent'] = str(payload.get('intent'))

        if result.tool_name == 'draft_answer':
            draft = result.payload.get('answer_draft')
            if isinstance(draft, str) and draft.strip():
                out['answer_draft'] = draft.strip()

        return out

    def _execute_step(
        self,
        *,
        state: dict[str, Any],
        limits: GraphRunLimits,
        tool_executor: ToolExecutorPort,
        trace_logger: AgentTracePort | None,
        start_monotonic: float,
    ) -> dict[str, Any]:
        out = dict(state)

        iterations = int(out.get('_iterations') or 0)
        tool_calls = int(out.get('_tool_calls') or 0)
        plan_index = int(out.get('_plan_index') or 0)
        plan_steps = list(out.get('plan_steps') or [])

        if iterations >= limits.max_iterations:
            out['_done'] = True
            out['_terminated_reason'] = 'max_iterations'
            return out

        if tool_calls >= limits.max_tool_calls:
            out['_done'] = True
            out['_terminated_reason'] = 'max_tool_calls'
            return out

        if plan_index >= len(plan_steps):
            out['_done'] = True
            out['_terminated_reason'] = 'completed'
            return out

        if self._remaining_seconds(limits=limits, start_monotonic=start_monotonic) <= 0:
            out['_done'] = True
            out['_terminated_reason'] = 'timeout'
            return out

        step = plan_steps[plan_index]
        tool_name = str(step.get('tool_name') or '').strip()
        if not tool_name:
            out['_plan_index'] = plan_index + 1
            out['_iterations'] = iterations + 1
            return out

        args = self._build_tool_args(out)
        result = tool_executor.execute(tool_name=tool_name, arguments=args)
        out = self._handle_tool_result(state=out, result=result)

        out['_plan_index'] = plan_index + 1
        out['_iterations'] = iterations + 1
        out['_tool_calls'] = tool_calls + 1
        out['_done'] = int(out.get('_plan_index') or 0) >= len(plan_steps)
        if out['_done']:
            out['_terminated_reason'] = 'completed'

        self._log_trace(
            trace_logger=trace_logger,
            event='tool_executed',
            payload={
                'query': out.get('query'),
                'step': step,
                'argument_keys': sorted(args.keys()),
                'success': result.success,
                'error': result.error,
                'tool_calls': out.get('_tool_calls'),
                'iterations': out.get('_iterations'),
            },
        )
        return out

    @staticmethod
    def _compose_from_hits(hits: list[dict[str, Any]]) -> str:
        points: list[str] = []
        for row in hits[:3]:
            snippet = str(row.get('snippet') or '').strip()
            if snippet:
                points.append(snippet)
        if not points:
            return 'Not found in provided manuals based on retrieved evidence.'
        if len(points) == 1:
            return points[0]
        return '\n'.join(f'{idx + 1}. {value}' for idx, value in enumerate(points))

    @staticmethod
    def _llm_evidence_from_hits(hits: list[dict[str, Any]]) -> list[LlmEvidence]:
        out: list[LlmEvidence] = []
        for row in hits[:12]:
            out.append(
                LlmEvidence(
                    doc_id=str(row.get('doc_id') or ''),
                    page_start=int(row.get('page_start') or 0),
                    page_end=int(row.get('page_end') or 0),
                    content_type=str(row.get('content_type') or 'text'),
                    text=str(row.get('snippet') or ''),
                )
            )
        return out

    @staticmethod
    def _confidence(hits: list[dict[str, Any]], status: str) -> str:
        if status != 'ok' or not hits:
            return 'low'
        try:
            best = float(hits[0].get('score') or 0.0)
        except Exception:
            best = 0.0
        if best >= 0.60:
            return 'high'
        if best >= 0.35:
            return 'medium'
        return 'low'

    def _finalize_state(
        self,
        *,
        state: dict[str, Any],
        llm: LlmPort | None,
        trace_logger: AgentTracePort | None,
    ) -> dict[str, Any]:
        out = dict(state)
        hits = [row for row in list(out.get('evidence_hits') or []) if isinstance(row, dict)]
        draft = str(out.get('answer_draft') or '').strip()

        if not draft and hits and llm is not None:
            try:
                draft = llm.generate_answer(
                    query=str(out.get('query') or ''),
                    intent=str(out.get('intent') or 'general'),
                    evidence=self._llm_evidence_from_hits(hits),
                ).strip()
            except Exception as exc:
                out['warnings'] = list(out.get('warnings') or []) + [f'LLM draft failed: {type(exc).__name__}']

        if not draft:
            draft = self._compose_from_hits(hits)

        status = str(out.get('status') or 'ok')
        if not hits and status == 'ok':
            status = 'not_found'

        out['answer_draft'] = draft
        out['status'] = status
        out['confidence'] = self._confidence(hits, status)

        if not out.get('reasoning_summary'):
            plan_tools = [str(row.get('tool_name')) for row in list(out.get('plan_steps') or []) if row.get('tool_name')]
            out['reasoning_summary'] = f"Plan executed with tools: {', '.join(plan_tools)}" if plan_tools else None

        self._log_trace(
            trace_logger=trace_logger,
            event='graph_finalized',
            payload={
                'query': out.get('query'),
                'status': out.get('status'),
                'confidence': out.get('confidence'),
                'iterations': out.get('_iterations'),
                'tool_calls': out.get('_tool_calls'),
                'terminated_reason': out.get('_terminated_reason'),
            },
        )
        return out

    @staticmethod
    def _as_output(state: dict[str, Any]) -> GraphRunOutput:
        public_state = dict(state)
        iterations = int(public_state.pop('_iterations', 0) or 0)
        tool_calls = int(public_state.pop('_tool_calls', 0) or 0)
        terminated_reason = str(public_state.pop('_terminated_reason', 'completed'))
        public_state.pop('_done', None)
        public_state.pop('_plan_index', None)
        return GraphRunOutput(
            state=public_state,
            iterations=iterations,
            tool_calls=tool_calls,
            terminated_reason=terminated_reason,
        )
