from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException

from packages.adapters.data_contracts.yaml_catalog_adapter import YamlDocumentCatalogAdapter
from packages.adapters.ocr.noop_ocr_adapter import NoopOcrAdapter
from packages.adapters.pdf.pypdf_parser_adapter import PypdfParserAdapter
from packages.adapters.storage.filesystem_chunk_store_adapter import FilesystemChunkStoreAdapter
from packages.adapters.tables.simple_table_extractor_adapter import SimpleTableExtractorAdapter
from packages.application.config import load_config
from packages.application.use_cases.ingest_document import (
    IngestDocumentInput,
    ingest_document_use_case,
)
from packages.application.use_cases.validate_data_contracts import (
    ValidateDataContractsInput,
    validate_data_contracts_use_case,
)


DATA_DIR = Path('.context/project/data')
CATALOG_PATH = DATA_DIR / 'document_catalog.yaml'
GOLDEN_PATH = DATA_DIR / 'golden_questions.yaml'
ASSETS_DIR = Path('data/assets')

app = FastAPI(title='Equipment Manuals Chatbot API', version='0.2.0')


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

    result = ingest_document_use_case(
        IngestDocumentInput(doc_id=doc_id, pdf_path=pdf_path),
        pdf_parser=PypdfParserAdapter(),
        ocr_adapter=NoopOcrAdapter(),
        table_extractor=SimpleTableExtractorAdapter(),
        chunk_store=FilesystemChunkStoreAdapter(ASSETS_DIR),
    )

    return {
        'doc_id': result.doc_id,
        'asset_ref': result.asset_ref,
        'total_chunks': result.total_chunks,
        'by_type': result.by_type,
    }
