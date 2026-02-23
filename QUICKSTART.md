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

### Soft reset (remove ingested chunks/uploads)

```powershell
Remove-Item -Recurse -Force data\assets\*
Remove-Item -Recurse -Force data\uploads\*
```

Then re-ingest docs.

### Full reset (containers + volumes + local artifacts)

```powershell
docker compose -f infra/docker-compose.yml down -v
Remove-Item -Recurse -Force data\assets\*
Remove-Item -Recurse -Force data\uploads\*
docker compose -f infra/docker-compose.yml up --build -d
```

## 8. Useful Health Checks

```powershell
curl http://localhost:8000/health
curl http://localhost:8000/health/contracts
curl http://localhost:8000/ingested/docs
curl http://localhost:8000/jobs?limit=10
```

---

## 9. MCP Server (Phase 5)

Exposes three tools to any MCP-compatible client (Claude Desktop, VS Code Copilot, Cursor, custom agents):

| Tool | What it does |
|------|-------------|
| `list_manuals` | List all available equipment manuals |
| `search_manuals` | Return grounded evidence chunks for a query |
| `answer_question` | Return a full grounded answer with citations |

### Prerequisites

All ingested docs must be present in `data/assets/` before starting the MCP server.
The server reads directly from the filesystem — Docker does **not** need to be running.

### 9.1 Inspect & Test with MCP Inspector

MCP Inspector is an interactive browser-based tool. Requires Node.js ≥ 18.

**stdio mode (recommended for local testing):**

```powershell
npx -y @modelcontextprotocol/inspector python -m apps.mcp.server
```

Open `http://localhost:5173` in a browser → click **Connect** → you can list and call
all three tools interactively.

**SSE mode (if you want to test over HTTP):**

Start the server first:

```powershell
$env:MCP_TRANSPORT = "sse"
$env:MCP_PORT = "8001"
python -m apps.mcp.server
```

Then point the inspector at the running SSE server:

```powershell
npx -y @modelcontextprotocol/inspector --cli http://localhost:8001/sse --transport sse
```

Or open `http://localhost:5173`, set transport to **SSE**, URL to `http://localhost:8001/sse`,
and click **Connect**.

### 9.2 Run the Server Manually

**stdio (default — used by Claude Desktop / VS Code):**

```powershell
python -m apps.mcp.server
```

The server waits on stdin — it is controlled by the MCP client process.

**SSE (hosted, port 8001):**

```powershell
$env:MCP_TRANSPORT = "sse"
python -m apps.mcp.server
# or with a custom port:
$env:MCP_PORT = "9000"
python -m apps.mcp.server
```

### 9.3 Quick Smoke Test (Python)

Send a one-shot tool call via the MCP Python client:

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def smoke_test():
    params = StdioServerParameters(command="python", args=["-m", "apps.mcp.server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List tools
            tools = await session.list_tools()
            print("Tools:", [t.name for t in tools.tools])

            # List manuals
            result = await session.call_tool("list_manuals", {})
            print("Manuals:", result.content)

            # Search
            result = await session.call_tool(
                "search_manuals",
                {"query": "bearing preload setting"}
            )
            print("Chunks returned:", len(result.content))

asyncio.run(smoke_test())
```

Save as `.context/temp/smoke_mcp.py` and run:

```powershell
python .context/temp/smoke_mcp.py
```

### 9.4 Claude Desktop Configuration

Edit `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or
`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "ai-manuals": {
      "command": "python",
      "args": ["-m", "apps.mcp.server"],
      "cwd": "D:/wsl_shared/projects/ai_maunuals",
      "env": {
        "LLM_PROVIDER": "local",
        "LLM_BASE_URL": "http://localhost:11434"
      }
    }
  }
}
```

Restart Claude Desktop. The three tools appear in the tool picker (hammer icon).

**Verify:** Ask Claude — *"List the available equipment manuals"* — it should call
`list_manuals` and return your ingested docs.

### 9.5 VS Code Copilot Configuration

Create or edit `.vscode/mcp.json` in the workspace root (already in `.gitignore`):

```json
{
  "servers": {
    "ai-manuals": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "apps.mcp.server"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

In VS Code Chat (Agent mode), the tools `search_manuals`, `answer_question`, and
`list_manuals` will appear automatically.

### 9.6 Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `stdio` | `stdio` for local clients, `sse` for hosted |
| `MCP_PORT` | `8001` | HTTP port for SSE transport (ignored for stdio) |
| `LLM_PROVIDER` | `local` | Same as the API — passed through to answering use case |
| `LLM_BASE_URL` | `http://localhost:11434` | Ollama base URL |

### 9.7 Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `ModuleNotFoundError: mcp` | `mcp` not installed | `pip install "mcp>=1.0"` |
| `list_manuals` returns empty | Catalog path wrong | Run from repo root; check `.context/project/data/document_catalog.yaml` exists |
| `search_manuals` returns no chunks | No ingested docs | Ingest at least one doc first (see §5) |
| Claude Desktop doesn't show tools | `cwd` path wrong in config | Use absolute path to repo root |
| MCP Inspector can't connect on SSE | Server not started | Run `python -m apps.mcp.server` with `MCP_TRANSPORT=sse` first |
