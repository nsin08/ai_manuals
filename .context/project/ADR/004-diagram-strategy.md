# ADR-004: Diagram Strategy (OCR-first, Vision Fallback)

Status: Accepted
Date: 2026-02-17

## Context

Diagram-based queries are common (pins, labels, dimensions) and may not be answerable from text alone.

## Decision

Use OCR-first strategy for figure crops and captions in MVP.
Add optional targeted vision fallback behind provider toggle.

## Rationale

- OCR-first keeps local-first path viable.
- Fallback vision enables higher accuracy for hard diagrams when permitted.

## Consequences

Positive:
- Delivers MVP capability without mandatory cloud dependency.

Negative:
- OCR-only path may miss low-quality or densely annotated diagrams.

## Trigger for Fallback

Invoke vision fallback only when:
- relevant figure is found, and
- required value/connection cannot be extracted confidently.
