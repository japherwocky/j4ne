"""
MCP Call Tool - Generic tool caller

Allows calling arbitrary MCP tools without pre-wrapping them.
Validates parameters against tool schemas.
"""

from tools.mcp_registry import get_registry


class MCPCallTool:
    """Generic tool caller for any MCP tool"""

    def __init__(self):
        """Initialize MCP call tool"""
        self.registry = None

    def _get_registry(self):
        """Get or create registry (lazy initialization)"""
        if self.registry is None:
            self.registry = get_registry()
        return self.registry

    def list_available_tools(self):
        """
        List all available MCP tools

        Returns:
            Dict of tool_name -> tool_schema
        """
        registry = self._get_registry()
        return registry.list_tools()

    def get_tool_schema(self, tool_name):
        """
        Get schema for a specific tool

        Args:
            tool_name: Name or alias of the tool

        Returns:
            Tool schema or None if not found
        """
        registry = self._get_registry()
        return registry.get_tool_schema(tool_name)

    def run(self, tool_name, arguments, validate=True):
        """
        Call an MCP tool

        Args:
            tool_name: Name or alias of the tool
            arguments: Tool arguments dict
            validate: Whether to validate against schema (default: True)

        Returns:
            Tool execution result
        """
        if not tool_name or not isinstance(tool_name, str):
            raise ValueError("tool_name must be a non-empty string")

        if not isinstance(arguments, dict):
            raise ValueError("arguments must be a dict")

        registry = self._get_registry()

        # Get tool schema for validation
        schema = None
        if validate:
            schema = registry.get_tool_schema(tool_name)
            if schema:
                self._validate_arguments(tool_name, arguments, schema)

        # Call the tool
        try:
            result = registry.call_tool(tool_name, arguments)
            return self._format_result(result)
        except ValueError as e:
            if f"Tool '{tool_name}' not found" in str(e):
                available = registry.list_tools()
                raise ValueError(
                    f"Tool '{tool_name}' not found. "
                    f"Available tools: {list(available.keys())}"
                ) from e
            raise

    def _validate_arguments(self, tool_name, arguments, schema):
        """
        Validate arguments against tool schema

        Args:
            tool_name: Name of the tool
            arguments: Arguments to validate
            schema: Tool schema

        Raises:
            ValueError: If validation fails
        """
        input_schema = schema.get("inputSchema")

        if not input_schema:
            # No schema to validate against
            return

        schema_type = input_schema.get("type")

        if schema_type != "object":
            raise ValueError(
                f"Tool '{tool_name}' expects input type '{schema_type}', got object"
            )

        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        # Check for required parameters
        for param in required:
            if param not in arguments:
                raise ValueError(
                    f"Tool '{tool_name}' missing required parameter: {param}"
                )

        # Check for unknown parameters
        for param in arguments:
            if param not in properties:
                # Warn but don't fail
                print(
                    f"Warning: Tool '{tool_name}' does not recognize parameter: {param}"
                )

    def _format_result(self, result):
        """
        Format the raw MCP result for better usability

        Args:
            result: Raw result from MCP tool

        Returns:
            Formatted result
        """
        if not result:
            return "No result"

        # Handle different result formats
        if isinstance(result, list):
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
_mcp_call_tool = None


def get_mcp_call_tool():
    """Get or create MCP call tool instance"""
    global _mcp_call_tool
    if _mcp_call_tool is None:
        _mcp_call_tool = MCPCallTool()
    return _mcp_call_tool


# Convenience function
def mcp_call(tool_name, arguments, validate=True):
    """
    Call an MCP tool

    Args:
        tool_name: Name or alias of the tool
        arguments: Tool arguments dict
        validate: Whether to validate against schema (default: True)

    Returns:
        Tool execution result

    Example:
        >>> # List available tools
        >>> tools = mcp_list_tools()
        >>> print(tools)

        >>> # Call a tool
        >>> result = mcp_call("codesearch", {"query": "fastapi", "tokensNum": 5000})
        >>> print(result)
    """
    tool = get_mcp_call_tool()
    return tool.run(tool_name, arguments, validate)


# Convenience function for listing tools
def mcp_list_tools():
    """
    List all available MCP tools

    Returns:
        Dict of tool_name -> tool_schema

    Example:
        >>> tools = mcp_list_tools()
        >>> for name, schema in tools.items():
        ...     print(f"{name}: {schema.get('description', 'No description')}")
    """
    tool = get_mcp_call_tool()
    return tool.list_available_tools()


# Convenience function for getting tool schema
def mcp_get_schema(tool_name):
    """
    Get schema for a specific MCP tool

    Args:
        tool_name: Name or alias of the tool

    Returns:
        Tool schema or None if not found

    Example:
        >>> schema = mcp_get_schema("codesearch")
        >>> print(schema.get("description"))
        >>> print(schema.get("inputSchema"))
    """
    tool = get_mcp_call_tool()
    return tool.get_tool_schema(tool_name)


if __name__ == "__main__":
    # Simple test
    import sys
    import json

    # Show available tools
    print("=" * 60)
    print("Available MCP Tools")
    print("=" * 60)

    tools = mcp_list_tools()

    if not tools:
        print("No tools available. Make sure MCP servers are configured.")
        sys.exit(0)

    for name, schema in tools.items():
        desc = schema.get("description", "No description")
        print(f"\n{name}:")
        print(f"  Description: {desc}")

        # Show input schema
        input_schema = schema.get("inputSchema")
        if input_schema:
            properties = input_schema.get("properties", {})
            if properties:
                print(f"  Parameters:")
                for param_name, param_schema in properties.items():
                    param_type = param_schema.get("type", "unknown")
                    param_desc = param_schema.get("description", "")
                    print(f"    - {param_name} ({param_type}): {param_desc}")

    print("\n" + "=" * 60)
    print("To call a tool:")
    print("  python -m tools.mcp_call_tool <tool_name> <arguments_json>")
    print("Example:")
    print('  python -m tools.mcp_call_tool codesearch \'{"query": "fastapi"}\'')
    print("=" * 60)
