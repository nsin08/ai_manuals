from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
from packages.adapters.reranker.factory import create_reranker_adapter
from packages.adapters.retrieval.filesystem_chunk_query_adapter import FilesystemChunkQueryAdapter
from packages.adapters.retrieval.hash_vector_search_adapter import HashVectorSearchAdapter
from packages.adapters.retrieval.metadata_vector_search_adapter import MetadataVectorSearchAdapter
from packages.adapters.retrieval.retrieval_trace_logger import RetrievalTraceLogger
from packages.adapters.retrieval.simple_keyword_search_adapter import SimpleKeywordSearchAdapter
from packages.application.config import load_config
from packages.application.use_cases.run_golden_evaluation import (
    RunGoldenEvaluationInput,
    run_golden_evaluation_use_case,
)
from packages.application.use_cases.search_evidence import SearchEvidenceInput, search_evidence_use_case


def _default_golden_path() -> Path:
    v3 = Path('.context/project/data/golden_questions_v3.yaml')
    if v3.exists():
        return v3
    return Path('.context/project/data/golden_questions.yaml')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run and archive baseline golden evaluation on ingested docs')
    parser.add_argument('--catalog-path', type=Path, default=Path('.context/project/data/document_catalog.yaml'))
    parser.add_argument('--golden-path', type=Path, default=_default_golden_path())
    parser.add_argument('--assets-dir', type=Path, default=Path('data/assets'))
    parser.add_argument('--reports-root', type=Path, default=Path('.context/reports/golden_live'))
    parser.add_argument('--doc-id', default=None, help='Optional comma-separated doc ids to evaluate')
    parser.add_argument('--top-n', type=int, default=8)
    parser.add_argument('--limit', type=int, default=20)

    parser.add_argument('--enable-llm-answering', action='store_true')
    parser.add_argument('--disable-llm-answering', action='store_true')
    parser.add_argument('--enable-reranker', action='store_true')
    parser.add_argument('--disable-reranker', action='store_true')
    parser.add_argument('--enable-agentic-mode', action='store_true')
    parser.add_argument('--disable-agentic-mode', action='store_true')
    return parser.parse_args()


def _resolve_toggle(default: bool, *, enable: bool, disable: bool) -> bool:
    if enable and disable:
        raise ValueError('cannot pass both enable and disable flags')
    if enable:
        return True
    if disable:
        return False
    return default


def _parse_doc_ids(value: str | None) -> list[str] | None:
    if not value:
        return None
    rows = [item.strip() for item in value.split(',')]
    out = [item for item in rows if item]
    return out or None


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
    cfg,
    use_agentic_mode: bool,
    chunk_query: FilesystemChunkQueryAdapter,
    vector_search,
    reranker,
):
    if not use_agentic_mode:
        return None, None, None, None

    def _search_evidence_tool(arguments: dict[str, object]) -> dict[str, object]:
        query = str(arguments.get('query') or '').strip()
        if not query:
            raise ValueError('query is required')

        output = search_evidence_use_case(
            SearchEvidenceInput(
                query=query,
                doc_id=str(arguments.get('doc_id')).strip() if arguments.get('doc_id') else None,
                top_n=int(arguments.get('top_n') or 8),
                top_k_keyword=int(arguments.get('top_k_keyword') or 20),
                top_k_vector=int(arguments.get('top_k_vector') or 20),
                rerank_pool_size=int(arguments.get('rerank_pool_size') or 24),
            ),
            chunk_query=chunk_query,
            keyword_search=SimpleKeywordSearchAdapter(),
            vector_search=vector_search,
            trace_logger=RetrievalTraceLogger(Path(cfg.retrieval_trace_file)),
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
        provider=cfg.agentic_provider,
        base_url=cfg.llm_base_url,
        model=cfg.llm_model,
    )
    tool_executor = create_tool_executor_adapter(provider=cfg.agentic_provider, tools=tool_defs)
    state_graph_runner = create_state_graph_runner_adapter(provider=cfg.agentic_provider)
    agent_trace_logger = create_agent_trace_logger(Path(cfg.agentic_trace_file))
    return planner, tool_executor, state_graph_runner, agent_trace_logger


def _list_ingested_doc_ids(assets_dir: Path) -> list[str]:
    if not assets_dir.exists():
        return []
    return sorted(
        row.name
        for row in assets_dir.iterdir()
        if row.is_dir() and (row / 'chunks.jsonl').exists()
    )


def _group_pass_rate(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    groups = Counter(str(row.get(key) or '') for row in rows)
    for value in sorted(groups.keys()):
        group_rows = [row for row in rows if str(row.get(key) or '') == value]
        passed = sum(1 for row in group_rows if bool(row.get('pass_result')))
        out.append(
            {
                key: value,
                'total': len(group_rows),
                'passed': passed,
                'pass_rate_pct': round((passed * 100.0 / max(1, len(group_rows))), 2),
            }
        )
    return out


def _write_markdown_summary(path: Path, summary: dict[str, Any]) -> None:
    overall = summary['overall']
    lines: list[str] = [
        f"# Golden Live Run Summary ({overall['run_id']})",
        '',
        f"- Generated at (UTC): {overall['generated_at_utc']}",
        f"- Docs tested: {overall['docs_tested']}",
        f"- Total questions: {overall['total_questions']}",
        f"- Passed: {overall['passed_questions']}",
        f"- Failed: {overall['failed_questions']}",
        f"- Pass rate: {overall['pass_rate_pct']}%",
        f"- Expected-match passed: {overall['expected_match_passed']}/{overall['total_questions']}",
        f"- Citation doc+page present: {overall['citation_ok']}/{overall['total_questions']}",
        f"- Grounded answers: {overall['grounded_ok']}/{overall['total_questions']}",
        f"- Planned turns: {overall['planned_turns_total']}",
        f"- Executed turns: {overall['executed_turns_total']}",
        f"- Turn execution rate: {overall['turn_execution_rate_pct']}%",
        '',
        '## Per Doc',
    ]

    for row in summary['per_doc']:
        lines.append(
            '- '
            f"{row['doc_id']}: {row['passed']}/{row['total']} passed ({row['pass_rate_pct']}%), "
            f"expected-match {row['expected_match_passed']}/{row['total']}, "
            f"citations {row['citation_ok']}/{row['total']}, "
            f"grounded {row['grounded_ok']}/{row['total']}"
        )

    lines.extend(['', '## By Question Type'])
    for row in summary['by_question_type']:
        lines.append(f"- {row['question_type']}: {row['passed']}/{row['total']} passed ({row['pass_rate_pct']}%)")

    lines.extend(['', '## By Difficulty'])
    for row in summary['by_difficulty']:
        lines.append(f"- {row['difficulty']}: {row['passed']}/{row['total']} passed ({row['pass_rate_pct']}%)")

    lines.extend(['', '## By RAG Mode'])
    for row in summary['by_rag_mode']:
        lines.append(f"- {row['rag_mode']}: {row['passed']}/{row['total']} passed ({row['pass_rate_pct']}%)")

    lines.extend(['', '## Failure Taxonomy (Top Reasons)'])
    for row in summary['top_failure_reasons'][:10]:
        lines.append(f"- {row['reason']}: {row['count']}")

    lines.extend(['', '## Failure Taxonomy (Answer Status)'])
    for row in summary['by_answer_status']:
        lines.append(f"- {row['answer_status']}: {row['count']}")

    path.write_text('\n'.join(lines), encoding='utf-8')


def _load_recent_agent_trace_summary(trace_path: Path, start_utc: datetime) -> dict[str, Any]:
    if not trace_path.exists():
        return {
            'window_start_utc': start_utc.isoformat(),
            'total_events': 0,
            'plans': 0,
            'tool_executed': 0,
            'tool_failed': 0,
            'finalized': 0,
            'finalized_ok': 0,
            'finalized_not_found': 0,
            'trace_file_missing': True,
        }

    recent: list[dict[str, Any]] = []
    for line in trace_path.read_text(encoding='utf-8').splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        ts_text = str(payload.get('ts') or '').replace('Z', '+00:00')
        if not ts_text:
            continue
        try:
            ts = datetime.fromisoformat(ts_text)
        except ValueError:
            continue
        if ts >= start_utc:
            recent.append(payload)

    return {
        'window_start_utc': start_utc.isoformat(),
        'total_events': len(recent),
        'plans': sum(1 for row in recent if row.get('event') == 'plan_generated'),
        'tool_executed': sum(1 for row in recent if row.get('event') == 'tool_executed'),
        'tool_failed': sum(1 for row in recent if row.get('event') == 'tool_failed'),
        'finalized': sum(1 for row in recent if row.get('event') == 'graph_finalized'),
        'finalized_ok': sum(
            1
            for row in recent
            if row.get('event') == 'graph_finalized' and row.get('status') == 'ok'
        ),
        'finalized_not_found': sum(
            1
            for row in recent
            if row.get('event') == 'graph_finalized' and row.get('status') == 'not_found'
        ),
    }


def main() -> int:
    args = parse_args()
    base_cfg = load_config()
    run_start_utc = datetime.now(UTC)

    use_llm_answering = _resolve_toggle(
        base_cfg.use_llm_answering,
        enable=args.enable_llm_answering,
        disable=args.disable_llm_answering,
    )
    use_reranker = _resolve_toggle(
        base_cfg.use_reranker,
        enable=args.enable_reranker,
        disable=args.disable_reranker,
    )
    use_agentic_mode = _resolve_toggle(
        base_cfg.use_agentic_mode,
        enable=args.enable_agentic_mode,
        disable=args.disable_agentic_mode,
    )

    selected_doc_ids = _parse_doc_ids(args.doc_id)
    doc_ids = selected_doc_ids or _list_ingested_doc_ids(args.assets_dir)
    if not doc_ids:
        raise SystemExit('No ingested docs found to evaluate')

    run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir = args.reports_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / 'run_start_utc.txt').write_text(run_start_utc.isoformat(), encoding='utf-8')

    vector_search = HashVectorSearchAdapter()
    if base_cfg.embedding_provider.strip().lower() in {'ollama', 'local'}:
        vector_search = MetadataVectorSearchAdapter(
            create_embedding_adapter(
                provider=base_cfg.embedding_provider,
                base_url=base_cfg.embedding_base_url,
                model=base_cfg.embedding_model,
            )
        )

    llm = None
    if use_llm_answering:
        llm = create_llm_adapter(
            provider=base_cfg.llm_provider,
            base_url=base_cfg.llm_base_url,
            model=base_cfg.llm_model,
        )

    reranker = None
    if use_reranker:
        reranker = create_reranker_adapter(
            provider=base_cfg.reranker_provider,
            base_url=base_cfg.reranker_base_url,
            model=base_cfg.reranker_model,
        )

    chunk_query = FilesystemChunkQueryAdapter(args.assets_dir)
    planner, tool_executor, state_graph_runner, agent_trace_logger = _build_agentic_stack(
        cfg=base_cfg,
        use_agentic_mode=use_agentic_mode,
        chunk_query=chunk_query,
        vector_search=vector_search,
        reranker=reranker,
    )

    all_rows: list[dict[str, Any]] = []
    per_doc: list[dict[str, Any]] = []
    for doc_id in doc_ids:
        output = run_golden_evaluation_use_case(
            RunGoldenEvaluationInput(
                catalog_path=args.catalog_path,
                golden_questions_path=args.golden_path,
                top_n=args.top_n,
                doc_id_filter=doc_id,
                limit=args.limit if args.limit > 0 else None,
            ),
            chunk_query=chunk_query,
            keyword_search=SimpleKeywordSearchAdapter(),
            vector_search=vector_search,
            trace_logger=AnswerTraceLogger(Path(base_cfg.answer_trace_file)),
            llm=llm,
            reranker=reranker,
            use_agentic_mode=use_agentic_mode,
            planner=planner,
            tool_executor=tool_executor,
            state_graph_runner=state_graph_runner,
            agent_trace_logger=agent_trace_logger,
            agent_max_iterations=base_cfg.agentic_max_iterations,
            agent_max_tool_calls=base_cfg.agentic_max_tool_calls,
            agent_timeout_seconds=base_cfg.agentic_timeout_seconds,
        )

        doc_payload = {
            'total_questions': output.total_questions,
            'passed_questions': output.passed_questions,
            'failed_questions': output.failed_questions,
            'pass_rate': output.pass_rate,
            'missing_docs': output.missing_docs,
            'results': [asdict(row) for row in output.results],
        }
        (run_dir / f'golden_live_{doc_id}.json').write_text(
            json.dumps(doc_payload, indent=2),
            encoding='utf-8',
        )

        rows = doc_payload['results']
        all_rows.extend(rows)
        per_doc.append(
            {
                'doc_id': doc_id,
                'total': doc_payload['total_questions'],
                'passed': doc_payload['passed_questions'],
                'failed': doc_payload['failed_questions'],
                'pass_rate_pct': round(float(doc_payload['pass_rate']), 2),
                'expected_match_passed': sum(1 for row in rows if row.get('expected_match') is True),
                'citation_ok': sum(1 for row in rows if row.get('has_citation_doc_page') is True),
                'grounded_ok': sum(1 for row in rows if row.get('grounded') is True),
            }
        )

    failure_rows = [row for row in all_rows if not bool(row.get('pass_result'))]
    failure_reasons = Counter(
        reason
        for row in failure_rows
        for reason in (row.get('reasons') or [])
        if reason
    )
    answer_status_counts = Counter(str(row.get('answer_status') or '') for row in failure_rows)
    missing_keyword_counts = Counter(
        keyword
        for row in failure_rows
        for keyword in (row.get('missing_expected_keywords') or [])
        if keyword
    )

    overall = {
        'run_id': run_id,
        'generated_at_utc': datetime.now(UTC).isoformat(),
        'docs_tested': len(per_doc),
        'total_questions': len(all_rows),
        'passed_questions': sum(1 for row in all_rows if bool(row.get('pass_result'))),
        'failed_questions': sum(1 for row in all_rows if not bool(row.get('pass_result'))),
        'pass_rate_pct': round(
            sum(1 for row in all_rows if bool(row.get('pass_result'))) * 100.0 / max(1, len(all_rows)),
            2,
        ),
        'expected_match_passed': sum(1 for row in all_rows if row.get('expected_match') is True),
        'citation_ok': sum(1 for row in all_rows if row.get('has_citation_doc_page') is True),
        'grounded_ok': sum(1 for row in all_rows if row.get('grounded') is True),
        'planned_turns_total': sum(int(row.get('planned_turns') or 1) for row in all_rows),
        'executed_turns_total': sum(int(row.get('executed_turns') or 0) for row in all_rows),
        'golden_path': str(args.golden_path),
        'assets_dir': str(args.assets_dir),
        'use_agentic_mode': use_agentic_mode,
        'use_llm_answering': use_llm_answering,
        'use_reranker': use_reranker,
    }
    overall['turn_execution_rate_pct'] = round(
        overall['executed_turns_total'] * 100.0 / max(1, overall['planned_turns_total']),
        2,
    )

    summary_payload = {
        'overall': overall,
        'per_doc': per_doc,
        'by_question_type': _group_pass_rate(all_rows, 'question_type'),
        'by_difficulty': _group_pass_rate(all_rows, 'difficulty'),
        'by_rag_mode': _group_pass_rate(all_rows, 'rag_mode'),
        'top_failure_reasons': [
            {'reason': reason, 'count': count}
            for reason, count in failure_reasons.most_common()
        ],
        'by_answer_status': [
            {'answer_status': status, 'count': count}
            for status, count in sorted(answer_status_counts.items(), key=lambda x: (-x[1], x[0]))
        ],
        'missing_expected_keyword_counts': [
            {'keyword': keyword, 'count': count}
            for keyword, count in missing_keyword_counts.most_common(25)
        ],
    }
    (run_dir / 'run_summary.json').write_text(json.dumps(summary_payload, indent=2), encoding='utf-8')
    _write_markdown_summary(run_dir / 'run_summary.md', summary_payload)

    failed_cases_path_json = run_dir / 'failed_cases.json'
    failed_cases_path_csv = run_dir / 'failed_cases.csv'
    failed_cases_path_json.write_text(json.dumps(failure_rows, indent=2), encoding='utf-8')
    with failed_cases_path_csv.open('w', newline='', encoding='utf-8') as fh:
        fields = [
            'doc',
            'question_id',
            'question_type',
            'difficulty',
            'rag_mode',
            'answer_status',
            'expected_match',
            'planned_turns',
            'executed_turns',
            'missing_expected_keywords',
            'reasons',
        ]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in failure_rows:
            writer.writerow(
                {
                    'doc': row.get('doc'),
                    'question_id': row.get('question_id'),
                    'question_type': row.get('question_type'),
                    'difficulty': row.get('difficulty'),
                    'rag_mode': row.get('rag_mode'),
                    'answer_status': row.get('answer_status'),
                    'expected_match': row.get('expected_match'),
                    'planned_turns': row.get('planned_turns'),
                    'executed_turns': row.get('executed_turns'),
                    'missing_expected_keywords': ','.join(row.get('missing_expected_keywords') or []),
                    'reasons': ' | '.join(row.get('reasons') or []),
                }
            )

    trace_summary = _load_recent_agent_trace_summary(Path(base_cfg.agentic_trace_file), run_start_utc)
    (run_dir / 'agent_trace_summary.json').write_text(json.dumps(trace_summary, indent=2), encoding='utf-8')

    config_snapshot = {
        'run_id': run_id,
        'catalog_path': str(args.catalog_path),
        'golden_path': str(args.golden_path),
        'doc_ids': doc_ids,
        'top_n': args.top_n,
        'limit': args.limit,
        'use_agentic_mode': use_agentic_mode,
        'use_llm_answering': use_llm_answering,
        'use_reranker': use_reranker,
        'llm_provider': base_cfg.llm_provider,
        'llm_model': base_cfg.llm_model,
        'embedding_provider': base_cfg.embedding_provider,
        'embedding_model': base_cfg.embedding_model,
        'reranker_provider': base_cfg.reranker_provider,
        'reranker_model': base_cfg.reranker_model,
        'agentic_provider': base_cfg.agentic_provider,
        'agentic_limits': {
            'max_iterations': base_cfg.agentic_max_iterations,
            'max_tool_calls': base_cfg.agentic_max_tool_calls,
            'timeout_seconds': base_cfg.agentic_timeout_seconds,
        },
    }
    (run_dir / 'config_snapshot.json').write_text(json.dumps(config_snapshot, indent=2), encoding='utf-8')

    print(json.dumps({'run_id': run_id, 'run_dir': str(run_dir), 'overall': overall}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
