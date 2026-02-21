from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from packages.ports.tool_executor_port import ToolExecutionResult, ToolExecutorPort

ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class LangChainToolDefinition:
    name: str
    description: str
    handler: ToolHandler
    required_args: tuple[str, ...] = field(default_factory=tuple)


class LangChainToolExecutorAdapter(ToolExecutorPort):
    def __init__(self, tools: list[LangChainToolDefinition]) -> None:
        self._tool_defs = {row.name: row for row in tools}
        self._structured_tools = self._build_structured_tools(tools)

    @staticmethod
    def _build_structured_tools(tools: list[LangChainToolDefinition]) -> dict[str, Any]:
        try:
            from langchain_core.tools import StructuredTool  # type: ignore
        except Exception:
            return {}

        built: dict[str, Any] = {}
        for row in tools:
            try:
                structured = StructuredTool.from_function(
                    name=row.name,
                    description=row.description,
                    func=lambda _row=row, **kwargs: _row.handler(dict(kwargs)),
                )
                built[row.name] = structured
            except Exception:
                continue
        return built

    def available_tools(self) -> list[str]:
        return sorted(self._tool_defs.keys())

    def execute(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolExecutionResult:
        tool_def = self._tool_defs.get(tool_name)
        if tool_def is None:
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=f'Unknown tool: {tool_name}',
            )

        normalized_args: dict[str, Any] = dict(arguments or {})
        # Some tool runtimes pass single-input under `input`; map it for required `query`.
        if 'query' not in normalized_args and normalized_args.get('input') is not None:
            normalized_args['query'] = normalized_args.get('input')

        missing = [name for name in tool_def.required_args if name not in normalized_args]
        if missing:
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=(
                    f'Missing required args: {", ".join(missing)}; '
                    f'provided keys: {sorted(normalized_args.keys())}'
                ),
            )

        try:
            # Execute the validated handler directly to avoid adapter-specific arg shape drift.
            payload: Any = tool_def.handler(normalized_args)

            if not isinstance(payload, dict):
                payload = {'result': payload}
            return ToolExecutionResult(
                tool_name=tool_name,
                success=True,
                payload=dict(payload),
            )
        except Exception as exc:
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=(
                    f'{type(exc).__name__}: {exc}; '
                    f'tool={tool_name}; arg_keys={sorted(normalized_args.keys())}'
                ),
            )
