# Quickstart

This guide covers start, stop, ingest, and reset for the Equipment Manuals Assistant.

## 1. Prerequisites

- Docker Desktop running
- Ollama running locally (if using local models)
- Repo root as working directory

Optional model pulls:

```powershell
ollama pull mxbai-embed-large:latest
ollama pull deepseek-r1:8b
ollama pull qwen2.5vl:7b
```

## 2. Configure Environment

Create/update `.env` (or copy from `.env.example`).

Recommended local-model setup:

```env
USE_LLM_ANSWERING=true
LLM_PROVIDER=local
LLM_BASE_URL=http://host.docker.internal:11434
LLM_MODEL=deepseek-r1:8b

EMBEDDING_PROVIDER=ollama
EMBEDDING_BASE_URL=http://host.docker.internal:11434
EMBEDDING_MODEL=mxbai-embed-large:latest

USE_RERANKER=true
RERANKER_PROVIDER=ollama
RERANKER_BASE_URL=http://host.docker.internal:11434
RERANKER_MODEL=phi:latest
RERANKER_POOL_SIZE=24

USE_VISION_INGESTION=true
VISION_PROVIDER=ollama
VISION_BASE_URL=http://host.docker.internal:11434
VISION_MODEL=qwen2.5vl:7b
VISION_MAX_PAGES=40

USE_AGENTIC_MODE=true
AGENTIC_PROVIDER=langgraph
AGENTIC_MAX_ITERATIONS=4
AGENTIC_MAX_TOOL_CALLS=6
AGENTIC_TIMEOUT_SECONDS=20
INCLUDE_REASONING_SUMMARY=true

INGEST_CONCURRENCY=2
INGEST_PAGE_WORKERS=4
```

## 3. Start Services

```powershell
docker compose -f infra/docker-compose.yml up --build -d
docker ps
```

Open:

- Main UI: `http://localhost:8501/`
- Dev UI: `http://localhost:8501/dev`
- Admin UI: `http://localhost:8501/admin`
- API: `http://localhost:8000/health`

## 4. Stop Services

```powershell
docker compose -f infra/docker-compose.yml down
```

Stop + remove volumes (full DB reset):

```powershell
docker compose -f infra/docker-compose.yml down -v
```

## 5. Ingest Documents

### Option A: Admin UI

1. Open `http://localhost:8501/admin`
2. Upload PDF (or ingest catalog doc)
3. Verify in ingested docs list

### Option B: API (catalog doc)

```powershell
curl -X POST http://localhost:8000/ingest/rockwell_powerflex_40
```

### Option C: Background jobs API (recommended for large PDFs)

Start upload job:

```powershell
curl -X POST http://localhost:8000/jobs/upload ^
  -F "doc_id=rockwell_upload" ^
  -F "file=@.context/project/data/22b-um001_-en-e.pdf"
```

Start catalog ingest job:

```powershell
curl -X POST http://localhost:8000/jobs/ingest/rockwell_powerflex_40
```

Check progress:

```powershell
curl http://localhost:8000/jobs/<job_id>
```

### Option D: Script

```powershell
python scripts/run_ingestion.py --doc-id rockwell_powerflex_40 --embedding-provider ollama --embedding-base-url http://localhost:11434 --embedding-model mxbai-embed-large:latest --use-vision-ingestion --vision-provider ollama --vision-base-url http://localhost:11434 --vision-model qwen2.5vl:7b
```

## 6. Query / Validate

Ask from UI chat, or API:

```powershell
curl "http://localhost:8000/answer?q=What%20does%20fault%20F005%20mean%3F&doc_id=rockwell_powerflex_40&top_n=8&rerank_pool_size=24"
```

Run tests:

```powershell
pytest tests -q
```

Run reliability evaluation:

```powershell
python scripts/run_reliability_eval.py --use-llm-answering --llm-provider local --llm-base-url http://localhost:11434 --llm-model deepseek-r1:8b --embedding-provider ollama --embedding-base-url http://localhost:11434 --embedding-model mxbai-embed-large:latest --use-reranker --reranker-provider ollama --reranker-base-url http://localhost:11434 --reranker-model phi:latest --use-agentic-mode --agentic-provider langgraph
```

## 7. Reset Data

### Quickest way: Use cleanup script

```powershell
# Soft reset (keep DB, clear chunks, restart):
.\scripts\reset_local_state.ps1 -Soft

# Full reset (remove DB + volumes, clear filesystem, restart):
.\scripts\reset_local_state.ps1 -Full
```

### Manual cleanup

**Soft reset (remove ingested chunks/uploads only)**

Keep containers running. Remove filesystem chunks:

```powershell
# Clear filesystem storage (chunks, assets, uploads)
Get-ChildItem data\assets -Recurse -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem data\uploads -Recurse -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Restart worker/API containers to reload from empty state
docker compose -f infra/docker-compose.yml restart worker api
```

Then re-ingest docs.

**Full reset (containers + DB volumes + filesystem storage)**

⚠️ **REQUIRED after Phase 1 upgrade** (schema change: table → table_row)

```powershell
# 1. Stop and remove containers + Docker volumes (PostgreSQL + Redis):
docker compose -f infra/docker-compose.yml down -v

# 2. Clean ALL local filesystem storage (critical! -v doesn't touch filesystem):
Get-ChildItem data\assets -Recurse -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem data\uploads -Recurse -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem data\chunks -Recurse -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# 3. Restart fresh:
docker compose -f infra/docker-compose.yml up --build -d

# 4. VERIFY in admin console (wait 10s for startup):
#    http://localhost:8501/admin → Should show "Ingested Docs: 0"
```

### Phase 1 Upgrade (Table & Diagram Fidelity)

**⚠️ Breaking change to chunk schema:** Phase 1 replaces `content_type='table'` with `content_type='table_row'` and adds structured metadata (row_index, headers, units, bbox).

**Do this after merging Phase 1:**

```powershell
# Full reset to clear incompatible chunks:
docker compose -f infra/docker-compose.yml down -v
Remove-Item -Recurse -Force data\assets\*
Remove-Item -Recurse -Force data\uploads\*

# Restart:
docker compose -f infra/docker-compose.yml up --build -d

# Re-ingest all manuals with Phase 1 support:
python scripts/run_ingestion.py --doc-id siemens_g120_basic_positioner
python scripts/run_ingestion.py --doc-id rockwell_powerflex_40
python scripts/run_ingestion.py --doc-id timken_bearing_setting

# Test retrieval with table queries:
python scripts/run_retrieval.py --query "fault code table corrective" --doc-id siemens_g120_basic_positioner
```

Expected improvements:
- Table rows are now structured (headers, cells, units) instead of flat text
- Figure regions have bounding boxes for precise citation
- Better recall on spec table and fault code queries

## 8. Useful Health Checks

```powershell
curl http://localhost:8000/health
curl http://localhost:8000/health/contracts
curl http://localhost:8000/ingested/docs
curl http://localhost:8000/jobs?limit=10
```
