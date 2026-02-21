# Quality Gates and Evaluation

Version: 1.0
Date: 2026-02-21
Status: Draft

## 1. Golden Tests
- Each release must run golden evaluations.
- Golden questions must include table, diagram, and procedure coverage.
- Minimum pass rate for release: 85 percent.

## 2. Retrieval Gates
- Recall-at-5 on golden questions >= 0.80.
- Modality hit rate for table and diagram intents >= 0.70.
 - Procedure intent recall-at-5 >= 0.75.
 - Modality diversity: top-5 results include at least 2 modalities when intent is multimodal.

## 3. Ingestion QC Gates
- Text coverage >= 0.60 for digital manuals.
- OCR coverage >= 0.80 for scanned manuals.
- Embedding coverage >= 0.95.
- Table yield >= 0.20 for manuals tagged as table-heavy.

## 4. Answer Quality Gates
- 100 percent of answers include citations.
- Abstain required when evidence coverage < 0.50.
 - Confidence must be a numeric float between 0 and 1.

## 5. Release Checklist
- Regression tests pass.
- Golden evaluation pass rate >= threshold.
- QC metrics recorded for all new manuals.
- Known failure cases documented.
