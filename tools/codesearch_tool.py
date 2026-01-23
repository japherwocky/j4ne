"""
Code Search Tool - Exa MCP wrapper

Provides code search functionality using Exa's MCP server.
"""

from tools.mcp_registry import get_registry


class CodeSearchTool:
    """Tool for searching code examples and documentation via Exa"""

    def __init__(self):
        """Initialize code search tool"""
        self.tool_name = "codesearch"

    def run(self, query, tokens_num=5000):
        """
        Search for code examples and documentation

        Args:
            query: Search query for code
            tokens_num: Number of tokens to return (1000-50000)

        Returns:
            Search results with code examples and documentation
        """
        # Validate parameters
        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")

        if not isinstance(tokens_num, int):
            raise ValueError("tokens_num must be an integer")

        if tokens_num < 1000 or tokens_num > 50000:
            raise ValueError("tokens_num must be between 1000 and 50000")

        # Get registry and call tool
        registry = get_registry()

        # Build arguments for MCP tool
        arguments = {"query": query, "tokensNum": tokens_num}

        try:
            result = registry.call_tool(self.tool_name, arguments)
            return self._format_result(result)
        except ValueError as e:
            if f"Tool '{self.tool_name}' not found" in str(e):
                raise RuntimeError(
                    f"Code search tool not available. "
                    f"Make sure Exa MCP server is configured in mcp_config.yaml and is accessible."
                ) from e
            raise

    def _format_result(self, result):
        """
        Format the raw MCP result for better usability

        Args:
            result: Raw result from MCP tool

        Returns:
            Formatted result string
        """
        if not result:
            return "No results found"

        # Handle different result formats
        if isinstance(result, list):
            # MCP returns content array
            formatted_lines = []

            for item in result:
                if isinstance(item, dict):
                    # Extract text content
                    if "text" in item:
                        formatted_lines.append(item["text"])
                    elif "content" in item:
                        formatted_lines.append(item["content"])

            return "\n".join(formatted_lines) if formatted_lines else str(result)

        return str(result)


# Create singleton instance
_code_search_tool = None


def get_code_search_tool():
    """Get or create code search tool instance"""
    global _code_search_tool
    if _code_search_tool is None:
        _code_search_tool = CodeSearchTool()
    return _code_search_tool


# Convenience function
def codesearch(query, tokens_num=5000):
    """
    Search for code examples and documentation

    Args:
        query: Search query for code
        tokens_num: Number of tokens to return (1000-50000)

    Returns:
        Search results with code examples and documentation

    Example:
        >>> result = codesearch("fastapi authentication")
        >>> print(result)
    """
    tool = get_code_search_tool()
    return tool.run(query, tokens_num)


if __name__ == "__main__":
    # Simple test
    import sys

    if len(sys.argv) < 2:
        print("Usage: python codesearch_tool.py <query> [tokens_num]")
        print("Example: python codesearch_tool.py 'fastapi authentication' 5000")
        sys.exit(1)

    query = sys.argv[1]
    tokens_num = int(sys.argv[2]) if len(sys.argv) > 2 else 5000

    try:
        result = codesearch(query, tokens_num)
        print(result)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
