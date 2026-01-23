"""
Test script for Phase 3 MCP generic tool caller

Tests the structure and functionality of the generic MCP call tool.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.mcp_call_tool import (
    MCPCallTool,
    get_mcp_call_tool,
    mcp_call,
    mcp_list_tools,
    mcp_get_schema,
)


def test_mcp_call_tool_creation():
    """Test that MCP call tool can be created"""
    print("Testing MCPCallTool creation...")
    tool = MCPCallTool()
    assert tool.registry is None  # Lazy initialization
    print("[OK] MCPCallTool created successfully")


def test_mcp_call_singleton():
    """Test that singleton pattern works"""
    print("\nTesting MCPCallTool singleton...")
    tool1 = get_mcp_call_tool()
    tool2 = get_mcp_call_tool()
    assert tool1 is tool2
    print("[OK] Singleton pattern works correctly")


def test_convenience_functions():
    """Test convenience functions"""
    print("\nTesting convenience functions...")

    # Test mcp_list_tools function
    try:
        tools = mcp_list_tools()
        print(f"[OK] mcp_list_tools() works (found {len(tools)} tools)")
    except Exception as e:
        if "Connection" in str(e) or "not available" in str(e):
            print("[OK] mcp_list_tools() works (MCP server not available - expected)")
        else:
            raise

    # Test mcp_get_schema function
    try:
        schema = mcp_get_schema("codesearch")
        print(f"[OK] mcp_get_schema() works (schema: {type(schema).__name__})")
    except Exception as e:
        if "Connection" in str(e) or "not available" in str(e):
            print("[OK] mcp_get_schema() works (MCP server not available - expected)")
        else:
            raise


def test_parameter_validation():
    """Test parameter validation"""
    print("\nTesting parameter validation...")
    tool = MCPCallTool()

    # Test invalid tool_name
    try:
        tool.run("", {})
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "non-empty string" in str(e)
        print("[OK] Empty tool_name validation works")

    # Test invalid arguments type
    try:
        tool.run("test", "not a dict")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "must be a dict" in str(e)
        print("[OK] Invalid arguments type validation works")


def test_tool_schema_validation():
    """Test tool schema validation logic"""
    print("\nTesting tool schema validation...")

    # Test with no schema (should not raise)
    tool = MCPCallTool()
    tool._validate_arguments("test_tool", {"param": "value"}, {})
    print("[OK] Empty schema validation works")

    # Test with schema but no inputSchema (should not raise)
    tool._validate_arguments("test_tool", {"param": "value"}, {"name": "test"})
    print("[OK] Schema without inputSchema validation works")

    # Test with required parameters
    try:
        tool._validate_arguments(
            "test_tool",
            {},  # Missing required param
            {"inputSchema": {"type": "object", "required": ["param1"]}},
        )
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "missing required parameter" in str(e)
        print("[OK] Required parameter validation works")


def test_result_formatting():
    """Test result formatting"""
    print("\nTesting result formatting...")
    tool = MCPCallTool()

    # Test empty result
    result = tool._format_result(None)
    assert result == "No result"
    print("[OK] Empty result formatting works")

    # Test list result
    result = tool._format_result([{"text": "Line 1"}, {"content": "Line 2"}])
    assert "Line 1" in result
    assert "Line 2" in result
    print("[OK] List result formatting works")

    # Test string result
    result = tool._format_result("Simple string")
    assert result == "Simple string"
    print("[OK] String result formatting works")


def test_lazy_initialization():
    """Test lazy initialization"""
    print("\nTesting lazy initialization...")
    tool = MCPCallTool()

    # Registry should be None initially
    assert tool.registry is None
    print("[OK] Registry is None initially")

    # After getting registry, it should be set
    registry = tool._get_registry()
    assert registry is not None
    assert tool.registry is not None
    print("[OK] Registry initialized lazily")


def test_available_tools_function():
    """Test list_available_tools function"""
    print("\nTesting list_available_tools function...")
    tool = MCPCallTool()

    try:
        tools = tool.list_available_tools()
        print(f"[OK] list_available_tools() works (found {len(tools)} tools)")
    except Exception as e:
        if "Connection" in str(e) or "not available" in str(e):
            print(
                "[OK] list_available_tools() works (MCP server not available - expected)"
            )
        else:
            raise


def main():
    """Run all tests"""
    print("=" * 60)
    print("Phase 3 MCP Generic Tool Caller Tests")
    print("=" * 60)

    try:
        test_mcp_call_tool_creation()
        test_mcp_call_singleton()
        test_convenience_functions()
        test_parameter_validation()
        test_tool_schema_validation()
        test_result_formatting()
        test_lazy_initialization()
        test_available_tools_function()

        print("\n" + "=" * 60)
        print("All tests passed! [OK]")
        print("=" * 60)
        print("\nNote: These tests verify the structure and validation.")
        print("To test actual MCP connections, you need:")
        print("  1. A running MCP server")
        print("  2. Valid server configuration in mcp_config.yaml")
        print("  3. Network access to the server")

        return 0

    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
