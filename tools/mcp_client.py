"""
MCP Client - Generic MCP protocol handler

Implements JSON-RPC 2.0 communication with MCP servers over HTTP + SSE.
Supports tool discovery and invocation.
"""

import json
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List


class MCPClient:
    """Client for communicating with MCP servers via JSON-RPC 2.0"""

    def __init__(self, url, transport="http", timeout=30):
        """
        Initialize MCP client

        Args:
            url: MCP server URL
            transport: Transport type ('http' or 'stdio')
            timeout: Request timeout in seconds
        """
        self.url = url
        self.transport = transport
        self.timeout = timeout
        self.session = None
        self.request_id = 0

    async def connect(self):
        """Establish connection to MCP server"""
        if self.transport == "http":
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        elif self.transport == "stdio":
            # stdio transport would need subprocess management
            # For now, focus on HTTP + SSE
            raise NotImplementedError("stdio transport not yet implemented")
        else:
            raise ValueError(f"Unsupported transport: {self.transport}")

    async def disconnect(self):
        """Close connection to MCP server"""
        if self.session:
            await self.session.close()
            self.session = None

    def _next_request_id(self):
        """Generate next JSON-RPC request ID"""
        self.request_id += 1
        return self.request_id

    def _format_request(self, method, params=None):
        """
        Format JSON-RPC 2.0 request

        Args:
            method: JSON-RPC method name
            params: Method parameters (optional)

        Returns:
            JSON-RPC request dict
        """
        request = {"jsonrpc": "2.0", "id": self._next_request_id(), "method": method}
        if params:
            request["params"] = params
        return request

    async def _send_request(self, request):
        """
        Send JSON-RPC request and get response

        Args:
            request: JSON-RPC request dict

        Returns:
            Response data or raises exception
        """
        if not self.session:
            raise RuntimeError("Not connected to MCP server")

        try:
            async with self.session.post(
                self.url,
                json=request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")

                data = await response.json()

                # Check for JSON-RPC error
                if "error" in data:
                    error = data["error"]
                    raise Exception(
                        f"JSON-RPC Error {error.get('code')}: {error.get('message')}"
                    )

                return data.get("result")

        except aiohttp.ClientError as e:
            raise Exception(f"Connection error: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {str(e)}")

    async def initialize(self):
        """
        Initialize MCP connection

        Returns:
            Server capabilities
        """
        request = self._format_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "j4ne", "version": "1.0.0"},
            },
        )

        result = await self._send_request(request)
        return result

    async def list_tools(self):
        """
        List available tools from MCP server

        Returns:
            List of tool definitions
        """
        request = self._format_request("tools/list")
        result = await self._send_request(request)
        return result.get("tools", [])

    async def call_tool(self, tool_name, arguments):
        """
        Call a tool on the MCP server

        Args:
            tool_name: Name of tool to call
            arguments: Tool arguments dict

        Returns:
            Tool execution result
        """
        request = self._format_request(
            "tools/call", {"name": tool_name, "arguments": arguments}
        )

        result = await self._send_request(request)

        # MCP returns content array
        if "content" in result:
            return result["content"]

        return result

    async def get_tool_schema(self, tool_name):
        """
        Get schema for a specific tool

        Args:
            tool_name: Name of tool

        Returns:
            Tool schema or None if not found
        """
        tools = await self.list_tools()
        for tool in tools:
            if tool.get("name") == tool_name:
                return tool
        return None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()


class MCPClientSync:
    """Synchronous wrapper for MCPClient for non-async contexts"""

    def __init__(self, url, transport="http", timeout=30):
        """
        Initialize synchronous MCP client

        Args:
            url: MCP server URL
            transport: Transport type ('http' or 'stdio')
            timeout: Request timeout in seconds
        """
        self.url = url
        self.transport = transport
        self.timeout = timeout
        self._loop = None
        self._client = None  # Will be set by connect()

    def _get_loop(self):
        """Get or create event loop"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def connect(self):
        """Establish connection (synchronous)"""

        async def _connect():
            client = MCPClient(self.url, self.transport, self.timeout)
            await client.connect()
            return client

        self._loop = self._get_loop()
        self._client = self._loop.run_until_complete(_connect())

    def disconnect(self):
        """Close connection (synchronous)"""
        if self._client and self._loop:

            async def _disconnect():
                await self._client.disconnect()

            self._loop.run_until_complete(_disconnect())

    def initialize(self):
        """Initialize MCP connection (synchronous)"""
        if not self._client or not self._loop:
            raise RuntimeError("Not connected to MCP server")

        async def _init():
            return await self._client.initialize()

        return self._loop.run_until_complete(_init())

    def list_tools(self):
        """List available tools (synchronous)"""
        if not self._client or not self._loop:
            raise RuntimeError("Not connected to MCP server")

        async def _list():
            return await self._client.list_tools()

        return self._loop.run_until_complete(_list())

    def call_tool(self, tool_name, arguments):
        """Call a tool (synchronous)"""
        if not self._client or not self._loop:
            raise RuntimeError("Not connected to MCP server")

        async def _call():
            return await self._client.call_tool(tool_name, arguments)

        return self._loop.run_until_complete(_call())

    def get_tool_schema(self, tool_name):
        """Get tool schema (synchronous)"""
        if not self._client or not self._loop:
            raise RuntimeError("Not connected to MCP server")

        async def _schema():
            return await self._client.get_tool_schema(tool_name)

        return self._loop.run_until_complete(_schema())

    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            if hasattr(self, "_client") and self._client:
                self.disconnect()
        except:
            pass  # Ignore errors during cleanup
