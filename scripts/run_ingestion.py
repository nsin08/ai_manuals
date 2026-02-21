from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.adapters.data_contracts.yaml_catalog_adapter import YamlDocumentCatalogAdapter
from packages.adapters.embeddings.factory import create_embedding_adapter
from packages.adapters.ocr.factory import create_ocr_adapter
from packages.adapters.pdf.pypdf_parser_adapter import PypdfParserAdapter
from packages.adapters.storage.filesystem_chunk_store_adapter import FilesystemChunkStoreAdapter
from packages.adapters.tables.simple_table_extractor_adapter import SimpleTableExtractorAdapter
from packages.adapters.vision.factory import create_vision_adapter
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
    parser.add_argument('--ocr-engine', default='paddle', help='OCR engine: paddle|tesseract|noop')
    parser.add_argument('--ocr-fallback', default='tesseract', help='Fallback OCR engine')
    parser.add_argument('--embedding-provider', default='hash', help='Embedding provider: hash|ollama')
    parser.add_argument('--embedding-base-url', default='http://localhost:11434')
    parser.add_argument('--embedding-model', default='mxbai-embed-large:latest')
    parser.add_argument('--embedding-second-pass-max-chars', type=int, default=2048)
    parser.add_argument('--use-vision-ingestion', action='store_true')
    parser.add_argument('--vision-provider', default='ollama', help='Vision provider: noop|ollama')
    parser.add_argument('--vision-base-url', default='http://localhost:11434')
    parser.add_argument('--vision-model', default='qwen2.5vl:7b')
    parser.add_argument('--vision-max-pages', type=int, default=40)
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

    ocr_adapter = create_ocr_adapter(args.ocr_engine, args.ocr_fallback)
    embedding_adapter = create_embedding_adapter(
        provider=args.embedding_provider,
        base_url=args.embedding_base_url,
        model=args.embedding_model,
    )
    vision_adapter = None
    if args.use_vision_ingestion:
        vision_adapter = create_vision_adapter(
            provider=args.vision_provider,
            base_url=args.vision_base_url,
            model=args.vision_model,
        )

    result = ingest_document_use_case(
        IngestDocumentInput(doc_id=args.doc_id, pdf_path=pdf_path),
        pdf_parser=PypdfParserAdapter(),
        ocr_adapter=ocr_adapter,
        table_extractor=SimpleTableExtractorAdapter(),
        chunk_store=FilesystemChunkStoreAdapter(args.assets_dir),
        embedding_adapter=embedding_adapter,
        vision_adapter=vision_adapter,
        vision_max_pages=args.vision_max_pages,
        embedding_second_pass_max_chars=args.embedding_second_pass_max_chars,
    )

    print(json.dumps({
        'doc_id': result.doc_id,
        'asset_ref': result.asset_ref,
        'total_chunks': result.total_chunks,
        'by_type': result.by_type,
        'embedding_attempted': result.embedding_attempted,
        'embedding_success_count': result.embedding_success_count,
        'embedding_failed_count': result.embedding_failed_count,
        'embedding_coverage': result.embedding_coverage,
        'embedding_second_pass_attempted': result.embedding_second_pass_attempted,
        'embedding_second_pass_recovered': result.embedding_second_pass_recovered,
        'embedding_failure_reasons': result.embedding_failure_reasons or {},
        'warnings': result.warnings or [],
    }, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
