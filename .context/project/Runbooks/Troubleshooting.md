# Runbook: Troubleshooting

Version: 1.1
Date: 2026-02-17

## Symptom: Contract validation fails

Checks:
- Run `python scripts/validate_data_contracts.py --strict-files`
- Confirm every `status: present` catalog file exists in `.context/project/data`

Actions:
- Fix `document_catalog.yaml` filename/status mismatch
- Add missing PDF or set status to `missing` if intentionally absent

## Symptom: Golden evaluation pass rate drops

Checks:
- Run `python scripts/run_regression_gates.py --doc-id rockwell_powerflex_40 --limit 5 --min-pass-rate 80`
- Inspect `.context/reports/phase5_regression_gate.json`

Actions:
- Re-ingest affected docs
- Inspect retrieval traces in `.context/reports/retrieval_traces.jsonl`
- Review answer citations for missing `doc/page`

## Symptom: No citations in answers

Checks:
- Verify ingested chunks exist under `data/assets/<doc_id>/chunks.jsonl`
- Verify `/answer` response includes `retrieved_chunk_ids`

Actions:
- Ingest doc again
- Increase `top_n` on `/answer`
- Verify query specificity and `doc_id` filter

## Symptom: Service startup errors

Checks:
- `docker ps`
- `docker logs infra-api-1 --tail 200`
- `docker logs infra-ui-1 --tail 200`

Actions:
- Resolve env var/port conflicts
- Rebuild with `docker compose -f infra/docker-compose.yml up --build -d`
