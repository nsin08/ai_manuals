# Runbook: Troubleshooting

Version: 1.0
Date: 2026-02-17

## Symptom: Ingestion Fails on PDF

Checks:
- Validate file readability and format
- Review parser adapter logs
- Confirm OCR dependency availability

Actions:
- Retry with fallback parser/OCR
- Reduce ingestion concurrency for resource contention

## Symptom: Poor Answer Quality

Checks:
- Verify retrieval returns relevant chunks
- Verify citations map to expected docs/pages
- Confirm embeddings model is loaded correctly

Actions:
- Tune retrieval top-k and scoring weights
- Adjust table-first heuristic thresholds

## Symptom: Slow Query Responses

Checks:
- Inspect DB query performance and indexes
- Check worker/API CPU and memory usage
- Verify model inference latency

Actions:
- Optimize retrieval bounds
- Add caching where safe
- Scale worker concurrency cautiously

## Symptom: Service Startup Errors

Checks:
- Missing env vars
- Port conflicts
- Container healthcheck failures

Actions:
- Correct configuration and restart stack
- Inspect logs per service
