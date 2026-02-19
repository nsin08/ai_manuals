from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.adapters.answering.answer_trace_logger import AnswerTraceLogger
from packages.adapters.embeddings.factory import create_embedding_adapter
from packages.adapters.llm.factory import create_llm_adapter
from packages.adapters.retrieval.filesystem_chunk_query_adapter import FilesystemChunkQueryAdapter
from packages.adapters.retrieval.hash_vector_search_adapter import HashVectorSearchAdapter
from packages.adapters.retrieval.metadata_vector_search_adapter import MetadataVectorSearchAdapter
from packages.adapters.retrieval.simple_keyword_search_adapter import SimpleKeywordSearchAdapter
from packages.application.use_cases.answer_question import (
    AnswerQuestionInput,
    answer_question_use_case,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run grounded answer generation')
    parser.add_argument('--query', required=True, help='Question text')
    parser.add_argument('--doc-id', default=None, help='Optional doc id filter')
    parser.add_argument('--top-n', type=int, default=6, help='Number of evidence hits to use')
    parser.add_argument('--assets-dir', type=Path, default=Path('data/assets'))
    parser.add_argument(
        '--trace-file',
        type=Path,
        default=Path('.context/reports/answer_traces.jsonl'),
    )
    parser.add_argument('--use-llm-answering', action='store_true')
    parser.add_argument('--llm-provider', default='local')
    parser.add_argument('--llm-base-url', default='http://localhost:11434')
    parser.add_argument('--llm-model', default='deepseek-r1:8b')
    parser.add_argument('--embedding-provider', default='hash', help='hash|ollama')
    parser.add_argument('--embedding-base-url', default='http://localhost:11434')
    parser.add_argument('--embedding-model', default='mxbai-embed-large:latest')
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    vector_search = HashVectorSearchAdapter()
    if args.embedding_provider.strip().lower() == 'ollama':
        vector_search = MetadataVectorSearchAdapter(
            create_embedding_adapter(
                provider='ollama',
                base_url=args.embedding_base_url,
                model=args.embedding_model,
            )
        )

    llm = None
    if args.use_llm_answering:
        llm = create_llm_adapter(
            provider=args.llm_provider,
            base_url=args.llm_base_url,
            model=args.llm_model,
        )

    output = answer_question_use_case(
        AnswerQuestionInput(query=args.query, doc_id=args.doc_id, top_n=args.top_n),
        chunk_query=FilesystemChunkQueryAdapter(args.assets_dir),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=vector_search,
        trace_logger=AnswerTraceLogger(args.trace_file),
        llm=llm,
    )

    print(
        json.dumps(
            {
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
            },
            indent=2,
        )
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
