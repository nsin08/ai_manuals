# Full Agentic Sprint Plan (LangChain + LangGraph)

Version: 1.0
Date: 2026-02-19
Branch: feature/full-agentic-mode
Goal: Introduce full agentic orchestration with LangGraph while preserving local-first, grounded answering, and strict hexagonal boundaries.

## Definition of Done

- Agentic flow supports multi-step planning -> tool execution -> grounded synthesis for complex questions.
- `packages/application` orchestrates through ports only; no LangChain/LangGraph imports outside adapters.
- Existing response contract preserved (`ok`, `not_found`, `needs_follow_up`, `partial`) with citations.
- Golden and reliability metrics do not regress; targeted gains on multi-hop/procedure questions.
- Traceability captured for every step (plan, tool calls, evidence used, final answer decision).

## Architecture Guardrails (Non-Negotiable)

- Hexagonal rule remains enforced:
  - `domain` and `application` do not import `adapters` or framework-specific modules.
  - LangChain/LangGraph are infrastructure details in `packages/adapters/agentic/*`.
- Application depends on abstract ports such as:
  - `PlannerPort`
  - `ToolExecutorPort`
  - `StateGraphRunnerPort`
  - existing retrieval/llm/reranker/vision ports
- Agent state is a typed application model (plain dataclass/pydantic in `packages/application`), not framework-native state objects leaked across layers.
- API/UI continue calling a use-case (`answer_question`) and remain unaware of orchestration framework internals.

## Scope

In scope:
- LangGraph-backed state machine for question answering.
- LangChain tool wrappers around existing application capabilities.
- Multi-step reasoning for decomposition, evidence gathering, and answer drafting.
- Deterministic fallback path when graph/tool execution fails.
- Agent trace logging and evaluation extensions.

Out of scope (this sprint):
- Autonomous background task scheduling beyond request lifecycle.
- Multi-agent swarm with separate model providers.
- Cloud-managed orchestration runtime.

## Proposed Ports and Adapters

New ports (`packages/ports`):
- `planner_port.py`: produce plan steps from user query + context.
- `tool_executor_port.py`: execute named tools with validated args.
- `state_graph_runner_port.py`: run graph transitions over application state.
- `agent_trace_port.py`: persist step-level trace events.

New adapters (`packages/adapters/agentic`):
- `langgraph_runner_adapter.py`: compiles and runs LangGraph graph.
- `langchain_planner_adapter.py`: prompt/model driven plan generation.
- `langchain_tool_executor_adapter.py`: LangChain tool binding to retrieval/ingestion/query helpers.
- `jsonl_agent_trace_logger_adapter.py`: writes to `.context/reports/agent_traces.jsonl`.

## Application Changes

Use-case evolution (`packages/application/use_cases/answer_question.py`):
- Add an agentic mode branch behind config (`USE_AGENTIC_MODE=true|false`).
- Agentic branch flow:
  1. classify intent/complexity
  2. produce plan
  3. run graph loop (retrieve -> inspect -> optionally refine query -> draft)
  4. run grounding/citation checks
  5. emit standard response contract
- Fallback branch:
  - if planner/graph/tool stage fails or exceeds budget -> run existing deterministic pipeline.

State model (`packages/application/agentic/state.py`):
- `question`, `intent`, `plan_steps`, `tool_calls`, `evidence_pool`, `draft_answer`, `status`, `confidence`, `trace_id`, `errors`.

Policy updates:
- Budget limits: max graph iterations, max tool calls, timeout budget.
- Guardrails: no final answer without evidence; force `partial`/`not_found` when unsupported.

## Sprint Breakdown

## Sprint A: Contracts and Skeleton

Deliverables:
- Add new ports and application state model.
- Add config toggles and execution budgets.
- Add boundary tests preventing LangChain/LangGraph imports in application/domain.

Acceptance checks:
- `answer_question` compiles with `USE_AGENTIC_MODE=false` unchanged behavior.
- Static/dependency test confirms architecture boundaries.

Evidence:
- `tests/unit/test_architecture_boundaries.py`
- `.context/reports/agentic_contract_check.json`

## Sprint B: LangGraph Orchestration MVP

Deliverables:
- Implement graph nodes: `plan`, `retrieve`, `evaluate_evidence`, `draft`, `grounding_gate`, `finalize`.
- Implement planner + tool executor adapters.
- Integrate trace logger for node transitions and tool outcomes.

Acceptance checks:
- Agent can answer at least one multi-step query requiring >1 retrieval pass.
- On node/tool failure, fallback path returns valid response contract.

Evidence:
- `tests/unit/test_agentic_graph_runner.py`
- `.context/reports/agentic_trace_samples.json`

## Sprint C: Tooling Depth and Reliability

Deliverables:
- Tool set includes: `search_evidence`, `explain_sources`, optional `run_followup_clarifier`.
- Add argument schemas and validation for tool invocation.
- Add retry/backoff policy per node with capped attempts.

Acceptance checks:
- Invalid tool args never crash flow; graph records controlled error and continues/falls back.
- Multi-hop golden subset improves over deterministic baseline.

Evidence:
- `tests/unit/test_agentic_tool_validation.py`
- `.context/reports/agentic_vs_baseline_subset.json`

## Sprint D: Evaluation, UI Signals, and Gate

Deliverables:
- Extend eval script to report agentic metrics:
  - tool-call precision
  - grounded finalization rate
  - fallback rate
  - average graph depth
- UI/API include optional `reasoning_summary` and `trace_id` (debug/admin view).
- Add regression gate threshold for agentic mode.

Acceptance checks:
- CI gate fails if grounded finalization or pass rate drops below threshold.
- UI keeps concise answer-first experience; diagnostics remain optional.

Evidence:
- `scripts/run_reliability_eval.py` (extended)
- `.context/reports/agentic_eval_summary.json`

## Evaluation Strategy

Baseline comparison:
- Compare deterministic vs agentic on same golden subset (focus: procedure, troubleshooting, comparison).

Primary KPIs:
- Golden pass rate delta.
- Citation presence and precision.
- False `not_found` and false `ok` rates.
- Median latency and P95 latency impact.
- Fallback rate (target low, non-zero acceptable).

## Risks and Mitigations

- Framework leakage into core layers.
  - Mitigation: port-first design + boundary tests.
- Agent loops causing latency/cost spikes.
  - Mitigation: strict budgets and loop guards.
- Hallucinated tool usage or unsupported claims.
  - Mitigation: grounding gate + evidence-required finalization.
- Debug complexity.
  - Mitigation: structured traces per node and tool call.

## Execution Checklist

- [ ] Define ports/state/config for agentic flow.
- [ ] Implement LangGraph adapter and tool executor.
- [ ] Wire `answer_question` with guarded agentic mode + fallback.
- [ ] Add architecture boundary and behavior tests.
- [ ] Extend evaluation and regression gates.
- [ ] Update runbooks + progress checklist with new evidence artifacts.

## Suggested ADRs

- ADR-006: LangGraph as orchestration adapter under hexagonal architecture.
- ADR-007: Agent execution budgets and fallback policy.

## Immediate Next Steps

1. Confirm this sprint plan as baseline.
2. Implement Sprint A contracts and boundary tests first.
3. Run baseline eval snapshot before enabling agentic mode by default.
