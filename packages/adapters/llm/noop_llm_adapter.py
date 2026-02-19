from __future__ import annotations

from packages.ports.llm_port import LlmEvidence, LlmPort


class NoopLlmAdapter(LlmPort):
    def generate_answer(
        self,
        *,
        query: str,
        intent: str,
        evidence: list[LlmEvidence],
    ) -> str:
        _ = query, intent, evidence
        return ''
