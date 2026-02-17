from __future__ import annotations

import os
import time
from pathlib import Path

from packages.adapters.data_contracts.yaml_catalog_adapter import YamlDocumentCatalogAdapter
from packages.adapters.ocr.noop_ocr_adapter import NoopOcrAdapter
from packages.adapters.pdf.pypdf_parser_adapter import PypdfParserAdapter
from packages.adapters.storage.filesystem_chunk_store_adapter import FilesystemChunkStoreAdapter
from packages.adapters.tables.simple_table_extractor_adapter import SimpleTableExtractorAdapter
from packages.application.use_cases.ingest_document import (
    IngestDocumentInput,
    ingest_document_use_case,
)
from packages.application.use_cases.validate_data_contracts import (
    ValidateDataContractsInput,
    validate_data_contracts_use_case,
)



def run_startup_contract_validation() -> int:
    data_dir = Path('.context/project/data')
    result = validate_data_contracts_use_case(
        ValidateDataContractsInput(
            catalog_path=data_dir / 'document_catalog.yaml',
            golden_questions_path=data_dir / 'golden_questions.yaml',
            strict_files=False,
        )
    )

    print('Worker startup validation complete')
    print(f'Contract errors: {len(result.errors)}')
    print(f'Contract warnings: {len(result.warnings)}')

    if result.errors:
        for err in result.errors:
            print(f'ERROR: {err}')
        return 1
    return 0



def run_single_ingestion(doc_id: str) -> None:
    catalog_path = Path('.context/project/data/document_catalog.yaml')
    catalog = YamlDocumentCatalogAdapter(catalog_path)
    record = catalog.get(doc_id)

    if record is None:
        print(f'Worker ingestion skipped: unknown doc id {doc_id}')
        return
    if record.status != 'present' or not record.filename:
        print(f'Worker ingestion skipped: doc {doc_id} not ingestable (status={record.status})')
        return

    pdf_path = catalog_path.parent / record.filename
    if not pdf_path.exists():
        print(f'Worker ingestion skipped: missing file {pdf_path}')
        return

    result = ingest_document_use_case(
        IngestDocumentInput(doc_id=doc_id, pdf_path=pdf_path),
        pdf_parser=PypdfParserAdapter(),
        ocr_adapter=NoopOcrAdapter(),
        table_extractor=SimpleTableExtractorAdapter(),
        chunk_store=FilesystemChunkStoreAdapter(Path('data/assets')),
    )

    print(
        f'Worker ingestion completed for {doc_id}: '
        f'{result.total_chunks} chunks -> {result.asset_ref}'
    )



def main() -> int:
    if run_startup_contract_validation() != 0:
        return 1

    ingest_doc_id = os.getenv('INGEST_DOC_ID', '').strip()
    if ingest_doc_id:
        run_single_ingestion(ingest_doc_id)

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print('Worker stopping')
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
