# Backend Technology Guide

Version: 1.1
Date: 2026-02-17

## Purpose

Define backend technology choices and implementation standards, including golden-question evaluation support.

## Core Stack

- Python 3.11
- FastAPI (API)
- Celery + Redis (background jobs)
- PostgreSQL 16 + pgvector (data + vector)

## Libraries

- PDF: PyMuPDF, pdfplumber
- Tables: Camelot (+ fallback parsing)
- OCR: PaddleOCR (primary), Tesseract (fallback)
- Embeddings: sentence-transformers wrapper for BAAI models
- Local LLM provider: Ollama HTTP client
- Config: `pydantic-settings`
- DB access/migrations: SQLAlchemy + Alembic
- Data contracts: PyYAML for golden/canonical catalog files

## Retrieval and Ranking

- Hybrid retrieval: Postgres FTS + pgvector
- Query-intent weighting:
  - table/spec intents prioritize table chunks
  - diagram/electrical intents prioritize figure OCR + captions
- Optional reranker: cross-encoder as post-MVP toggle

## API Standards

- Pydantic models for request/response contracts
- Explicit error codes for retrieval/ingestion failures
- Correlation id in request context
- Stable answer schema that always returns `citations[]`

## Evaluation Standards

- Golden question loader from `.context/project/data/golden_questions.yaml`
- Required checks per answer:
  - citation includes document + page
  - answer grounded in retrieved evidence
- Store per-question result and aggregate pass rate

## Coding Standards

- Keep domain pure and framework-agnostic
- Keep adapter code isolated from use-case logic
- Write unit tests before/alongside adapter integration tests

## Observability

- JSON logs to stdout
- Run ids for ingestion, query, and evaluation runs
- Optional trace persistence in DB
