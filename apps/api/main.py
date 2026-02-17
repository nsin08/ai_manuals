from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

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
from packages.application.use_cases.ingest_document import (
    IngestDocumentInput,
    ingest_document_use_case,
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

app = FastAPI(title='Equipment Manuals Chatbot API', version='0.4.0')


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
                'score': hit.score,
                'keyword_score': hit.keyword_score,
                'vector_score': hit.vector_score,
                'snippet': hit.snippet,
            }
            for hit in output.hits
        ],
    }
