# Runbook: Deployment

Version: 1.1
Date: 2026-02-17

## Scope

Deployment steps for local/self-hosted MVP runtime.

## Pre-deploy Checklist

- Working tree clean for target release commit
- Required env vars present in `.env`
- Data contracts pass: `python scripts/validate_data_contracts.py --strict-files`
- Regression gates pass: `python scripts/run_regression_gates.py --doc-id rockwell_powerflex_40 --limit 5 --min-pass-rate 80`

## Deployment Steps

1. `docker compose -f infra/docker-compose.yml pull`
2. `docker compose -f infra/docker-compose.yml up --build -d`
3. `curl http://localhost:8000/health`
4. `curl "http://localhost:8000/answer?q=fault%20code%20corrective%20action&doc_id=rockwell_powerflex_40&top_n=5"`

## Post-deploy Validation

- API health is `ok`
- UI reachable at `http://localhost:8501`
- Answer endpoint returns citations with `doc_id` and `page`
- Golden subset evaluation returns pass rate above threshold

## Rollback

1. Checkout previous release tag.
2. `docker compose -f infra/docker-compose.yml up --build -d`
3. Re-run health and answer smoke checks.
