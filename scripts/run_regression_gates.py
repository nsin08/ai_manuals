from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from dataclasses import asdict
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
from packages.application.use_cases.ingest_document import (
    IngestDocumentInput,
    ingest_document_use_case,
)
from packages.application.use_cases.run_golden_evaluation import (
    RunGoldenEvaluationInput,
    run_golden_evaluation_use_case,
)
from packages.application.use_cases.validate_data_contracts import (
    ValidateDataContractsInput,
    validate_data_contracts_use_case,
)


def _default_golden_path() -> Path:
    v3_path = Path('.context/project/data/golden_questions_v3.yaml')
    if v3_path.exists():
        return v3_path
    return Path('.context/project/data/golden_questions.yaml')


def _pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run strict regression gates for Phase 5')
    parser.add_argument(
        '--catalog-path',
        type=Path,
        default=Path('.context/project/data/document_catalog.yaml'),
    )
    parser.add_argument(
        '--golden-path',
        type=Path,
        default=_default_golden_path(),
    )
    parser.add_argument('--doc-id', default='rockwell_powerflex_40')
    parser.add_argument('--top-n', type=int, default=6)
    parser.add_argument('--limit', type=int, default=5)
    parser.add_argument('--min-pass-rate', type=float, default=80.0)
    parser.add_argument('--min-grounded-rate', type=float, default=98.0)
    parser.add_argument('--min-turn-execution-rate', type=float, default=98.0)
    parser.add_argument('--ocr-engine', default='noop')
    parser.add_argument('--ocr-fallback', default='noop')
    parser.add_argument(
        '--assets-dir',
        type=Path,
        default=Path('.context/temp/phase5_regression_assets'),
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('.context/reports/phase5_regression_gate.json'),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    checks: list[dict[str, object]] = []

    validation = validate_data_contracts_use_case(
        ValidateDataContractsInput(
            catalog_path=args.catalog_path,
            golden_questions_path=args.golden_path,
            strict_files=True,
        )
    )
    checks.append(
        {
            'name': 'data_contracts_strict',
            'passed': validation.is_valid(),
            'errors': validation.errors,
            'warnings': validation.warnings,
        }
    )
    if not validation.is_valid():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({'checks': checks}, indent=2), encoding='utf-8')
        print(json.dumps({'checks': checks}, indent=2))
        return 1

    catalog = YamlDocumentCatalogAdapter(args.catalog_path)
    doc = catalog.get(args.doc_id)
    if doc is None or doc.status != 'present' or not doc.filename:
        checks.append({'name': 'doc_present_in_catalog', 'passed': False, 'doc_id': args.doc_id})
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({'checks': checks}, indent=2), encoding='utf-8')
        print(json.dumps({'checks': checks}, indent=2))
        return 1

    pdf_path = args.catalog_path.parent / doc.filename
    if not pdf_path.exists():
        checks.append(
            {
                'name': 'doc_file_exists',
                'passed': False,
                'doc_id': args.doc_id,
                'pdf_path': str(pdf_path),
            }
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({'checks': checks}, indent=2), encoding='utf-8')
        print(json.dumps({'checks': checks}, indent=2))
        return 1

    if args.assets_dir.exists():
        shutil.rmtree(args.assets_dir)
    args.assets_dir.mkdir(parents=True, exist_ok=True)

    ingest_start = time.perf_counter()
    ingest_result = ingest_document_use_case(
        IngestDocumentInput(doc_id=args.doc_id, pdf_path=pdf_path),
        pdf_parser=PypdfParserAdapter(),
        ocr_adapter=create_ocr_adapter(args.ocr_engine, args.ocr_fallback),
        table_extractor=SimpleTableExtractorAdapter(),
        chunk_store=FilesystemChunkStoreAdapter(args.assets_dir),
    )
    ingest_secs = round(time.perf_counter() - ingest_start, 3)
    checks.append(
        {
            'name': 'ingestion',
            'passed': ingest_result.total_chunks > 0,
            'doc_id': args.doc_id,
            'total_chunks': ingest_result.total_chunks,
            'duration_seconds': ingest_secs,
        }
    )

    eval_start = time.perf_counter()
    eval_result = run_golden_evaluation_use_case(
        RunGoldenEvaluationInput(
            catalog_path=args.catalog_path,
            golden_questions_path=args.golden_path,
            top_n=args.top_n,
            doc_id_filter=args.doc_id,
            limit=args.limit,
        ),
        chunk_query=FilesystemChunkQueryAdapter(args.assets_dir),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
        trace_logger=None,
    )
    eval_secs = round(time.perf_counter() - eval_start, 3)
    total_questions = eval_result.total_questions
    grounded_questions = sum(1 for row in eval_result.results if row.grounded)
    grounded_rate = _pct(grounded_questions, total_questions)
    turn_execution_questions = sum(
        1 for row in eval_result.results if row.executed_turns >= row.planned_turns
    )
    turn_execution_rate = _pct(turn_execution_questions, total_questions)
    planned_turns_total = sum(row.planned_turns for row in eval_result.results)
    executed_turns_total = sum(row.executed_turns for row in eval_result.results)

    pass_rate_ok = eval_result.pass_rate >= args.min_pass_rate
    checks.append(
        {
            'name': 'golden_threshold',
            'passed': pass_rate_ok and not eval_result.missing_docs,
            'min_pass_rate': args.min_pass_rate,
            'actual_pass_rate': eval_result.pass_rate,
            'missing_docs': eval_result.missing_docs,
            'total_questions': eval_result.total_questions,
            'failed_questions': eval_result.failed_questions,
            'duration_seconds': eval_secs,
        }
    )
    checks.append(
        {
            'name': 'grounded_threshold',
            'passed': grounded_rate >= args.min_grounded_rate and not eval_result.missing_docs,
            'min_grounded_rate': args.min_grounded_rate,
            'actual_grounded_rate': grounded_rate,
            'grounded_questions': grounded_questions,
            'total_questions': total_questions,
        }
    )
    checks.append(
        {
            'name': 'turn_execution_threshold',
            'passed': turn_execution_rate >= args.min_turn_execution_rate and not eval_result.missing_docs,
            'min_turn_execution_rate': args.min_turn_execution_rate,
            'actual_turn_execution_rate': turn_execution_rate,
            'turn_execution_questions': turn_execution_questions,
            'total_questions': total_questions,
            'planned_turns_total': planned_turns_total,
            'executed_turns_total': executed_turns_total,
        }
    )

    overall_passed = all(bool(item.get('passed')) for item in checks)
    payload = {
        'overall_passed': overall_passed,
        'doc_id': args.doc_id,
        'limit': args.limit,
        'top_n': args.top_n,
        'total_duration_seconds': round(time.perf_counter() - started, 3),
        'checks': checks,
        'evaluation_summary': {
            'total_questions': eval_result.total_questions,
            'passed_questions': eval_result.passed_questions,
            'failed_questions': eval_result.failed_questions,
            'pass_rate': eval_result.pass_rate,
            'grounded_questions': grounded_questions,
            'grounded_rate': grounded_rate,
            'turn_execution_questions': turn_execution_questions,
            'turn_execution_rate': turn_execution_rate,
            'planned_turns_total': planned_turns_total,
            'executed_turns_total': executed_turns_total,
            'missing_docs': eval_result.missing_docs,
            'results': [asdict(row) for row in eval_result.results],
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(json.dumps(payload, indent=2))

    return 0 if overall_passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
