# Infrastructure Technology Guide

Version: 1.1
Date: 2026-02-17

## Purpose

Define runtime infrastructure, local-first deployment, and benchmark execution baseline.

## Runtime Services

- `postgres` with pgvector extension
- `redis` for queueing
- `api` FastAPI service
- `worker` Celery worker
- `ui` Streamlit service
- optional `ollama` (if running local model in compose)
- optional `minio`

## Deployment Baseline

- Docker Compose for local and MVP deployment
- Bind-mounted assets under `/data/assets`
- Read-only benchmark/data mount from `.context/project/data`
- Environment variables from `.env`

## Security and Data Handling

- Local-first defaults enabled
- No external provider calls unless explicitly configured
- API keys never committed to repository
- Clear startup log of active provider mode (`local` or `cloud`)

## Reliability

- Service healthchecks in compose
- Restart policies for worker/api/ui
- Backup strategy for Postgres volume

## Performance Notes

- Background ingestion workers to avoid blocking API
- Tune worker concurrency for CPU-heavy OCR
- Use DB indexing for metadata filters and FTS
- Batch embedding generation to reduce ingestion latency

## Evaluation Operations

- Provide a repeatable command to run golden-question evaluation
- Persist evaluation summaries for regression tracking
- Fail CI gate when must-have checks regress beyond threshold
