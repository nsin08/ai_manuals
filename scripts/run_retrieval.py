from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.adapters.retrieval.filesystem_chunk_query_adapter import FilesystemChunkQueryAdapter
from packages.adapters.retrieval.hash_vector_search_adapter import HashVectorSearchAdapter
from packages.adapters.retrieval.retrieval_trace_logger import RetrievalTraceLogger
from packages.adapters.retrieval.simple_keyword_search_adapter import SimpleKeywordSearchAdapter
from packages.application.use_cases.search_evidence import SearchEvidenceInput, search_evidence_use_case



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run hybrid evidence retrieval')
    parser.add_argument('--query', required=True, help='Search query text')
    parser.add_argument('--doc-id', default=None, help='Optional doc id filter')
    parser.add_argument('--top-n', type=int, default=8, help='Number of hits to return')
    parser.add_argument('--assets-dir', type=Path, default=Path('data/assets'))
    parser.add_argument(
        '--trace-file',
        type=Path,
        default=Path('.context/reports/retrieval_traces.jsonl'),
    )
    return parser.parse_args()



def main() -> int:
    args = parse_args()

    output = search_evidence_use_case(
        SearchEvidenceInput(query=args.query, doc_id=args.doc_id, top_n=args.top_n),
        chunk_query=FilesystemChunkQueryAdapter(args.assets_dir),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
        trace_logger=RetrievalTraceLogger(args.trace_file),
    )

    print(
        json.dumps(
            {
                'query': output.query,
                'intent': output.intent,
                'total_chunks_scanned': output.total_chunks_scanned,
                'hits': [
                    {
                        'chunk_id': h.chunk_id,
                        'doc_id': h.doc_id,
                        'content_type': h.content_type,
                        'page_start': h.page_start,
                        'score': h.score,
                        'snippet': h.snippet,
                    }
                    for h in output.hits
                ],
            },
            indent=2,
        )
    )

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
