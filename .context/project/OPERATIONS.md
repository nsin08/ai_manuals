# Operations and Runbooks

Version: 1.0
Date: 2026-02-21
Status: Draft

## 1. Ingestion Runbook
- Register manual in the document catalog.
- Run ingestion job with OCR and table extraction enabled.
- Validate ingestion QC metrics and address failures.
- Record revision and source hash on catalog updates.

## 2. Retrieval Runbook
- Run retrieval checks on golden questions.
- Inspect retrieval traces for missed modalities.
- Adjust retrieval weights and reranker settings if needed.
 - Confirm modality hit counts for table, diagram, and procedure intents.

## 3. Answering Runbook
- Verify evidence-only answers with citations.
- Inspect abstain cases for missing ingestion artifacts.
 - Confirm confidence values are numeric and within 0..1.

## 4. Troubleshooting
- If embeddings fail, retry with reduced chunk size.
- If OCR fails, switch to fallback engine.
- If tables are missed, adjust parser strategy or use fallback heuristics.

## 5. Release Runbook
- Run regression gates and golden evaluations.
- Archive reports for traceability.
