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
from packages.adapters.agentic.factory import (
    create_agent_trace_logger,
    create_planner_adapter,
    create_state_graph_runner_adapter,
    create_tool_executor_adapter,
)
from packages.adapters.agentic.langchain_tool_executor_adapter import LangChainToolDefinition
from packages.adapters.embeddings.factory import create_embedding_adapter
from packages.adapters.llm.factory import create_llm_adapter
from packages.adapters.retrieval.filesystem_chunk_query_adapter import FilesystemChunkQueryAdapter
from packages.adapters.retrieval.hash_vector_search_adapter import HashVectorSearchAdapter
from packages.adapters.retrieval.metadata_vector_search_adapter import MetadataVectorSearchAdapter
from packages.adapters.retrieval.retrieval_trace_logger import RetrievalTraceLogger
from packages.adapters.retrieval.simple_keyword_search_adapter import SimpleKeywordSearchAdapter
from packages.adapters.reranker.factory import create_reranker_adapter
from packages.application.use_cases.search_evidence import SearchEvidenceInput, search_evidence_use_case
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
    parser.add_argument('--use-llm-answering', action='store_true')
    parser.add_argument('--llm-provider', default='local')
    parser.add_argument('--llm-base-url', default='http://localhost:11434')
    parser.add_argument('--llm-model', default='deepseek-r1:8b')
    parser.add_argument('--embedding-provider', default='hash', help='hash|ollama')
    parser.add_argument('--embedding-base-url', default='http://localhost:11434')
    parser.add_argument('--embedding-model', default='mxbai-embed-large:latest')
    parser.add_argument('--use-reranker', action='store_true')
    parser.add_argument('--reranker-provider', default='ollama', help='noop|ollama')
    parser.add_argument('--reranker-base-url', default='http://localhost:11434')
    parser.add_argument('--reranker-model', default='deepseek-r1:8b')
    parser.add_argument('--use-agentic-mode', action='store_true')
    parser.add_argument('--agentic-provider', default='langgraph')
    parser.add_argument('--agentic-max-iterations', type=int, default=4)
    parser.add_argument('--agentic-max-tool-calls', type=int, default=6)
    parser.add_argument('--agentic-timeout-seconds', type=float, default=20.0)
    parser.add_argument(
        '--agentic-trace-file',
        type=Path,
        default=Path('.context/reports/agent_traces.jsonl'),
    )
    parser.add_argument(
        '--retrieval-trace-file',
        type=Path,
        default=Path('.context/reports/retrieval_traces.jsonl'),
    )
    return parser.parse_args()


def _serialize_hit(hit) -> dict[str, object]:
    return {
        'chunk_id': hit.chunk_id,
        'doc_id': hit.doc_id,
        'content_type': hit.content_type,
        'page_start': hit.page_start,
        'page_end': hit.page_end,
        'section_path': hit.section_path,
        'figure_id': hit.figure_id,
        'table_id': hit.table_id,
        'score': hit.score,
        'keyword_score': hit.keyword_score,
        'vector_score': hit.vector_score,
        'rerank_score': hit.rerank_score,
        'snippet': hit.snippet,
    }


def _build_agentic_stack(
    *,
    args: argparse.Namespace,
    chunk_query: FilesystemChunkQueryAdapter,
    vector_search,
    reranker,
):
    if not args.use_agentic_mode:
        return None, None, None, None

    def _search_evidence_tool(arguments: dict[str, object]) -> dict[str, object]:
        query = str(arguments.get('query') or '').strip()
        if not query:
            raise ValueError('query is required')

        output = search_evidence_use_case(
            SearchEvidenceInput(
                query=query,
                doc_id=str(arguments.get('doc_id')).strip() if arguments.get('doc_id') else None,
                top_n=int(arguments.get('top_n') or args.top_n),
                top_k_keyword=int(arguments.get('top_k_keyword') or 20),
                top_k_vector=int(arguments.get('top_k_vector') or 20),
                rerank_pool_size=int(arguments.get('rerank_pool_size') or 24),
            ),
            chunk_query=chunk_query,
            keyword_search=SimpleKeywordSearchAdapter(),
            vector_search=vector_search,
            trace_logger=RetrievalTraceLogger(args.retrieval_trace_file),
            reranker=reranker,
        )
        return {
            'query': output.query,
            'intent': output.intent,
            'total_chunks_scanned': output.total_chunks_scanned,
            'hits': [_serialize_hit(hit) for hit in output.hits],
        }

    tool_defs = [
        LangChainToolDefinition(
            name='search_evidence',
            description='Retrieve ranked evidence chunks for grounded answering.',
            handler=_search_evidence_tool,
            required_args=('query',),
        ),
        LangChainToolDefinition(
            name='draft_answer',
            description='Placeholder tool for answer drafting stage.',
            handler=lambda _: {},
            required_args=(),
        ),
    ]

    planner = create_planner_adapter(
        provider=args.agentic_provider,
        base_url=args.llm_base_url,
        model=args.llm_model,
    )
    tool_executor = create_tool_executor_adapter(provider=args.agentic_provider, tools=tool_defs)
    state_graph_runner = create_state_graph_runner_adapter(provider=args.agentic_provider)
    agent_trace_logger = create_agent_trace_logger(args.agentic_trace_file)
    return planner, tool_executor, state_graph_runner, agent_trace_logger


def main() -> int:
    args = parse_args()

    vector_search = HashVectorSearchAdapter()
    if args.embedding_provider.strip().lower() in {'ollama', 'local'}:
        vector_search = MetadataVectorSearchAdapter(
            create_embedding_adapter(
                provider=args.embedding_provider,
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
    reranker = None
    if args.use_reranker:
        reranker = create_reranker_adapter(
            provider=args.reranker_provider,
            base_url=args.reranker_base_url,
            model=args.reranker_model,
        )

    chunk_query = FilesystemChunkQueryAdapter(args.assets_dir)
    planner, tool_executor, state_graph_runner, agent_trace_logger = _build_agentic_stack(
        args=args,
        chunk_query=chunk_query,
        vector_search=vector_search,
        reranker=reranker,
    )

    output = run_golden_evaluation_use_case(
        RunGoldenEvaluationInput(
            catalog_path=args.catalog_path,
            golden_questions_path=args.golden_path,
            top_n=args.top_n,
            doc_id_filter=args.doc_id,
            limit=args.limit if args.limit > 0 else None,
        ),
        chunk_query=chunk_query,
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=vector_search,
        trace_logger=AnswerTraceLogger(args.trace_file),
        llm=llm,
        reranker=reranker,
        use_agentic_mode=args.use_agentic_mode,
        planner=planner,
        tool_executor=tool_executor,
        state_graph_runner=state_graph_runner,
        agent_trace_logger=agent_trace_logger,
        agent_max_iterations=args.agentic_max_iterations,
        agent_max_tool_calls=args.agentic_max_tool_calls,
        agent_timeout_seconds=args.agentic_timeout_seconds,
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
