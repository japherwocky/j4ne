"""
Shared test setup.

Tests that call real services are marked `live` and skipped unless
J4NE_LIVE_TESTS=1, so a plain `pytest tests/` spends no API calls:

    J4NE_LIVE_TESTS=1 pytest tests/ -m live -v
"""

import os
import sys
from pathlib import Path

import pytest

# Make the repo importable however pytest is started
sys.path.insert(0, str(Path(__file__).parent.parent))

LIVE = os.getenv("J4NE_LIVE_TESTS") == "1"


def pytest_configure(config):
    config.addinivalue_line("markers", "live: calls a real external service; needs J4NE_LIVE_TESTS=1")


def pytest_collection_modifyitems(config, items):
    if LIVE:
        return
    skip_live = pytest.mark.skip(reason="calls a real service; set J4NE_LIVE_TESTS=1 to run")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


@pytest.fixture(autouse=True)
def no_mcp_network(monkeypatch):
    """The MCP tests reach mcp.exa.ai through get_registry(); keep them offline"""
    if LIVE:
        return
    try:
        import tools.mcp_registry as mcp_registry
    except ImportError:
        return

    def offline(self, server_name, server_config):
        raise ConnectionError("network disabled in tests (set J4NE_LIVE_TESTS=1)")

    monkeypatch.setattr(mcp_registry.MCPToolRegistry, "_connect_server", offline)
    monkeypatch.setattr(mcp_registry, "_global_registry", None)
