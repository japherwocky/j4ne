"""
Web Search Tool - Exa MCP wrapper

Provides web search functionality using Exa's MCP server.
"""

from tools.mcp_registry import get_registry


class WebSearchTool:
    """Tool for searching the web via Exa"""

    def __init__(self):
        """Initialize web search tool"""
        self.tool_name = "websearch"

    def run(
        self,
        query,
        num_results=8,
        livecrawl="fallback",
        search_type="auto",
        context_max_characters=10000,
    ):
        """
        Search the web and scrape content from URLs

        Args:
            query: Web search query
            num_results: Number of results to return (default: 8)
            livecrawl: Live crawl mode - 'fallback' or 'preferred'
            search_type: Search type - 'auto', 'fast', or 'deep'
            context_max_characters: Max characters for context (default: 10000)

        Returns:
            Search results with scraped web content
        """
        # Validate parameters
        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")

        if not isinstance(num_results, int) or num_results < 1:
            raise ValueError("num_results must be a positive integer")

        if livecrawl not in ["fallback", "preferred"]:
            raise ValueError("livecrawl must be 'fallback' or 'preferred'")

        if search_type not in ["auto", "fast", "deep"]:
            raise ValueError("search_type must be 'auto', 'fast', or 'deep'")

        if not isinstance(context_max_characters, int) or context_max_characters < 1:
            raise ValueError("context_max_characters must be a positive integer")

        # Get registry and call tool
        registry = get_registry()

        # Build arguments for MCP tool
        arguments = {
            "query": query,
            "numResults": num_results,
            "livecrawl": livecrawl,
            "type": search_type,
            "contextMaxCharacters": context_max_characters,
        }

        try:
            result = registry.call_tool(self.tool_name, arguments)
            return self._format_result(result)
        except ValueError as e:
            if f"Tool '{self.tool_name}' not found" in str(e):
                raise RuntimeError(
                    f"Web search tool not available. "
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
_web_search_tool = None


def get_web_search_tool():
    """Get or create web search tool instance"""
    global _web_search_tool
    if _web_search_tool is None:
        _web_search_tool = WebSearchTool()
    return _web_search_tool


# Convenience function
def websearch(
    query,
    num_results=8,
    livecrawl="fallback",
    search_type="auto",
    context_max_characters=10000,
):
    """
    Search the web and scrape content from URLs

    Args:
        query: Web search query
        num_results: Number of results to return (default: 8)
        livecrawl: Live crawl mode - 'fallback' or 'preferred'
        search_type: Search type - 'auto', 'fast', or 'deep'
        context_max_characters: Max characters for context (default: 10000)

    Returns:
        Search results with scraped web content

    Example:
        >>> result = websearch("AI news 2025", num_results=5)
        >>> print(result)
    """
    tool = get_web_search_tool()
    return tool.run(query, num_results, livecrawl, search_type, context_max_characters)


if __name__ == "__main__":
    # Simple test
    import sys

    if len(sys.argv) < 2:
        print("Usage: python websearch_tool.py <query> [num_results]")
        print("Example: python websearch_tool.py 'AI news 2025' 5")
        sys.exit(1)

    query = sys.argv[1]
    num_results = int(sys.argv[2]) if len(sys.argv) > 2 else 8

    try:
        result = websearch(query, num_results)
        print(result)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
