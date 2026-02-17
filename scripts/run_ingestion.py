from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.adapters.data_contracts.yaml_catalog_adapter import YamlDocumentCatalogAdapter
from packages.adapters.ocr.noop_ocr_adapter import NoopOcrAdapter
from packages.adapters.pdf.pypdf_parser_adapter import PypdfParserAdapter
from packages.adapters.storage.filesystem_chunk_store_adapter import FilesystemChunkStoreAdapter
from packages.adapters.tables.simple_table_extractor_adapter import SimpleTableExtractorAdapter
from packages.application.use_cases.ingest_document import (
    IngestDocumentInput,
    ingest_document_use_case,
)



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run document ingestion for one doc_id')
    parser.add_argument('--doc-id', required=True, help='Document id from document_catalog.yaml')
    parser.add_argument(
        '--catalog',
        type=Path,
        default=Path('.context/project/data/document_catalog.yaml'),
        help='Path to catalog yaml',
    )
    parser.add_argument(
        '--assets-dir',
        type=Path,
        default=Path('data/assets'),
        help='Output directory for persisted chunk artifacts',
    )
    return parser.parse_args()



def main() -> int:
    args = parse_args()

    catalog = YamlDocumentCatalogAdapter(args.catalog)
    record = catalog.get(args.doc_id)
    if record is None:
        print(f'ERROR: unknown doc id: {args.doc_id}')
        return 1

    if record.status != 'present' or not record.filename:
        print(f'ERROR: doc id {args.doc_id} is not ingestable (status={record.status})')
        return 1

    pdf_path = args.catalog.parent / record.filename
    if not pdf_path.exists():
        print(f'ERROR: file not found for {args.doc_id}: {pdf_path}')
        return 1

    result = ingest_document_use_case(
        IngestDocumentInput(doc_id=args.doc_id, pdf_path=pdf_path),
        pdf_parser=PypdfParserAdapter(),
        ocr_adapter=NoopOcrAdapter(),
        table_extractor=SimpleTableExtractorAdapter(),
        chunk_store=FilesystemChunkStoreAdapter(args.assets_dir),
    )

    print(json.dumps({
        'doc_id': result.doc_id,
        'asset_ref': result.asset_ref,
        'total_chunks': result.total_chunks,
        'by_type': result.by_type,
    }, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
