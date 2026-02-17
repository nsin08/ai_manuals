from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.adapters.answering.answer_trace_logger import AnswerTraceLogger
from packages.adapters.retrieval.filesystem_chunk_query_adapter import FilesystemChunkQueryAdapter
from packages.adapters.retrieval.hash_vector_search_adapter import HashVectorSearchAdapter
from packages.adapters.retrieval.simple_keyword_search_adapter import SimpleKeywordSearchAdapter
from packages.application.use_cases.run_golden_evaluation import (
    RunGoldenEvaluationInput,
    run_golden_evaluation_use_case,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run golden-question evaluation')
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
    parser.add_argument('--assets-dir', type=Path, default=Path('data/assets'))
    parser.add_argument('--doc-id', default=None, help='Optional question doc filter')
    parser.add_argument('--top-n', type=int, default=6)
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument(
        '--trace-file',
        type=Path,
        default=Path('.context/reports/answer_traces.jsonl'),
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('.context/reports/golden_eval_summary.json'),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    output = run_golden_evaluation_use_case(
        RunGoldenEvaluationInput(
            catalog_path=args.catalog_path,
            golden_questions_path=args.golden_path,
            top_n=args.top_n,
            doc_id_filter=args.doc_id,
            limit=args.limit if args.limit > 0 else None,
        ),
        chunk_query=FilesystemChunkQueryAdapter(args.assets_dir),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
        trace_logger=AnswerTraceLogger(args.trace_file),
    )

    payload = {
        'total_questions': output.total_questions,
        'passed_questions': output.passed_questions,
        'failed_questions': output.failed_questions,
        'pass_rate': output.pass_rate,
        'missing_docs': output.missing_docs,
        'results': [asdict(row) for row in output.results],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
