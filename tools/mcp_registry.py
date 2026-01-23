"""
MCP Tool Registry - Manages MCP servers and tool discovery

Loads configuration, connects to servers, discovers tools,
and provides a unified interface for tool invocation.
"""

import yaml
import os
from typing import Dict, List, Any, Optional
from tools.mcp_client import MCPClientSync


class MCPToolRegistry:
    """Registry for MCP servers and their tools"""

    def __init__(self, config_path=None):
        """
        Initialize MCP tool registry

        Args:
            config_path: Path to MCP config YAML file
        """
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), "..", "mcp_config.yaml"
            )

        self.config_path = config_path
        self.config = self._load_config()
        self.clients = {}  # server_name -> MCPClientSync
        self.tools = {}  # tool_name -> (server_name, tool_schema)
        self.aliases = {}  # alias -> tool_name

    def _load_config(self):
        """
        Load MCP configuration from YAML file

        Returns:
            Configuration dict
        """
        if not os.path.exists(self.config_path):
            # Return default config if file doesn't exist
            return {"mcp_servers": {}}

        with open(self.config_path, "r") as f:
            return yaml.safe_load(f)

    def connect_all(self):
        """Connect to all configured MCP servers"""
        servers = self.config.get("mcp_servers", {})

        for server_name, server_config in servers.items():
            try:
                self._connect_server(server_name, server_config)
            except Exception as e:
                print(f"Warning: Failed to connect to MCP server '{server_name}': {e}")

    def _connect_server(self, server_name, server_config):
        """
        Connect to a single MCP server

        Args:
            server_name: Name of the server
            server_config: Server configuration dict
        """
        url = server_config.get("url")
        transport = server_config.get("transport", "http")
        timeout = server_config.get("timeout", 30)

        if not url:
            raise ValueError(f"Server '{server_name}' missing URL")

        client = MCPClientSync(url, transport, timeout)
        client.connect()

        # Initialize the connection
        client.initialize()

        self.clients[server_name] = client

        # Discover tools
        self._discover_tools(server_name, server_config)

    def _discover_tools(self, server_name, server_config):
        """
        Discover tools from a connected server

        Args:
            server_name: Name of the server
            server_config: Server configuration dict
        """
        client = self.clients[server_name]
        tools_config = server_config.get("tools", [])

        # Get all tools from server
        all_tools = client.list_tools()

        for tool in all_tools:
            tool_name = tool.get("name")

            if not tool_name:
                continue

            # Check if this tool is in the explicit list
            if tools_config:
                # Only register tools in the explicit list
                for tool_entry in tools_config:
                    if tool_entry.get("name") == tool_name:
                        # Register with alias if provided
                        alias = tool_entry.get("alias", tool_name)
                        self.tools[alias] = (server_name, tool)
                        self.aliases[alias] = tool_name
                        break
            else:
                # Auto-discover all tools
                self.tools[tool_name] = (server_name, tool)

    def list_tools(self):
        """
        List all discovered tools

        Returns:
            Dict of tool_name -> tool_schema
        """
        return {name: schema for name, (_, schema) in self.tools.items()}

    def get_tool_schema(self, tool_name):
        """
        Get schema for a specific tool

        Args:
            tool_name: Name or alias of the tool

        Returns:
            Tool schema or None if not found
        """
        if tool_name in self.tools:
            return self.tools[tool_name][1]
        return None

    def call_tool(self, tool_name, arguments):
        """
        Call a tool on its MCP server

        Args:
            tool_name: Name or alias of the tool
            arguments: Tool arguments dict

        Returns:
            Tool execution result
        """
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")

        server_name, tool_schema = self.tools[tool_name]
        client = self.clients[server_name]

        # Get actual tool name (in case alias was used)
        actual_tool_name = tool_schema.get("name")

        return client.call_tool(actual_tool_name, arguments)

    def get_server_tools(self, server_name):
        """
        Get all tools from a specific server

        Args:
            server_name: Name of the server

        Returns:
            List of tool schemas
        """
        tools = []
        for tool_name, (srv_name, tool_schema) in self.tools.items():
            if srv_name == server_name:
                tools.append(tool_schema)
        return tools

    def disconnect_all(self):
        """Disconnect from all MCP servers"""
        for server_name, client in self.clients.items():
            try:
                client.disconnect()
            except Exception as e:
                print(f"Warning: Error disconnecting from '{server_name}': {e}")

        self.clients.clear()
        self.tools.clear()
        self.aliases.clear()

    def __enter__(self):
        """Context manager entry"""
        self.connect_all()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect_all()


# Global registry instance
_global_registry = None


def get_registry(config_path=None):
    """
    Get or create global MCP tool registry

    Args:
        config_path: Optional path to config file

    Returns:
        MCPToolRegistry instance
    """
    global _global_registry

    if _global_registry is None:
        _global_registry = MCPToolRegistry(config_path)
        _global_registry.connect_all()

    return _global_registry
