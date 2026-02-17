from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AnswerTraceLogger:
    def __init__(self, trace_file: Path) -> None:
        self._trace_file = trace_file

    def log(self, payload: dict[str, Any]) -> None:
        self._trace_file.parent.mkdir(parents=True, exist_ok=True)
        with self._trace_file.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(payload, ensure_ascii=True))
            fh.write('\n')
