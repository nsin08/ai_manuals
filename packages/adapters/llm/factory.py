from __future__ import annotations

from packages.adapters.llm.noop_llm_adapter import NoopLlmAdapter
from packages.adapters.llm.ollama_llm_adapter import OllamaLlmAdapter
from packages.ports.llm_port import LlmPort


def create_llm_adapter(
    *,
    provider: str,
    base_url: str,
    model: str,
) -> LlmPort:
    normalized = provider.strip().lower()
    if normalized == 'local' and model.strip():
        return OllamaLlmAdapter(base_url=base_url, model=model)
    return NoopLlmAdapter()
