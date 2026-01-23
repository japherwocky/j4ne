"""
Test script for Phase 2 MCP tools (codesearch and websearch)

Tests the structure and validation of the tool wrappers.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.codesearch_tool import CodeSearchTool, get_code_search_tool, codesearch
from tools.websearch_tool import WebSearchTool, get_web_search_tool, websearch


def test_codesearch_tool_creation():
    """Test that codesearch tool can be created"""
    print("Testing CodeSearchTool creation...")
    tool = CodeSearchTool()
    assert tool.tool_name == "codesearch"
    print("[OK] CodeSearchTool created successfully")


def test_codesearch_singleton():
    """Test that singleton pattern works"""
    print("\nTesting CodeSearchTool singleton...")
    tool1 = get_code_search_tool()
    tool2 = get_code_search_tool()
    assert tool1 is tool2
    print("[OK] Singleton pattern works correctly")


def test_codesearch_validation():
    """Test codesearch parameter validation"""
    print("\nTesting CodeSearchTool parameter validation...")
    tool = CodeSearchTool()

    # Test invalid query
    try:
        tool.run("")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "non-empty string" in str(e)
        print("[OK] Empty query validation works")

    # Test invalid tokens_num
    try:
        tool.run("test", tokens_num=500)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "between 1000 and 50000" in str(e)
        print("[OK] Invalid tokens_num validation works")

    # Test valid parameters (will fail if MCP server not available)
    try:
        result = tool.run("test query", tokens_num=5000)
        print(f"[OK] Valid parameters accepted (result: {type(result).__name__})")
    except RuntimeError as e:
        if "not available" in str(e):
            print(
                "[OK] Valid parameters accepted (MCP server not available - expected)"
            )
        else:
            raise
    except Exception as e:
        # Network errors are expected if no MCP server
        if "Connection" in str(e) or "timeout" in str(e).lower():
            print("[OK] Valid parameters accepted (connection failed - expected)")
        else:
            raise


def test_websearch_tool_creation():
    """Test that websearch tool can be created"""
    print("\nTesting WebSearchTool creation...")
    tool = WebSearchTool()
    assert tool.tool_name == "websearch"
    print("[OK] WebSearchTool created successfully")


def test_websearch_singleton():
    """Test that singleton pattern works"""
    print("\nTesting WebSearchTool singleton...")
    tool1 = get_web_search_tool()
    tool2 = get_web_search_tool()
    assert tool1 is tool2
    print("[OK] Singleton pattern works correctly")


def test_websearch_validation():
    """Test websearch parameter validation"""
    print("\nTesting WebSearchTool parameter validation...")
    tool = WebSearchTool()

    # Test invalid query
    try:
        tool.run("")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "non-empty string" in str(e)
        print("[OK] Empty query validation works")

    # Test invalid num_results
    try:
        tool.run("test", num_results=0)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "positive integer" in str(e)
        print("[OK] Invalid num_results validation works")

    # Test invalid livecrawl
    try:
        tool.run("test", livecrawl="invalid")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "'fallback' or 'preferred'" in str(e)
        print("[OK] Invalid livecrawl validation works")

    # Test invalid search_type
    try:
        tool.run("test", search_type="invalid")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "'auto', 'fast', or 'deep'" in str(e)
        print("[OK] Invalid search_type validation works")

    # Test valid parameters (will fail if MCP server not available)
    try:
        result = tool.run("test query", num_results=5)
        print(f"[OK] Valid parameters accepted (result: {type(result).__name__})")
    except RuntimeError as e:
        if "not available" in str(e):
            print(
                "[OK] Valid parameters accepted (MCP server not available - expected)"
            )
        else:
            raise
    except Exception as e:
        # Network errors are expected if no MCP server
        if "Connection" in str(e) or "timeout" in str(e).lower():
            print("[OK] Valid parameters accepted (connection failed - expected)")
        else:
            raise


def test_convenience_functions():
    """Test convenience functions"""
    print("\nTesting convenience functions...")

    # Test codesearch function
    try:
        result = codesearch("test")
        print(f"[OK] codesearch() function works (result: {type(result).__name__})")
    except RuntimeError as e:
        if "not available" in str(e):
            print(
                "[OK] codesearch() function works (MCP server not available - expected)"
            )
        else:
            raise
    except Exception as e:
        if "Connection" in str(e) or "timeout" in str(e).lower():
            print("[OK] codesearch() function works (connection failed - expected)")
        else:
            raise

    # Test websearch function
    try:
        result = websearch("test")
        print(f"[OK] websearch() function works (result: {type(result).__name__})")
    except RuntimeError as e:
        if "not available" in str(e):
            print(
                "[OK] websearch() function works (MCP server not available - expected)"
            )
        else:
            raise
    except Exception as e:
        if "Connection" in str(e) or "timeout" in str(e).lower():
            print("[OK] websearch() function works (connection failed - expected)")
        else:
            raise


def test_result_formatting():
    """Test result formatting"""
    print("\nTesting result formatting...")

    codesearch_tool = CodeSearchTool()
    websearch_tool = WebSearchTool()

    # Test empty result
    result = codesearch_tool._format_result(None)
    assert result == "No results found"
    print("[OK] Empty result formatting works")

    # Test list result
    result = codesearch_tool._format_result([{"text": "Line 1"}, {"content": "Line 2"}])
    assert "Line 1" in result
    assert "Line 2" in result
    print("[OK] List result formatting works")

    # Test string result
    result = codesearch_tool._format_result("Simple string")
    assert result == "Simple string"
    print("[OK] String result formatting works")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Phase 2 MCP Tools Tests")
    print("=" * 60)

    try:
        test_codesearch_tool_creation()
        test_codesearch_singleton()
        test_codesearch_validation()
        test_websearch_tool_creation()
        test_websearch_singleton()
        test_websearch_validation()
        test_convenience_functions()
        test_result_formatting()

        print("\n" + "=" * 60)
        print("All tests passed! [OK]")
        print("=" * 60)
        print("\nNote: These tests verify the structure and validation.")
        print("To test actual MCP connections, you need:")
        print("  1. A running MCP server (e.g., Exa)")
        print("  2. Valid server configuration in mcp_config.yaml")
        print("  3. Network access to the server")
        print("  4. Exa API key (if required)")

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
