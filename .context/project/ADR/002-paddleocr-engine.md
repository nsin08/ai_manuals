# ADR-002: PaddleOCR as Primary OCR Engine

Status: Accepted
Date: 2026-02-17

## Context

The system must support scanned manuals and diagram labels, where OCR quality directly impacts retrieval quality.

## Decision

Use PaddleOCR as primary OCR engine, with Tesseract as fallback option.

## Rationale

- Better practical accuracy on technical labels and mixed layouts.
- Good support for detection + recognition pipeline.

## Consequences

Positive:
- Improved extraction quality for figures and scanned pages.

Negative:
- Heavier runtime dependencies than Tesseract alone.

## Alternatives Considered

- Tesseract-only pipeline: rejected due to lower expected quality in noisy diagrams.
