# ADR-003: Evidence-grounded Answering Policy

Status: Accepted
Date: 2026-02-17

## Context

Engineering answers must be auditable and safe. Hallucinated procedures or specs are unacceptable.

## Decision

Adopt strict grounding policy: no evidence, no claim.
Every answer must include citations to source content.

## Rationale

- Increases operator trust.
- Makes review and debugging practical.
- Supports safety and compliance expectations.

## Consequences

Positive:
- Clear answer provenance.
- Better failure behavior on unknown questions.

Negative:
- Some answers may be incomplete without enough retrieved evidence.

## Implementation Notes

- Return explicit "not found in provided manuals" when evidence is insufficient.
- Include closest citations and ask one follow-up when ambiguous.
