from __future__ import annotations

import argparse
import json
import shutil
import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.adapters.data_contracts.yaml_catalog_adapter import YamlDocumentCatalogAdapter
from packages.adapters.ocr.factory import create_ocr_adapter
from packages.adapters.pdf.pypdf_parser_adapter import PypdfParserAdapter
from packages.adapters.retrieval.filesystem_chunk_query_adapter import FilesystemChunkQueryAdapter
from packages.adapters.retrieval.hash_vector_search_adapter import HashVectorSearchAdapter
from packages.adapters.retrieval.simple_keyword_search_adapter import SimpleKeywordSearchAdapter
from packages.adapters.storage.filesystem_chunk_store_adapter import FilesystemChunkStoreAdapter
from packages.adapters.tables.simple_table_extractor_adapter import SimpleTableExtractorAdapter
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Capture local performance baseline for Phase 5')
    parser.add_argument(
        '--catalog-path',
        type=Path,
        default=Path('.context/project/data/document_catalog.yaml'),
    )
    parser.add_argument(
        '--golden-path',
        type=Path,
        default=Path('.context/project/data/golden_questions.yaml'),
    )
    parser.add_argument(
        '--assets-dir',
        type=Path,
        default=Path('.context/temp/phase5_perf_assets'),
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('.context/reports/phase5_performance_baseline.json'),
    )
    parser.add_argument('--ocr-engine', default='noop')
    parser.add_argument('--ocr-fallback', default='noop')
    return parser.parse_args()


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, int(round(0.95 * (len(ordered) - 1))))
    return ordered[index]


def main() -> int:
    args = parse_args()
    catalog = YamlDocumentCatalogAdapter(args.catalog_path)

    if args.assets_dir.exists():
        shutil.rmtree(args.assets_dir)
    args.assets_dir.mkdir(parents=True, exist_ok=True)

    ingest_docs = ['rockwell_powerflex_40', 'neets_module_4']
    ingest_rows: list[dict[str, object]] = []

    for doc_id in ingest_docs:
        record = catalog.get(doc_id)
        if record is None or record.status != 'present' or not record.filename:
            continue
        pdf_path = args.catalog_path.parent / record.filename
        if not pdf_path.exists():
            continue

        start = time.perf_counter()
        result = ingest_document_use_case(
            IngestDocumentInput(doc_id=doc_id, pdf_path=pdf_path),
            pdf_parser=PypdfParserAdapter(),
            ocr_adapter=create_ocr_adapter(args.ocr_engine, args.ocr_fallback),
            table_extractor=SimpleTableExtractorAdapter(),
            chunk_store=FilesystemChunkStoreAdapter(args.assets_dir),
        )
        elapsed = round(time.perf_counter() - start, 3)
        ingest_rows.append(
            {
                'doc_id': doc_id,
                'duration_seconds': elapsed,
                'total_chunks': result.total_chunks,
                'by_type': result.by_type,
            }
        )

    chunk_query = FilesystemChunkQueryAdapter(args.assets_dir)
    answer_queries = [
        ('rockwell_powerflex_40', 'Find the fault code corrective action guidance.'),
        ('rockwell_powerflex_40', 'What are installation clearance requirements?'),
        ('neets_module_4', 'Explain series vs parallel circuits in schematics.'),
        ('neets_module_4', 'What does the AWG table describe?'),
    ]
    answer_rows: list[dict[str, object]] = []
    latencies: list[float] = []

    for doc_id, query in answer_queries:
        start = time.perf_counter()
        output = answer_question_use_case(
            AnswerQuestionInput(query=query, doc_id=doc_id, top_n=6),
            chunk_query=chunk_query,
            keyword_search=SimpleKeywordSearchAdapter(),
            vector_search=HashVectorSearchAdapter(),
            trace_logger=None,
        )
        elapsed = round(time.perf_counter() - start, 3)
        latencies.append(elapsed)
        answer_rows.append(
            {
                'doc_id': doc_id,
                'query': query,
                'duration_seconds': elapsed,
                'status': output.status,
                'citation_count': len(output.citations),
            }
        )

    eval_start = time.perf_counter()
    eval_output = run_golden_evaluation_use_case(
        RunGoldenEvaluationInput(
            catalog_path=args.catalog_path,
            golden_questions_path=args.golden_path,
            doc_id_filter='rockwell_powerflex_40',
            top_n=6,
            limit=5,
        ),
        chunk_query=chunk_query,
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
        trace_logger=None,
    )
    eval_elapsed = round(time.perf_counter() - eval_start, 3)

    payload = {
        'baseline_scope': {
            'ingested_docs': [row['doc_id'] for row in ingest_rows],
            'answer_query_count': len(answer_rows),
            'golden_eval_doc': 'rockwell_powerflex_40',
            'golden_eval_limit': 5,
        },
        'ingestion': {
            'runs': ingest_rows,
            'mean_seconds': round(
                statistics.mean([float(row['duration_seconds']) for row in ingest_rows]), 3
            )
            if ingest_rows
            else 0.0,
        },
        'answers': {
            'runs': answer_rows,
            'latency_mean_seconds': round(statistics.mean(latencies), 3) if latencies else 0.0,
            'latency_median_seconds': round(statistics.median(latencies), 3) if latencies else 0.0,
            'latency_p95_seconds': round(_p95(latencies), 3) if latencies else 0.0,
        },
        'golden_evaluation': {
            'duration_seconds': eval_elapsed,
            'total_questions': eval_output.total_questions,
            'passed_questions': eval_output.passed_questions,
            'failed_questions': eval_output.failed_questions,
            'pass_rate': eval_output.pass_rate,
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
