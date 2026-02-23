"""MCP server entry point for the Equipment Manuals Chatbot.

Exposes three tools:
  - search_manuals  : retrieve grounded evidence chunks
  - answer_question : generate a grounded answer with citations
  - list_manuals    : list available equipment manuals

Transport:
  MCP_TRANSPORT=stdio (default) – for Claude Desktop / VS Code Copilot
  MCP_TRANSPORT=sse             – HTTP SSE for hosted deployments (MCP_PORT=8001)

Run:  python -m apps.mcp.server
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from packages.adapters.data_contracts.yaml_catalog_adapter import YamlDocumentCatalogAdapter
from packages.adapters.retrieval.filesystem_chunk_query_adapter import FilesystemChunkQueryAdapter
from packages.adapters.retrieval.hash_vector_search_adapter import HashVectorSearchAdapter
from packages.adapters.retrieval.simple_keyword_search_adapter import SimpleKeywordSearchAdapter
from packages.application.use_cases.answer_question import (
    AnswerQuestionInput,
    answer_question_use_case,
)
from packages.application.use_cases.search_evidence import (
    SearchEvidenceInput,
    search_evidence_use_case,
)

_DATA_DIR = Path('.context/project/data')
_CATALOG_PATH = _DATA_DIR / 'document_catalog.yaml'
_ASSETS_DIR = Path('data/assets')

mcp = FastMCP(
    'ai-manuals',
    host='0.0.0.0',
    port=int(os.getenv('MCP_PORT', '8001')),
)


# ---------------------------------------------------------------------------
# Internal helpers (tested independently, no MCP protocol coupling)
# ---------------------------------------------------------------------------

def _build_chunk_query(doc_ids: list[str] | None):
    """Return a chunk query adapter, optionally scoped to the given doc_ids."""
    base = FilesystemChunkQueryAdapter(_ASSETS_DIR)
    selected = set(doc_ids or [])
    if not selected:
        return base

    class _ScopedAdapter:
        def list_chunks(self, doc_id: str | None = None):
            if doc_id:
                if doc_id not in selected:
                    return []
                return base.list_chunks(doc_id=doc_id)
            rows = base.list_chunks(doc_id=None)
            return [r for r in rows if r.doc_id in selected]

    return _ScopedAdapter()


async def _search_manuals_impl(
    query: str,
    doc_ids: list[str] | None = None,
) -> list[dict]:
    """Business logic for the search_manuals tool."""
    chunk_query = _build_chunk_query(doc_ids)
    output = search_evidence_use_case(
        SearchEvidenceInput(query=query, doc_id=None),
        chunk_query=chunk_query,
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
    )
    return [
        {
            'content': h.snippet,
            'doc_id': h.doc_id,
            'page': h.page_start,
            'type': h.content_type,
        }
        for h in output.hits
    ]


async def _answer_question_impl(
    query: str,
    doc_ids: list[str] | None = None,
) -> dict:
    """Business logic for the answer_question tool."""
    chunk_query = _build_chunk_query(doc_ids)
    output = answer_question_use_case(
        AnswerQuestionInput(query=query, doc_id=None),
        chunk_query=chunk_query,
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
    )
    return {
        'answer': output.answer,
        'confidence': output.confidence,
        'abstain': output.abstain,
        'citations': [
            {
                'doc_id': c.doc_id,
                'page': c.page,
                'section_path': c.section_path,
                'label': c.label,
            }
            for c in output.citations
        ],
    }


async def _list_manuals_impl() -> list[dict]:
    """Business logic for the list_manuals tool."""
    catalog = YamlDocumentCatalogAdapter(_CATALOG_PATH)
    records = catalog.list_documents()
    return [{'doc_id': r.doc_id, 'title': r.title, 'status': r.status} for r in records]


# ---------------------------------------------------------------------------
# MCP tool registrations (thin wrappers — transport-agnostic)
# ---------------------------------------------------------------------------

@mcp.tool()
async def search_manuals(query: str, doc_ids: list[str] | None = None) -> list[dict]:
    """Search equipment manuals for relevant chunks. Returns grounded evidence."""
    return await _search_manuals_impl(query, doc_ids)


@mcp.tool()
async def answer_question(query: str, doc_ids: list[str] | None = None) -> dict:
    """Answer a question grounded in equipment manual evidence."""
    return await _answer_question_impl(query, doc_ids)


@mcp.tool()
async def list_manuals() -> list[dict]:
    """List all available equipment manuals in the catalog."""
    return await _list_manuals_impl()


# ---------------------------------------------------------------------------
# Transport runners
# ---------------------------------------------------------------------------

async def _run_stdio() -> None:
    await mcp.run_stdio_async()


async def _run_sse() -> None:
    await mcp.run_sse_async()


async def main() -> None:
    transport = os.getenv('MCP_TRANSPORT', 'stdio').strip().lower()
    if transport == 'sse':
        await _run_sse()
    else:
        await _run_stdio()


if __name__ == '__main__':
    asyncio.run(main())
