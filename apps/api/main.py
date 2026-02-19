from __future__ import annotations

import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from apps.api.ingestion_jobs import IngestionJob, IngestionJobManager
from packages.adapters.answering.answer_trace_logger import AnswerTraceLogger
from packages.adapters.agentic.factory import (
    create_agent_trace_logger,
    create_planner_adapter,
    create_state_graph_runner_adapter,
    create_tool_executor_adapter,
)
from packages.adapters.agentic.langchain_tool_executor_adapter import LangChainToolDefinition
from packages.adapters.data_contracts.yaml_catalog_adapter import YamlDocumentCatalogAdapter
from packages.adapters.embeddings.factory import create_embedding_adapter
from packages.adapters.llm.factory import create_llm_adapter
from packages.adapters.ocr.factory import create_ocr_adapter
from packages.adapters.pdf.pypdf_parser_adapter import PypdfParserAdapter
from packages.adapters.retrieval.filesystem_chunk_query_adapter import FilesystemChunkQueryAdapter
from packages.adapters.retrieval.hash_vector_search_adapter import HashVectorSearchAdapter
from packages.adapters.retrieval.metadata_vector_search_adapter import MetadataVectorSearchAdapter
from packages.adapters.retrieval.retrieval_trace_logger import RetrievalTraceLogger
from packages.adapters.retrieval.simple_keyword_search_adapter import SimpleKeywordSearchAdapter
from packages.adapters.reranker.factory import create_reranker_adapter
from packages.adapters.storage.filesystem_chunk_store_adapter import FilesystemChunkStoreAdapter
from packages.adapters.tables.simple_table_extractor_adapter import SimpleTableExtractorAdapter
from packages.adapters.vision.factory import create_vision_adapter
from packages.application.config import load_config
from packages.application.use_cases.answer_question import (
    AnswerQuestionInput,
    answer_question_use_case,
)
from packages.application.use_cases.ingest_document import (
    IngestDocumentInput,
    ingest_document_use_case,
)
from packages.application.use_cases.run_golden_evaluation import (
    RunGoldenEvaluationInput,
    run_golden_evaluation_use_case,
)
from packages.application.use_cases.search_evidence import (
    EvidenceHit,
    SearchEvidenceInput,
    search_evidence_use_case,
)
from packages.application.use_cases.validate_data_contracts import (
    ValidateDataContractsInput,
    validate_data_contracts_use_case,
)


DATA_DIR = Path('.context/project/data')
CATALOG_PATH = DATA_DIR / 'document_catalog.yaml'
GOLDEN_PATH = DATA_DIR / 'golden_questions.yaml'
ASSETS_DIR = Path('data/assets')
UPLOADS_DIR = Path('data/uploads')
_BOOT_CONFIG = load_config()
JOB_MANAGER = IngestionJobManager(max_workers=_BOOT_CONFIG.ingest_concurrency)

app = FastAPI(title='Equipment Manuals Chatbot API', version='0.7.0')


def _slugify(value: str) -> str:
    slug = re.sub(r'[^a-zA-Z0-9_-]+', '_', value.strip().lower())
    slug = slug.strip('_')
    return slug or 'uploaded_manual'


def _build_embedding_adapter(cfg):
    return create_embedding_adapter(
        provider=cfg.embedding_provider,
        base_url=cfg.embedding_base_url,
        model=cfg.embedding_model,
    )


def _build_vector_search(cfg):
    if cfg.embedding_provider.strip().lower() in {'ollama', 'local'}:
        return MetadataVectorSearchAdapter(_build_embedding_adapter(cfg))
    return HashVectorSearchAdapter()


def _build_llm(cfg):
    if not cfg.use_llm_answering:
        return None
    return create_llm_adapter(
        provider=cfg.llm_provider,
        base_url=cfg.llm_base_url,
        model=cfg.llm_model,
    )


def _build_reranker(cfg):
    if not cfg.use_reranker:
        return None
    return create_reranker_adapter(
        provider=cfg.reranker_provider,
        base_url=cfg.reranker_base_url,
        model=cfg.reranker_model,
    )


def _build_vision(cfg):
    if not cfg.use_vision_ingestion:
        return None
    return create_vision_adapter(
        provider=cfg.vision_provider,
        base_url=cfg.vision_base_url,
        model=cfg.vision_model,
    )


def _serialize_hit(hit: EvidenceHit) -> dict[str, object]:
    return {
        'chunk_id': hit.chunk_id,
        'doc_id': hit.doc_id,
        'content_type': hit.content_type,
        'page_start': hit.page_start,
        'page_end': hit.page_end,
        'section_path': hit.section_path,
        'figure_id': hit.figure_id,
        'table_id': hit.table_id,
        'score': hit.score,
        'keyword_score': hit.keyword_score,
        'vector_score': hit.vector_score,
        'rerank_score': hit.rerank_score,
        'snippet': hit.snippet,
    }


def _build_agentic_stack(
    *,
    cfg,
    chunk_query,
    reranker,
):
    if not cfg.use_agentic_mode:
        return None, None, None, None

    def _search_evidence_tool(arguments: dict[str, object]) -> dict[str, object]:
        query = str(arguments.get('query') or '').strip()
        if not query:
            raise ValueError('query is required')

        doc_id_value = arguments.get('doc_id')
        doc_id = str(doc_id_value).strip() if doc_id_value is not None else None
        top_n = int(arguments.get('top_n') or 6)
        top_k_keyword = int(arguments.get('top_k_keyword') or 20)
        top_k_vector = int(arguments.get('top_k_vector') or 20)
        rerank_pool_size = int(arguments.get('rerank_pool_size') or cfg.reranker_pool_size)

        output = search_evidence_use_case(
            SearchEvidenceInput(
                query=query,
                doc_id=doc_id,
                top_n=top_n,
                top_k_keyword=top_k_keyword,
                top_k_vector=top_k_vector,
                rerank_pool_size=rerank_pool_size,
            ),
            chunk_query=chunk_query,
            keyword_search=SimpleKeywordSearchAdapter(),
            vector_search=_build_vector_search(cfg),
            trace_logger=RetrievalTraceLogger(Path(cfg.retrieval_trace_file)),
            reranker=reranker,
        )
        return {
            'query': output.query,
            'intent': output.intent,
            'total_chunks_scanned': output.total_chunks_scanned,
            'hits': [_serialize_hit(hit) for hit in output.hits],
        }

    def _draft_answer_tool(arguments: dict[str, object]) -> dict[str, object]:
        _ = arguments
        return {}

    tool_defs = [
        LangChainToolDefinition(
            name='search_evidence',
            description='Retrieve ranked evidence chunks for grounded answering.',
            handler=_search_evidence_tool,
            required_args=('query',),
        ),
        LangChainToolDefinition(
            name='draft_answer',
            description='Placeholder tool for answer drafting stage.',
            handler=_draft_answer_tool,
            required_args=(),
        ),
    ]

    planner = create_planner_adapter(
        provider=cfg.agentic_provider,
        base_url=cfg.llm_base_url,
        model=cfg.llm_model,
    )
    tool_executor = create_tool_executor_adapter(provider=cfg.agentic_provider, tools=tool_defs)
    state_graph_runner = create_state_graph_runner_adapter(provider=cfg.agentic_provider)
    agent_trace_logger = create_agent_trace_logger(Path(cfg.agentic_trace_file))
    return planner, tool_executor, state_graph_runner, agent_trace_logger


def _parse_doc_ids_csv(doc_ids: str | None) -> list[str]:
    if not doc_ids:
        return []
    parsed = [item.strip() for item in doc_ids.split(',')]
    return [item for item in parsed if item]


def _scoped_chunk_query(selected_doc_ids: list[str] | None):
    base = FilesystemChunkQueryAdapter(ASSETS_DIR)
    selected = set(selected_doc_ids or [])
    if not selected:
        return base

    class _ScopedChunkQueryAdapter:
        def list_chunks(self, doc_id: str | None = None):
            if doc_id:
                if doc_id not in selected:
                    return []
                return base.list_chunks(doc_id=doc_id)

            rows = base.list_chunks(doc_id=None)
            return [row for row in rows if row.doc_id in selected]

    return _ScopedChunkQueryAdapter()


def _resolve_pdf_path(doc_id: str) -> Path | None:
    catalog = YamlDocumentCatalogAdapter(CATALOG_PATH)
    record = catalog.get(doc_id)
    if record and record.filename:
        catalog_pdf = CATALOG_PATH.parent / record.filename
        if catalog_pdf.exists():
            return catalog_pdf

    uploaded_pdf = UPLOADS_DIR / f'{doc_id}.pdf'
    if uploaded_pdf.exists():
        return uploaded_pdf
    return None


def _serialize_job(job: IngestionJob) -> dict[str, object]:
    return {
        'job_id': job.job_id,
        'kind': job.kind,
        'doc_id': job.doc_id,
        'filename': job.filename,
        'status': job.status,
        'created_at': job.created_at,
        'updated_at': job.updated_at,
        'stage': job.stage,
        'message': job.message,
        'processed_pages': job.processed_pages,
        'total_pages': job.total_pages,
        'error': job.error,
        'result': job.result,
    }


def _ingest_uploaded_pdf_task(
    *,
    cfg,
    target_doc_id: str,
    target_path: Path,
    original_filename: str,
):
    ocr_adapter = create_ocr_adapter(cfg.ocr_engine, cfg.ocr_fallback_engine)
    embedding_adapter = _build_embedding_adapter(cfg)
    vision_adapter = _build_vision(cfg)

    def _task(progress_callback):
        result = ingest_document_use_case(
            IngestDocumentInput(doc_id=target_doc_id, pdf_path=target_path),
            pdf_parser=PypdfParserAdapter(),
            ocr_adapter=ocr_adapter,
            table_extractor=SimpleTableExtractorAdapter(),
            chunk_store=FilesystemChunkStoreAdapter(ASSETS_DIR),
            embedding_adapter=embedding_adapter,
            vision_adapter=vision_adapter,
            vision_max_pages=cfg.vision_max_pages,
            page_workers=cfg.ingest_page_workers,
            progress_callback=progress_callback,
        )
        return {
            'doc_id': result.doc_id,
            'filename': original_filename,
            'stored_path': str(target_path),
            'asset_ref': result.asset_ref,
            'total_chunks': result.total_chunks,
            'by_type': result.by_type,
        }

    return _task


def _ingest_catalog_pdf_task(
    *,
    cfg,
    doc_id: str,
    pdf_path: Path,
):
    ocr_adapter = create_ocr_adapter(cfg.ocr_engine, cfg.ocr_fallback_engine)
    embedding_adapter = _build_embedding_adapter(cfg)
    vision_adapter = _build_vision(cfg)

    def _task(progress_callback):
        result = ingest_document_use_case(
            IngestDocumentInput(doc_id=doc_id, pdf_path=pdf_path),
            pdf_parser=PypdfParserAdapter(),
            ocr_adapter=ocr_adapter,
            table_extractor=SimpleTableExtractorAdapter(),
            chunk_store=FilesystemChunkStoreAdapter(ASSETS_DIR),
            embedding_adapter=embedding_adapter,
            vision_adapter=vision_adapter,
            vision_max_pages=cfg.vision_max_pages,
            page_workers=cfg.ingest_page_workers,
            progress_callback=progress_callback,
        )
        return {
            'doc_id': result.doc_id,
            'asset_ref': result.asset_ref,
            'total_chunks': result.total_chunks,
            'by_type': result.by_type,
        }

    return _task


@app.get('/health')
def health() -> dict[str, object]:
    cfg = load_config()
    validation = validate_data_contracts_use_case(
        ValidateDataContractsInput(
            catalog_path=CATALOG_PATH,
            golden_questions_path=GOLDEN_PATH,
            strict_files=False,
        )
    )

    return {
        'status': 'ok' if validation.is_valid() else 'degraded',
        'app_env': cfg.app_env,
        'llm_provider': cfg.llm_provider,
        'use_llm_answering': cfg.use_llm_answering,
        'llm_model': cfg.llm_model,
        'llm_base_url': cfg.llm_base_url,
        'embedding_provider': cfg.embedding_provider,
        'embedding_model': cfg.embedding_model,
        'embedding_base_url': cfg.embedding_base_url,
        'use_reranker': cfg.use_reranker,
        'reranker_provider': cfg.reranker_provider,
        'reranker_model': cfg.reranker_model,
        'use_vision_ingestion': cfg.use_vision_ingestion,
        'vision_provider': cfg.vision_provider,
        'vision_model': cfg.vision_model,
        'use_agentic_mode': cfg.use_agentic_mode,
        'agentic_provider': cfg.agentic_provider,
        'agentic_max_iterations': cfg.agentic_max_iterations,
        'agentic_max_tool_calls': cfg.agentic_max_tool_calls,
        'ocr_engine': cfg.ocr_engine,
        'ocr_fallback_engine': cfg.ocr_fallback_engine,
        'contract_errors': len(validation.errors),
        'contract_warnings': len(validation.warnings),
    }


@app.get('/health/contracts')
def contract_health() -> dict[str, object]:
    validation = validate_data_contracts_use_case(
        ValidateDataContractsInput(
            catalog_path=CATALOG_PATH,
            golden_questions_path=GOLDEN_PATH,
            strict_files=False,
        )
    )

    return {
        'valid': validation.is_valid(),
        'errors': validation.errors,
        'warnings': validation.warnings,
    }


@app.get('/catalog')
def list_catalog() -> dict[str, object]:
    catalog = YamlDocumentCatalogAdapter(CATALOG_PATH)
    docs = [doc.__dict__ for doc in catalog.list_documents()]
    return {'documents': docs}


@app.get('/ingested/docs')
def list_ingested_docs() -> dict[str, object]:
    catalog = YamlDocumentCatalogAdapter(CATALOG_PATH)
    catalog_by_id = {row.doc_id: row for row in catalog.list_documents()}
    docs: list[dict[str, object]] = []

    if not ASSETS_DIR.exists():
        return {'documents': docs, 'total': 0}

    for doc_path in sorted([p for p in ASSETS_DIR.iterdir() if p.is_dir()], key=lambda p: p.name):
        chunks_path = doc_path / 'chunks.jsonl'
        total_chunks = 0
        by_type: dict[str, int] = {}
        if chunks_path.exists():
            with chunks_path.open('r', encoding='utf-8') as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    total_chunks += 1
                    try:
                        row = json.loads(line)
                        content_type = str(row.get('content_type') or 'unknown')
                        by_type[content_type] = by_type.get(content_type, 0) + 1
                    except json.JSONDecodeError:
                        by_type['invalid'] = by_type.get('invalid', 0) + 1

        mtime = datetime.fromtimestamp(doc_path.stat().st_mtime, tz=UTC).isoformat()
        catalog_row = catalog_by_id.get(doc_path.name)
        docs.append(
            {
                'doc_id': doc_path.name,
                'total_chunks': total_chunks,
                'by_type': by_type,
                'asset_path': str(chunks_path) if chunks_path.exists() else None,
                'updated_at': mtime,
                'in_catalog': catalog_row is not None,
                'catalog_status': catalog_row.status if catalog_row else None,
                'catalog_filename': catalog_row.filename if catalog_row else None,
                'catalog_title': catalog_row.title if catalog_row else None,
            }
        )

    return {'documents': docs, 'total': len(docs)}


@app.delete('/ingested/{doc_id}')
def delete_ingested_doc(doc_id: str) -> dict[str, object]:
    target = ASSETS_DIR / doc_id
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail=f'Ingested doc not found: {doc_id}')

    shutil.rmtree(target)
    return {'deleted': True, 'doc_id': doc_id}


@app.get('/pdf/{doc_id}')
def get_pdf(doc_id: str):
    pdf_path = _resolve_pdf_path(doc_id)
    if pdf_path is None:
        raise HTTPException(status_code=404, detail=f'PDF not found for doc_id: {doc_id}')
    return FileResponse(
        path=str(pdf_path),
        media_type='application/pdf',
        headers={
            'Content-Disposition': f'inline; filename="{pdf_path.name}"',
            'X-Content-Type-Options': 'nosniff',
            'Cache-Control': 'no-store',
        },
    )


@app.get('/jobs')
def list_jobs(limit: int = Query(50, ge=1, le=200)) -> dict[str, object]:
    rows = JOB_MANAGER.list(limit=limit)
    return {'jobs': [_serialize_job(row) for row in rows], 'total': len(rows)}


@app.get('/jobs/{job_id}')
def get_job(job_id: str) -> dict[str, object]:
    try:
        return _serialize_job(JOB_MANAGER.get(job_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f'Unknown job id: {job_id}') from exc


@app.post('/jobs/upload')
async def upload_manual_job(
    file: UploadFile = File(...),
    doc_id: str | None = Form(default=None),
) -> dict[str, object]:
    if not file.filename:
        raise HTTPException(status_code=400, detail='Uploaded file name is required')
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail='Only PDF files are supported')

    resolved_doc_id = _slugify(doc_id or Path(file.filename).stem)
    ts = datetime.now(UTC).strftime('%Y%m%d%H%M%S')
    target_doc_id = f'{resolved_doc_id}_{ts}'

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    target_path = UPLOADS_DIR / f'{target_doc_id}.pdf'
    target_path.write_bytes(await file.read())

    cfg = load_config()
    job = JOB_MANAGER.submit(
        kind='upload',
        doc_id=target_doc_id,
        filename=file.filename,
        task=_ingest_uploaded_pdf_task(
            cfg=cfg,
            target_doc_id=target_doc_id,
            target_path=target_path,
            original_filename=file.filename,
        ),
    )
    return _serialize_job(job)


@app.post('/jobs/ingest/{doc_id}')
def ingest_catalog_job(doc_id: str) -> dict[str, object]:
    cfg = load_config()
    catalog = YamlDocumentCatalogAdapter(CATALOG_PATH)
    record = catalog.get(doc_id)

    if record is None:
        raise HTTPException(status_code=404, detail=f'Unknown doc id: {doc_id}')

    if record.status != 'present' or not record.filename:
        raise HTTPException(
            status_code=400,
            detail=f'Document {doc_id} is not ingestable (status={record.status})',
        )

    pdf_path = CATALOG_PATH.parent / record.filename
    if not pdf_path.exists():
        raise HTTPException(status_code=400, detail=f'PDF file missing for {doc_id}: {pdf_path}')

    job = JOB_MANAGER.submit(
        kind='catalog',
        doc_id=doc_id,
        filename=record.filename,
        task=_ingest_catalog_pdf_task(
            cfg=cfg,
            doc_id=doc_id,
            pdf_path=pdf_path,
        ),
    )
    return _serialize_job(job)


@app.post('/upload')
async def upload_manual(
    file: UploadFile = File(...),
    doc_id: str | None = Form(default=None),
) -> dict[str, object]:
    if not file.filename:
        raise HTTPException(status_code=400, detail='Uploaded file name is required')
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail='Only PDF files are supported')

    resolved_doc_id = _slugify(doc_id or Path(file.filename).stem)
    ts = datetime.now(UTC).strftime('%Y%m%d%H%M%S')
    target_doc_id = f'{resolved_doc_id}_{ts}'

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    target_path = UPLOADS_DIR / f'{target_doc_id}.pdf'
    target_path.write_bytes(await file.read())

    cfg = load_config()
    ocr_adapter = create_ocr_adapter(cfg.ocr_engine, cfg.ocr_fallback_engine)
    embedding_adapter = _build_embedding_adapter(cfg)
    vision_adapter = _build_vision(cfg)
    result = ingest_document_use_case(
        IngestDocumentInput(doc_id=target_doc_id, pdf_path=target_path),
        pdf_parser=PypdfParserAdapter(),
        ocr_adapter=ocr_adapter,
        table_extractor=SimpleTableExtractorAdapter(),
        chunk_store=FilesystemChunkStoreAdapter(ASSETS_DIR),
        embedding_adapter=embedding_adapter,
        vision_adapter=vision_adapter,
        vision_max_pages=cfg.vision_max_pages,
        page_workers=cfg.ingest_page_workers,
    )

    return {
        'doc_id': result.doc_id,
        'filename': file.filename,
        'stored_path': str(target_path),
        'asset_ref': result.asset_ref,
        'total_chunks': result.total_chunks,
        'by_type': result.by_type,
    }


@app.post('/ingest/{doc_id}')
def ingest_document(doc_id: str) -> dict[str, object]:
    cfg = load_config()
    catalog = YamlDocumentCatalogAdapter(CATALOG_PATH)
    record = catalog.get(doc_id)

    if record is None:
        raise HTTPException(status_code=404, detail=f'Unknown doc id: {doc_id}')

    if record.status != 'present' or not record.filename:
        raise HTTPException(
            status_code=400,
            detail=f'Document {doc_id} is not ingestable (status={record.status})',
        )

    pdf_path = CATALOG_PATH.parent / record.filename
    if not pdf_path.exists():
        raise HTTPException(status_code=400, detail=f'PDF file missing for {doc_id}: {pdf_path}')

    ocr_adapter = create_ocr_adapter(cfg.ocr_engine, cfg.ocr_fallback_engine)
    embedding_adapter = _build_embedding_adapter(cfg)
    vision_adapter = _build_vision(cfg)

    result = ingest_document_use_case(
        IngestDocumentInput(doc_id=doc_id, pdf_path=pdf_path),
        pdf_parser=PypdfParserAdapter(),
        ocr_adapter=ocr_adapter,
        table_extractor=SimpleTableExtractorAdapter(),
        chunk_store=FilesystemChunkStoreAdapter(ASSETS_DIR),
        embedding_adapter=embedding_adapter,
        vision_adapter=vision_adapter,
        vision_max_pages=cfg.vision_max_pages,
        page_workers=cfg.ingest_page_workers,
    )

    return {
        'doc_id': result.doc_id,
        'asset_ref': result.asset_ref,
        'total_chunks': result.total_chunks,
        'by_type': result.by_type,
    }


@app.get('/search')
def search(
    q: str = Query(..., min_length=1),
    doc_id: str | None = None,
    doc_ids: str | None = None,
    top_n: int = Query(8, ge=1, le=50),
    rerank_pool_size: int | None = Query(None, ge=0, le=100),
) -> dict[str, object]:
    cfg = load_config()
    selected_doc_ids = _parse_doc_ids_csv(doc_ids)
    reranker = _build_reranker(cfg)
    output = search_evidence_use_case(
        SearchEvidenceInput(
            query=q,
            doc_id=doc_id,
            top_n=top_n,
            rerank_pool_size=rerank_pool_size or cfg.reranker_pool_size,
        ),
        chunk_query=_scoped_chunk_query(selected_doc_ids),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=_build_vector_search(cfg),
        trace_logger=RetrievalTraceLogger(Path(cfg.retrieval_trace_file)),
        reranker=reranker,
    )

    return {
        'query': output.query,
        'intent': output.intent,
        'total_chunks_scanned': output.total_chunks_scanned,
        'hits': [
            {
                'chunk_id': hit.chunk_id,
                'doc_id': hit.doc_id,
                'content_type': hit.content_type,
                'page_start': hit.page_start,
                'page_end': hit.page_end,
                'section_path': hit.section_path,
                'figure_id': hit.figure_id,
                'table_id': hit.table_id,
                'score': hit.score,
                'keyword_score': hit.keyword_score,
                'vector_score': hit.vector_score,
                'rerank_score': hit.rerank_score,
                'snippet': hit.snippet,
            }
            for hit in output.hits
        ],
    }


@app.get('/answer')
def answer(
    q: str = Query(..., min_length=1),
    doc_id: str | None = None,
    doc_ids: str | None = None,
    top_n: int = Query(6, ge=1, le=20),
    rerank_pool_size: int | None = Query(None, ge=0, le=100),
) -> dict[str, object]:
    cfg = load_config()
    selected_doc_ids = _parse_doc_ids_csv(doc_ids)
    scoped_chunk_query = _scoped_chunk_query(selected_doc_ids)
    reranker = _build_reranker(cfg)
    planner, tool_executor, state_graph_runner, agent_trace_logger = _build_agentic_stack(
        cfg=cfg,
        chunk_query=scoped_chunk_query,
        reranker=reranker,
    )
    output = answer_question_use_case(
        AnswerQuestionInput(
            query=q,
            doc_id=doc_id,
            top_n=top_n,
            rerank_pool_size=rerank_pool_size or cfg.reranker_pool_size,
        ),
        chunk_query=scoped_chunk_query,
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=_build_vector_search(cfg),
        trace_logger=AnswerTraceLogger(Path(cfg.answer_trace_file)),
        llm=_build_llm(cfg),
        reranker=reranker,
        use_agentic_mode=cfg.use_agentic_mode,
        planner=planner,
        tool_executor=tool_executor,
        state_graph_runner=state_graph_runner,
        agent_trace_logger=agent_trace_logger,
        agent_max_iterations=cfg.agentic_max_iterations,
        agent_max_tool_calls=cfg.agentic_max_tool_calls,
        agent_timeout_seconds=cfg.agentic_timeout_seconds,
    )

    response: dict[str, object] = {
        'query': output.query,
        'intent': output.intent,
        'status': output.status,
        'confidence': output.confidence,
        'answer': output.answer,
        'follow_up_question': output.follow_up_question,
        'warnings': output.warnings,
        'total_chunks_scanned': output.total_chunks_scanned,
        'retrieved_chunk_ids': output.retrieved_chunk_ids,
        'citations': [
            {
                'doc_id': citation.doc_id,
                'page': citation.page,
                'section_path': citation.section_path,
                'figure_id': citation.figure_id,
                'table_id': citation.table_id,
                'label': citation.label,
            }
            for citation in output.citations
        ],
    }
    if cfg.include_reasoning_summary:
        response['reasoning_summary'] = output.reasoning_summary
    return response


@app.get('/evaluate/golden')
def evaluate_golden(
    doc_id: str | None = None,
    top_n: int = Query(6, ge=1, le=20),
    limit: int = Query(0, ge=0, le=200),
) -> dict[str, object]:
    cfg = load_config()
    chunk_query = FilesystemChunkQueryAdapter(ASSETS_DIR)
    reranker = _build_reranker(cfg)
    planner, tool_executor, state_graph_runner, agent_trace_logger = _build_agentic_stack(
        cfg=cfg,
        chunk_query=chunk_query,
        reranker=reranker,
    )
    output = run_golden_evaluation_use_case(
        RunGoldenEvaluationInput(
            catalog_path=CATALOG_PATH,
            golden_questions_path=GOLDEN_PATH,
            top_n=top_n,
            doc_id_filter=doc_id,
            limit=limit if limit > 0 else None,
        ),
        chunk_query=chunk_query,
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=_build_vector_search(cfg),
        trace_logger=AnswerTraceLogger(Path(cfg.answer_trace_file)),
        llm=_build_llm(cfg),
        reranker=reranker,
        use_agentic_mode=cfg.use_agentic_mode,
        planner=planner,
        tool_executor=tool_executor,
        state_graph_runner=state_graph_runner,
        agent_trace_logger=agent_trace_logger,
        agent_max_iterations=cfg.agentic_max_iterations,
        agent_max_tool_calls=cfg.agentic_max_tool_calls,
        agent_timeout_seconds=cfg.agentic_timeout_seconds,
    )

    return {
        'total_questions': output.total_questions,
        'passed_questions': output.passed_questions,
        'failed_questions': output.failed_questions,
        'pass_rate': output.pass_rate,
        'missing_docs': output.missing_docs,
        'results': [
            {
                'question_id': row.question_id,
                'doc': row.doc,
                'intent': row.intent,
                'question_type': row.question_type,
                'difficulty': row.difficulty,
                'rag_mode': row.rag_mode,
                'turn_count': row.turn_count,
                'answer_status': row.answer_status,
                'has_citation_doc_page': row.has_citation_doc_page,
                'grounded': row.grounded,
                'follow_up_expected': row.follow_up_expected,
                'follow_up_ok': row.follow_up_ok,
                'expected_keyword_hits': row.expected_keyword_hits,
                'expected_keyword_total': row.expected_keyword_total,
                'expected_match': row.expected_match,
                'missing_expected_keywords': row.missing_expected_keywords,
                'citation_count': row.citation_count,
                'pass_result': row.pass_result,
                'reasons': row.reasons,
                'follow_up_question': row.follow_up_question,
                'planned_turns': row.planned_turns,
                'executed_turns': row.executed_turns,
                'turn_prompts': row.turn_prompts,
                'turn_statuses': row.turn_statuses,
            }
            for row in output.results
        ],
    }
