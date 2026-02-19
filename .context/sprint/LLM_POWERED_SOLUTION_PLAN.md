# LLM-Powered Solution Sprint Plan

Version: 1.0
Date: 2026-02-18
Branch: feature/llm-powered-solution

## Goal

Upgrade the existing local-first manuals assistant to use local LLM-powered answering and embedding-based retrieval while preserving grounding, citations, and offline-first defaults.

## Success Criteria

- End-user UI remains default at `http://localhost:8501/`
- LLM-backed answer synthesis enabled with safe fallback to deterministic mode
- Embedding retrieval upgraded from hash vectors to Ollama embeddings (`mxbai-embed-large`)
- Golden benchmark pass rate improves over current baseline
- Regression/security gates remain green

## Scope

In scope:
- Ollama adapter for chat completion and embeddings
- Config flags and runtime wiring for LLM/embedding provider selection
- Retrieval upgrade: lexical + real embeddings hybrid merge
- Prompting strategy for grounded, citation-preserving answers
- UI improvements for end-user-first interaction and follow-ups
- Evaluation comparison report (before vs after)

Out of scope (this sprint):
- Cloud LLM provider integration
- Multi-tenant auth and user management
- External vector DB migration

## Architecture Changes

### New Ports and Adapters

- `LlmPort`: grounded answer synthesis interface
- `EmbeddingPort`: text embedding interface
- `OllamaLlmAdapter`: `/api/chat` based answer generation
- `OllamaEmbeddingAdapter`: `/api/embeddings` for chunk/query vectors

### Application Use-case Updates

- `answer_question_use_case`
  - add optional LLM synthesis path from retrieved evidence
  - enforce post-generation grounding policy and citation schema
  - keep deterministic fallback when LLM unavailable
- `search_evidence_use_case`
  - replace hash-vector backend with embedding vector backend
  - preserve lexical + vector hybrid and intent weighting

### Config Additions

- `USE_LLM_ANSWERING=true|false`
- `LOCAL_LLM_BASE_URL=http://host.docker.internal:11434`
- `LOCAL_LLM_MODEL=deepseek-r1:8b`
- `EMBEDDING_PROVIDER=ollama`
- `LOCAL_EMBEDDING_MODEL=mxbai-embed-large`

## Sprint Breakdown

## Sprint A: LLM Answering Foundation

Deliverables:
- Implement `LlmPort` and `OllamaLlmAdapter`
- Add grounded prompt template with explicit evidence constraints
- Integrate LLM path in `answer_question_use_case`
- Keep deterministic fallback if adapter errors/timeouts

Acceptance:
- `/answer` returns same response schema
- Citations always present when status is `ok`
- Unit tests for adapter fallback and schema invariants

Evidence:
- `tests/unit/test_answer_question_llm.py`
- `.context/reports/sprintA_answer_samples.json`

## Sprint B: Embedding Retrieval Upgrade

Deliverables:
- Implement `EmbeddingPort` and Ollama embedding adapter
- Persist/query embeddings for chunks
- Hybrid retrieval with lexical + embedding cosine scoring

Acceptance:
- Retrieval tests pass with embedding backend
- Golden subset top-k hit quality improved vs hash baseline

Evidence:
- `tests/unit/test_retrieval_embeddings.py`
- `.context/reports/sprintB_retrieval_comparison.json`

## Sprint C: UI Productization (End-User Default)

Deliverables:
- Keep UI default at root path `/`
- Chat-first UX with sources panel and follow-up controls
- Move debug tools behind optional "Admin" expander

Acceptance:
- Upload -> ask -> source inspection works for end users
- No raw JSON required for common user flow

Evidence:
- `tests/integration/test_ui_flow_phase_llm.md` (manual script)
- `.context/reports/sprintC_demo_checklist.md`

## Sprint D: Evaluation and Hardening

Deliverables:
- Golden benchmark before/after report
- Threshold updates for regression gates
- Runbook and release checklist updates

Acceptance:
- Regression gate workflow green
- Golden pass rate >= agreed threshold

Evidence:
- `.context/reports/sprintD_golden_comparison.json`
- `.github/workflows/18-regression-gates.yml` update

## Prompting Strategy

System prompt policy:
- Use only provided evidence chunks
- If evidence insufficient, respond with `not_found`
- Never fabricate values/steps
- Keep answer concise and operational

Answer format:
1. Direct answer or steps
2. Safety notes (if applicable)
3. Citations (doc/page; figure/table when available)

Follow-up behavior:
- Ask one concise clarifying question when ambiguity detected
- Preserve existing `needs_follow_up` status contract

## Risks and Mitigations

- Model hallucination risk
  - Mitigation: strict evidence prompt + post-check grounding gate
- Ollama runtime latency
  - Mitigation: timeout + deterministic fallback + caching candidates
- Embedding drift over heterogeneous docs
  - Mitigation: hybrid retrieval and weighted merge retained

## Execution Checklist

- [ ] Add ports/adapters for LLM + embeddings
- [ ] Wire config toggles
- [ ] Add tests and contract checks
- [ ] Run full benchmark and compare baseline
- [ ] Update runbooks and progress checklist
- [ ] Prepare PR with evidence mapping
