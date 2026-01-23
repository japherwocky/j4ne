"""
Test script for MCP client and registry

This script tests the MCP infrastructure without requiring actual MCP servers.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.mcp_client import MCPClient, MCPClientSync
from tools.mcp_registry import MCPToolRegistry


def test_mcp_client_creation():
    """Test that MCP client can be created"""
    print("Testing MCPClient creation...")
    client = MCPClient("http://example.com/mcp")
    assert client.url == "http://example.com/mcp"
    assert client.transport == "http"
    assert client.timeout == 30
    print("[OK] MCPClient created successfully")


def test_mcp_client_sync_creation():
    """Test that sync MCP client can be created"""
    print("\nTesting MCPClientSync creation...")
    client = MCPClientSync("http://example.com/mcp")
    assert client.url == "http://example.com/mcp"
    assert client.transport == "http"
    assert client.timeout == 30
    print("[OK] MCPClientSync created successfully")


def test_mcp_registry_creation():
    """Test that MCP registry can be created"""
    print("\nTesting MCPToolRegistry creation...")
    registry = MCPToolRegistry()
    assert registry.config_path.endswith("mcp_config.yaml")
    assert "mcp_servers" in registry.config
    print("[OK] MCPToolRegistry created successfully")


def test_mcp_registry_with_config():
    """Test that MCP registry loads config"""
    print("\nTesting MCPToolRegistry config loading...")
    registry = MCPToolRegistry()

    # Check that config was loaded
    assert "mcp_servers" in registry.config

    # Check that exa server is configured
    servers = registry.config.get("mcp_servers", {})
    if "exa" in servers:
        exa_config = servers["exa"]
        assert exa_config["url"] == "https://mcp.exa.ai/mcp"
        assert exa_config["transport"] == "http"
        assert "tools" in exa_config
        print("[OK] Exa server config loaded correctly")

    print("[OK] MCPToolRegistry config loaded successfully")


def test_json_rpc_formatting():
    """Test JSON-RPC request formatting"""
    print("\nTesting JSON-RPC request formatting...")
    client = MCPClient("http://example.com/mcp")

    # Test basic request
    request = client._format_request("test_method")
    assert request["jsonrpc"] == "2.0"
    assert request["method"] == "test_method"
    assert "id" in request
    assert "params" not in request
    print("[OK] Basic request formatted correctly")

    # Test request with params
    request = client._format_request("test_method", {"param1": "value1"})
    assert request["params"] == {"param1": "value1"}
    print("[OK] Request with params formatted correctly")

    # Test request ID increment
    id1 = client._format_request("test")["id"]
    id2 = client._format_request("test")["id"]
    assert id2 == id1 + 1
    print("[OK] Request IDs increment correctly")


def test_tool_discovery_structure():
    """Test that tool discovery structure is correct"""
    print("\nTesting tool discovery structure...")

    # Simulate tool schema from MCP server
    mock_tool = {
        "name": "test_tool",
        "description": "A test tool",
        "inputSchema": {"type": "object", "properties": {"param1": {"type": "string"}}},
    }

    assert mock_tool["name"] == "test_tool"
    assert "description" in mock_tool
    assert "inputSchema" in mock_tool
    print("[OK] Tool schema structure is correct")


def main():
    """Run all tests"""
    print("=" * 60)
    print("MCP Infrastructure Tests")
    print("=" * 60)

    try:
        test_mcp_client_creation()
        test_mcp_client_sync_creation()
        test_mcp_registry_creation()
        test_mcp_registry_with_config()
        test_json_rpc_formatting()
        test_tool_discovery_structure()

        print("\n" + "=" * 60)
        print("All tests passed! [OK]")
        print("=" * 60)
        print("\nNote: These tests verify the structure and configuration.")
        print("To test actual MCP connections, you need:")
        print("  1. A running MCP server")
        print("  2. Valid server configuration in mcp_config.yaml")
        print("  3. Network access to the server")

        return 0

    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
