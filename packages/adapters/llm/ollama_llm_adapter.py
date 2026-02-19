from __future__ import annotations

import json
import urllib.error
import urllib.request

from packages.ports.llm_port import LlmEvidence, LlmPort


class OllamaLlmAdapter(LlmPort):
    def __init__(self, *, base_url: str, model: str, timeout_seconds: int = 60) -> None:
        self._base_url = base_url.rstrip('/')
        self._model = model
        self._timeout_seconds = timeout_seconds

    def _prompt(self, query: str, intent: str, evidence: list[LlmEvidence]) -> str:
        lines: list[str] = [
            'You are a grounded industrial manuals assistant.',
            'Goal: provide a definitive, useful answer based only on evidence.',
            'Rules:',
            '- Use only the provided evidence snippets.',
            '- Do not invent facts, procedures, limits, or parameter values.',
            '- Prefer a direct answer first, then key details.',
            '- If evidence is partial, state what is known first, then clearly list unknowns.',
            '- Keep tone confident and practical, not hesitant.',
            f'Intent: {intent}',
            f'Question: {query}',
            '',
            'Evidence:',
        ]

        for idx, hit in enumerate(evidence[:8], start=1):
            lines.append(
                f'[{idx}] doc={hit.doc_id} page={hit.page_start}-{hit.page_end} '
                f'type={hit.content_type}: {hit.text}'
            )

        lines.append('')
        lines.append('Return plain text only in this structure:')
        lines.append('Direct answer: <1-2 sentences>')
        lines.append('Key details:')
        lines.append('- <detail>')
        lines.append('- <detail>')
        lines.append('If missing data:')
        lines.append('- <what is not explicitly present in evidence>')
        return '\n'.join(lines)

    def generate_answer(
        self,
        *,
        query: str,
        intent: str,
        evidence: list[LlmEvidence],
    ) -> str:
        if not query.strip() or not evidence:
            return ''

        payload = {
            'model': self._model,
            'stream': False,
            'messages': [
                {
                    'role': 'system',
                    'content': (
                        'Grounded answering only from provided evidence. '
                        'Be definitive and practical. Never hallucinate.'
                    ),
                },
                {'role': 'user', 'content': self._prompt(query, intent, evidence)},
            ],
        }
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            f'{self._base_url}/api/chat',
            data=data,
            method='POST',
            headers={'Content-Type': 'application/json'},
        )

        try:
            with urllib.request.urlopen(req, timeout=self._timeout_seconds) as response:
                body = json.loads(response.read().decode('utf-8'))
            message = body.get('message', {})
            text = message.get('content', '') if isinstance(message, dict) else ''
            return str(text).strip()
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return ''
