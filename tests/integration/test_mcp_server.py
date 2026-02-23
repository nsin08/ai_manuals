"""Integration tests — MCP server.

Tests that the MCP server module can be loaded cleanly and that the
stdio transport wiring is correctly assembled.

Run:  pytest tests/integration/test_mcp_server.py
"""
from __future__ import annotations

from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Startup / import
# ---------------------------------------------------------------------------

def test_module_imports_cleanly():
    """apps.mcp.server imports without raising any exception."""
    import importlib

    # Re-import to force evaluation (handles cached import across test runs)
    import apps.mcp.server  # noqa: F401


def test_server_instance_name():
    """The FastMCP instance is named 'ai-manuals'."""
    from apps.mcp.server import mcp as mcp_server

    assert mcp_server.name == 'ai-manuals'


# ---------------------------------------------------------------------------
# stdio transport
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stdio_startup():
    """_run_stdio() delegates to mcp.run_stdio_async()."""
    run_called = False

    async def _fake_run_stdio():
        nonlocal run_called
        run_called = True

    from apps.mcp import server as mcp_module

    with patch.object(mcp_module.mcp, 'run_stdio_async', side_effect=_fake_run_stdio):
        await mcp_module._run_stdio()

    assert run_called


@pytest.mark.asyncio
async def test_main_uses_stdio_by_default(monkeypatch):
    """main() delegates to _run_stdio when MCP_TRANSPORT is unset."""
    monkeypatch.delenv('MCP_TRANSPORT', raising=False)

    run_called = False

    async def _fake_stdio():
        nonlocal run_called
        run_called = True

    with patch('apps.mcp.server._run_stdio', side_effect=_fake_stdio):
        from apps.mcp.server import main

        await main()

    assert run_called


@pytest.mark.asyncio
async def test_main_uses_sse_when_transport_env_set(monkeypatch):
    """main() delegates to _run_sse when MCP_TRANSPORT=sse."""
    monkeypatch.setenv('MCP_TRANSPORT', 'sse')

    run_called = False

    async def _fake_sse():
        nonlocal run_called
        run_called = True

    with patch('apps.mcp.server._run_sse', side_effect=_fake_sse):
        from apps.mcp.server import main

        await main()

    assert run_called
