from __future__ import annotations

import os
from dataclasses import dataclass


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
    retrieval_trace_file: str
    answer_trace_file: str
    use_llm_answering: bool
    local_llm_base_url: str
    local_llm_model: str
    embedding_provider: str
    local_embedding_model: str



def load_config() -> AppConfig:
    return AppConfig(
        app_env=os.getenv('APP_ENV', 'local'),
        database_url=os.getenv(
            'DATABASE_URL', 'postgresql://ai_manuals:ai_manuals@localhost:5432/ai_manuals'
        ),
        redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        llm_provider=os.getenv('LLM_PROVIDER', 'local'),
        asset_store=os.getenv('ASSET_STORE', 'filesystem'),
        ocr_engine=os.getenv('OCR_ENGINE', 'paddle'),
        ocr_fallback_engine=os.getenv('OCR_FALLBACK_ENGINE', 'tesseract'),
        ingest_concurrency=int(os.getenv('INGEST_CONCURRENCY', '2')),
        retrieval_trace_file=os.getenv(
            'RETRIEVAL_TRACE_FILE', '.context/reports/retrieval_traces.jsonl'
        ),
        answer_trace_file=os.getenv(
            'ANSWER_TRACE_FILE', '.context/reports/answer_traces.jsonl'
        ),
        use_llm_answering=os.getenv('USE_LLM_ANSWERING', 'false').strip().lower() == 'true',
        local_llm_base_url=os.getenv('LOCAL_LLM_BASE_URL', 'http://localhost:11434'),
        local_llm_model=os.getenv('LOCAL_LLM_MODEL', 'deepseek-r1:8b'),
        embedding_provider=os.getenv('EMBEDDING_PROVIDER', 'hash'),
        local_embedding_model=os.getenv('LOCAL_EMBEDDING_MODEL', 'mxbai-embed-large:latest'),
    )
