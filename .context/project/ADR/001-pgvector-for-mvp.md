# ADR-001: pgvector in PostgreSQL for MVP

Status: Accepted
Date: 2026-02-17

## Context

The MVP needs hybrid retrieval with low operational complexity in a local-first environment.

## Decision

Use PostgreSQL 16 + pgvector as the vector store, with Postgres FTS for keyword retrieval.

## Rationale

- Single datastore reduces ops burden.
- Good fit for MVP scale.
- Keeps deployment simple in Docker Compose.

## Consequences

Positive:
- Simple setup and backup strategy.
- Strong transactional consistency with metadata.

Negative:
- Fewer advanced vector features than dedicated vector DBs.
- Large-scale tuning may be needed later.

## Alternatives Considered

- Dedicated vector DB (Qdrant/Weaviate/Milvus): rejected for MVP complexity.
