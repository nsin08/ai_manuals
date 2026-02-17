from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile

from packages.adapters.answering.answer_trace_logger import AnswerTraceLogger
from packages.adapters.data_contracts.yaml_catalog_adapter import YamlDocumentCatalogAdapter
from packages.adapters.ocr.factory import create_ocr_adapter
from packages.adapters.pdf.pypdf_parser_adapter import PypdfParserAdapter
from packages.adapters.retrieval.filesystem_chunk_query_adapter import FilesystemChunkQueryAdapter
from packages.adapters.retrieval.hash_vector_search_adapter import HashVectorSearchAdapter
from packages.adapters.retrieval.retrieval_trace_logger import RetrievalTraceLogger
from packages.adapters.retrieval.simple_keyword_search_adapter import SimpleKeywordSearchAdapter
from packages.adapters.storage.filesystem_chunk_store_adapter import FilesystemChunkStoreAdapter
from packages.adapters.tables.simple_table_extractor_adapter import SimpleTableExtractorAdapter
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

app = FastAPI(title='Equipment Manuals Chatbot API', version='0.6.0')


def _slugify(value: str) -> str:
    slug = re.sub(r'[^a-zA-Z0-9_-]+', '_', value.strip().lower())
    slug = slug.strip('_')
    return slug or 'uploaded_manual'


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
    result = ingest_document_use_case(
        IngestDocumentInput(doc_id=target_doc_id, pdf_path=target_path),
        pdf_parser=PypdfParserAdapter(),
        ocr_adapter=ocr_adapter,
        table_extractor=SimpleTableExtractorAdapter(),
        chunk_store=FilesystemChunkStoreAdapter(ASSETS_DIR),
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

    result = ingest_document_use_case(
        IngestDocumentInput(doc_id=doc_id, pdf_path=pdf_path),
        pdf_parser=PypdfParserAdapter(),
        ocr_adapter=ocr_adapter,
        table_extractor=SimpleTableExtractorAdapter(),
        chunk_store=FilesystemChunkStoreAdapter(ASSETS_DIR),
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
    top_n: int = Query(8, ge=1, le=50),
) -> dict[str, object]:
    cfg = load_config()
    output = search_evidence_use_case(
        SearchEvidenceInput(query=q, doc_id=doc_id, top_n=top_n),
        chunk_query=FilesystemChunkQueryAdapter(ASSETS_DIR),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
        trace_logger=RetrievalTraceLogger(Path(cfg.retrieval_trace_file)),
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
                'snippet': hit.snippet,
            }
            for hit in output.hits
        ],
    }


@app.get('/answer')
def answer(
    q: str = Query(..., min_length=1),
    doc_id: str | None = None,
    top_n: int = Query(6, ge=1, le=20),
) -> dict[str, object]:
    cfg = load_config()
    output = answer_question_use_case(
        AnswerQuestionInput(query=q, doc_id=doc_id, top_n=top_n),
        chunk_query=FilesystemChunkQueryAdapter(ASSETS_DIR),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
        trace_logger=AnswerTraceLogger(Path(cfg.answer_trace_file)),
    )

    return {
        'query': output.query,
        'intent': output.intent,
        'status': output.status,
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


@app.get('/evaluate/golden')
def evaluate_golden(
    doc_id: str | None = None,
    top_n: int = Query(6, ge=1, le=20),
    limit: int = Query(0, ge=0, le=200),
) -> dict[str, object]:
    cfg = load_config()
    output = run_golden_evaluation_use_case(
        RunGoldenEvaluationInput(
            catalog_path=CATALOG_PATH,
            golden_questions_path=GOLDEN_PATH,
            top_n=top_n,
            doc_id_filter=doc_id,
            limit=limit if limit > 0 else None,
        ),
        chunk_query=FilesystemChunkQueryAdapter(ASSETS_DIR),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
        trace_logger=AnswerTraceLogger(Path(cfg.answer_trace_file)),
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
                'answer_status': row.answer_status,
                'has_citation_doc_page': row.has_citation_doc_page,
                'grounded': row.grounded,
                'follow_up_expected': row.follow_up_expected,
                'follow_up_ok': row.follow_up_ok,
                'citation_count': row.citation_count,
                'pass_result': row.pass_result,
                'reasons': row.reasons,
                'follow_up_question': row.follow_up_question,
            }
            for row in output.results
        ],
    }
