# ADR-005: Local-first by Default, Cloud via Explicit Toggle

Status: Accepted
Date: 2026-02-17

## Context

The product requirement is offline capability and no mandatory API keys for MVP.

## Decision

Default to local providers for embeddings/LLM/OCR/storage.
Cloud providers are optional and enabled only through explicit environment configuration.

## Rationale

- Supports offline use and data locality.
- Prevents accidental data egress.
- Keeps compliance posture clearer.

## Consequences

Positive:
- Strong default privacy model.

Negative:
- Local models may produce lower quality than top cloud models in some cases.

## Guardrails

- Use `LLM_PROVIDER=cloud` only when key is configured.
- Log active provider in startup diagnostics.
