# Equipment Manuals Chatbot

Local-first AI chatbot for engineering documentation.

[![Framework](https://img.shields.io/badge/framework-space__framework-blue)](https://github.com/nsin08/space_framework)
[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/)

## Overview

This project builds a local-first chatbot that answers engineering questions from manuals (digital and scanned PDFs) with grounded citations.

Core capabilities:
- Troubleshooting queries (alarms, symptoms, corrective actions)
- SOP/procedure questions (commissioning, decommissioning, maintenance)
- Spec extraction from tables
- Diagram interpretation via OCR-first strategy
- Citation-backed answers (doc + page, plus figure/table where available)

## Current Status

Implemented through Phase 3:
- Phase 0 foundations and contract validation
- Phase 1 ingestion pipeline (PDF parsing, OCR adapters, table extraction, chunk storage)
- Phase 2 hybrid retrieval (keyword + vector fallback, intent weighting, trace logging)
- Phase 3 grounded answering (citations, not-found path, ambiguity follow-up)
- Phase 4 UI and evaluation (upload flow, chat source panel, golden-question runner)
- Phase 5 hardening (CI regression gates, performance baseline, security/local-first checks, release checklist)

Detailed progress and evidence are tracked in `.context/project/PROGRESS_CHECKLIST.md`.

## Documentation

- Project context index: `.context/project/README.md`
- Handover requirements: `.context/project/CODEX_HANDOVER.md`
- Architecture: `.context/project/ARCHITECTURE.md`
- Comprehensive plan: `.context/project/PROJECT_PLAN.md`
- Implementation roadmap: `.context/project/IMPLEMENTATION_ROADMAP.md`
- Dataset contracts: `.context/project/data/README.md`
- Golden questions: `.context/project/data/golden_questions.yaml`
- Document catalog: `.context/project/data/document_catalog.yaml`
- Agent/governance guidance: `.github/copilot-instructions.md`

## Intended Stack

- Backend: Python 3.11, FastAPI, Celery, Redis
- Storage: PostgreSQL 16 + pgvector
- OCR/PDF: PaddleOCR, Tesseract fallback, PyMuPDF, pdfplumber, Camelot
- Local LLM: Ollama
- UI: Streamlit
- Runtime: Docker Compose

## Governance

This repository follows `space_framework` governance with issue state machine, PR evidence mapping, and CODEOWNER review.

See `.github/copilot-instructions.md` for workflow details.
