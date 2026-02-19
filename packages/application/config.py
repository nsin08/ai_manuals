from __future__ import annotations

import os
from dataclasses import dataclass


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


def _env_alias(keys: list[str], default: str) -> str:
    for key in keys:
        value = os.getenv(key)
        if value is not None and value != '':
            return value
    return default


@dataclass(frozen=True)
class AppConfig:
    app_env: str
    database_url: str
    redis_url: str
    llm_provider: str
    asset_store: str
    ocr_engine: str
    ocr_fallback_engine: str
    ingest_concurrency: int
    ingest_page_workers: int
    retrieval_trace_file: str
    answer_trace_file: str
    use_llm_answering: bool
    llm_base_url: str
    llm_model: str
    embedding_provider: str
    embedding_base_url: str
    embedding_model: str
    use_reranker: bool
    reranker_provider: str
    reranker_base_url: str
    reranker_model: str
    reranker_pool_size: int
    use_vision_ingestion: bool
    vision_provider: str
    vision_base_url: str
    vision_model: str
    vision_max_pages: int


def load_config() -> AppConfig:
    return AppConfig(
        app_env=_env('APP_ENV', 'local'),
        database_url=_env(
            'DATABASE_URL', 'postgresql://ai_manuals:ai_manuals@localhost:5432/ai_manuals'
        ),
        redis_url=_env('REDIS_URL', 'redis://localhost:6379/0'),
        llm_provider=_env('LLM_PROVIDER', 'local'),
        asset_store=_env('ASSET_STORE', 'filesystem'),
        ocr_engine=_env('OCR_ENGINE', 'paddle'),
        ocr_fallback_engine=_env('OCR_FALLBACK_ENGINE', 'tesseract'),
        ingest_concurrency=int(_env('INGEST_CONCURRENCY', '2')),
        ingest_page_workers=int(_env('INGEST_PAGE_WORKERS', '4')),
        retrieval_trace_file=_env('RETRIEVAL_TRACE_FILE', '.context/reports/retrieval_traces.jsonl'),
        answer_trace_file=_env('ANSWER_TRACE_FILE', '.context/reports/answer_traces.jsonl'),
        use_llm_answering=_env('USE_LLM_ANSWERING', 'false').strip().lower() == 'true',
        llm_base_url=_env_alias(['LLM_BASE_URL', 'LOCAL_LLM_BASE_URL'], 'http://localhost:11434'),
        llm_model=_env_alias(['LLM_MODEL', 'LOCAL_LLM_MODEL'], 'deepseek-r1:8b'),
        embedding_provider=_env('EMBEDDING_PROVIDER', 'hash'),
        embedding_base_url=_env_alias(
            ['EMBEDDING_BASE_URL', 'LOCAL_LLM_BASE_URL'], 'http://localhost:11434'
        ),
        embedding_model=_env_alias(
            ['EMBEDDING_MODEL', 'LOCAL_EMBEDDING_MODEL'], 'mxbai-embed-large:latest'
        ),
        use_reranker=_env('USE_RERANKER', 'false').strip().lower() == 'true',
        reranker_provider=_env('RERANKER_PROVIDER', 'noop'),
        reranker_base_url=_env_alias(
            ['RERANKER_BASE_URL', 'LLM_BASE_URL', 'LOCAL_LLM_BASE_URL'], 'http://localhost:11434'
        ),
        reranker_model=_env('RERANKER_MODEL', 'deepseek-r1:8b'),
        reranker_pool_size=int(_env('RERANKER_POOL_SIZE', '24')),
        use_vision_ingestion=_env('USE_VISION_INGESTION', 'false').strip().lower() == 'true',
        vision_provider=_env('VISION_PROVIDER', 'noop'),
        vision_base_url=_env_alias(
            ['VISION_BASE_URL', 'LLM_BASE_URL', 'LOCAL_LLM_BASE_URL'], 'http://localhost:11434'
        ),
        vision_model=_env('VISION_MODEL', 'qwen2.5vl:7b'),
        vision_max_pages=int(_env('VISION_MAX_PAGES', '40')),
    )
