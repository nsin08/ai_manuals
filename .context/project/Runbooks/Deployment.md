# Runbook: Deployment

Version: 1.0
Date: 2026-02-17

## Scope

Deployment steps for MVP local/self-hosted environment.

## Pre-deploy Checklist

- Compose files validated
- Required env vars present
- DB migrations applied
- Smoke tests passing

## Deployment Steps

1. Pull latest images/code.
2. Apply migrations.
3. Start/refresh services with Docker Compose.
4. Run post-deploy health checks.

## Post-deploy Validation

- API health endpoint is green.
- UI reachable.
- Sample query returns citations.
- Ingestion job can run successfully.

## Rollback

1. Revert to prior image/tag or commit.
2. Restart services.
3. Re-validate health and sample query.
