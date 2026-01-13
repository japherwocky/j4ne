"""
LSP Client Infrastructure

Provides JSON-RPC communication with Language Server Protocol (LSP) servers.
This module handles the low-level communication, process management, and
protocol details for interacting with LSP servers.

Based on analysis of OpenCode's implementation, this focuses on:
- Reliable process management
- Proper timeout handling  
- Position coordinate conversion
- Clean error handling
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import psutil

from pylsp_jsonrpc import streams, Endpoint


logger = logging.getLogger(__name__)


class LSPClientError(Exception):
    """Base exception for LSP client errors."""
    pass


class LSPServerNotFoundError(LSPClientError):
    """Raised when LSP server executable is not found."""
    pass


class LSPServerTimeoutError(LSPClientError):
    """Raised when LSP server operation times out."""
    pass


class LSPServerCommunicationError(LSPClientError):
    """Raised when communication with LSP server fails."""
    pass


class Position:
    """LSP Position with proper coordinate conversion."""
    
    def __init__(self, line: int, character: int, zero_based: bool = True):
        """
        Initialize position.
        
        Args:
            line: Line number
            character: Character position
            zero_based: If True, coordinates are 0-based (LSP protocol).
                       If False, coordinates are 1-based (editor display).
        """
        if zero_based:
            self.line = line
            self.character = character
        else:
            # Convert from 1-based (editor) to 0-based (LSP)
            self.line = max(0, line - 1)
            self.character = max(0, character - 1)
    
    def to_lsp(self) -> Dict[str, int]:
        """Convert to LSP protocol format (0-based)."""
        return {"line": self.line, "character": self.character}
    
    def to_editor(self) -> Tuple[int, int]:
        """Convert to editor format (1-based)."""
        return (self.line + 1, self.character + 1)
    
    @classmethod
    def from_lsp(cls, data: Dict[str, int]) -> "Position":
        """Create from LSP protocol data (0-based)."""
        return cls(data["line"], data["character"], zero_based=True)
    
    @classmethod
    def from_editor(cls, line: int, character: int) -> "Position":
        """Create from editor coordinates (1-based)."""
        return cls(line, character, zero_based=False)


class LSPClient:
    """
    LSP Client for communicating with Language Server Protocol servers.
    
    Handles process management, JSON-RPC communication, and protocol details.
    Designed to be simple and reliable, avoiding the complexity issues found
    in OpenCode's implementation.
    """
    
    def __init__(self, server_command: List[str], workspace_root: Path, timeout: float = 30.0):
        """
        Initialize LSP client.
        
        Args:
            server_command: Command to start LSP server (e.g., ["pyright-langserver", "--stdio"])
            workspace_root: Root directory of the workspace/project
            timeout: Default timeout for LSP operations in seconds
        """
        self.server_command = server_command
        self.workspace_root = Path(workspace_root).resolve()
        self.timeout = timeout
        
        self._process: Optional[subprocess.Popen] = None
        self._endpoint: Optional[Endpoint] = None
        self._initialized = False
        self._next_id = 1
        
        # Server capabilities (populated during initialization)
        self.server_capabilities: Dict[str, Any] = {}
    
    async def start(self) -> None:
        """Start the LSP server and initialize the connection."""
        if self._process is not None:
            raise LSPClientError("LSP server is already running")
        
        # Check if server executable exists
        if not self._check_server_executable():
            raise LSPServerNotFoundError(f"LSP server not found: {self.server_command[0]}")
        
        try:
            # Start server process
            self._process = subprocess.Popen(
                self.server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.workspace_root,
                env=os.environ.copy()
            )
            
            # Set up JSON-RPC communication
            self._endpoint = Endpoint(
                streams.JsonRpcStreamReader(self._process.stdout),
                streams.JsonRpcStreamWriter(self._process.stdin)
            )
            
            # Initialize the server
            await self._initialize()
            
            logger.info(f"LSP server started successfully: {self.server_command[0]}")
            
        except Exception as e:
            await self.stop()
            raise LSPServerCommunicationError(f"Failed to start LSP server: {e}")
    
    async def stop(self) -> None:
        """Stop the LSP server and clean up resources."""
        if self._initialized:
            try:
                # Send shutdown request
                await self._send_request("shutdown", {})
                # Send exit notification
                await self._send_notification("exit", {})
            except Exception as e:
                logger.warning(f"Error during LSP server shutdown: {e}")
        
        if self._process is not None:
            try:
                # Give process time to exit gracefully
                self._process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't exit gracefully
                if psutil.pid_exists(self._process.pid):
                    try:
                        parent = psutil.Process(self._process.pid)
                        for child in parent.children(recursive=True):
                            child.kill()
                        parent.kill()
                    except psutil.NoSuchProcess:
                        pass
                self._process.kill()
            
            self._process = None
        
        self._endpoint = None
        self._initialized = False
        logger.info("LSP server stopped")
    
    async def go_to_definition(self, file_path: Path, position: Position) -> List[Dict[str, Any]]:
        """
        Find the definition of a symbol at the given position.
        
        Args:
            file_path: Path to the file
            position: Position in the file
            
        Returns:
            List of location dictionaries with 'uri', 'range' keys
        """
        if not self._initialized:
            raise LSPClientError("LSP server not initialized")
        
        params = {
            "textDocument": {"uri": file_path.as_uri()},
            "position": position.to_lsp()
        }
        
        result = await self._send_request("textDocument/definition", params)
        return self._normalize_locations(result)
    
    async def find_references(self, file_path: Path, position: Position, include_declaration: bool = True) -> List[Dict[str, Any]]:
        """
        Find all references to a symbol at the given position.
        
        Args:
            file_path: Path to the file
            position: Position in the file
            include_declaration: Whether to include the declaration in results
            
        Returns:
            List of location dictionaries with 'uri', 'range' keys
        """
        if not self._initialized:
            raise LSPClientError("LSP server not initialized")
        
        params = {
            "textDocument": {"uri": file_path.as_uri()},
            "position": position.to_lsp(),
            "context": {"includeDeclaration": include_declaration}
        }
        
        result = await self._send_request("textDocument/references", params)
        return self._normalize_locations(result)
    
    async def hover(self, file_path: Path, position: Position) -> Optional[Dict[str, Any]]:
        """
        Get hover information for a symbol at the given position.
        
        Args:
            file_path: Path to the file
            position: Position in the file
            
        Returns:
            Hover information dictionary with 'contents', 'range' keys, or None
        """
        if not self._initialized:
            raise LSPClientError("LSP server not initialized")
        
        params = {
            "textDocument": {"uri": file_path.as_uri()},
            "position": position.to_lsp()
        }
        
        result = await self._send_request("textDocument/hover", params)
        return result
    
    async def document_symbols(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Get all symbols in a document.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of symbol dictionaries with 'name', 'kind', 'range', 'selectionRange' keys
        """
        if not self._initialized:
            raise LSPClientError("LSP server not initialized")
        
        params = {
            "textDocument": {"uri": file_path.as_uri()}
        }
        
        result = await self._send_request("textDocument/documentSymbol", params)
        return result or []
    
    async def workspace_symbols(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for symbols across the entire workspace.
        
        Args:
            query: Search query string
            
        Returns:
            List of symbol information dictionaries
        """
        if not self._initialized:
            raise LSPClientError("LSP server not initialized")
        
        params = {"query": query}
        
        result = await self._send_request("workspace/symbol", params)
        return result or []
    
    async def go_to_implementation(self, file_path: Path, position: Position) -> List[Dict[str, Any]]:
        """
        Find implementations of an interface or abstract method at the given position.
        
        Args:
            file_path: Path to the file
            position: Position in the file
            
        Returns:
            List of location dictionaries with 'uri', 'range' keys
        """
        if not self._initialized:
            raise LSPClientError("LSP server not initialized")
        
        params = {
            "textDocument": {"uri": file_path.as_uri()},
            "position": position.to_lsp()
        }
        
        result = await self._send_request("textDocument/implementation", params)
        return self._normalize_locations(result)
    
    async def prepare_call_hierarchy(self, file_path: Path, position: Position) -> List[Dict[str, Any]]:
        """
        Prepare call hierarchy items at the given position.
        
        Args:
            file_path: Path to the file
            position: Position in the file
            
        Returns:
            List of call hierarchy item dictionaries
        """
        if not self._initialized:
            raise LSPClientError("LSP server not initialized")
        
        params = {
            "textDocument": {"uri": file_path.as_uri()},
            "position": position.to_lsp()
        }
        
        result = await self._send_request("textDocument/prepareCallHierarchy", params)
        return result or []
    
    async def incoming_calls(self, call_hierarchy_item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find all functions/methods that call the given call hierarchy item.
        
        Args:
            call_hierarchy_item: Call hierarchy item from prepare_call_hierarchy
            
        Returns:
            List of incoming call dictionaries
        """
        if not self._initialized:
            raise LSPClientError("LSP server not initialized")
        
        params = {"item": call_hierarchy_item}
        
        result = await self._send_request("callHierarchy/incomingCalls", params)
        return result or []
    
    async def outgoing_calls(self, call_hierarchy_item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find all functions/methods called by the given call hierarchy item.
        
        Args:
            call_hierarchy_item: Call hierarchy item from prepare_call_hierarchy
            
        Returns:
            List of outgoing call dictionaries
        """
        if not self._initialized:
            raise LSPClientError("LSP server not initialized")
        
        params = {"item": call_hierarchy_item}
        
        result = await self._send_request("callHierarchy/outgoingCalls", params)
        return result or []
    
    def _check_server_executable(self) -> bool:
        """Check if the LSP server executable is available."""
        try:
            subprocess.run(
                [self.server_command[0], "--help"],
                capture_output=True,
                timeout=5.0,
                check=False
            )
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False
    
    async def _initialize(self) -> None:
        """Initialize the LSP server with workspace information."""
        params = {
            "processId": os.getpid(),
            "rootUri": self.workspace_root.as_uri(),
            "capabilities": {
                "textDocument": {
                    "definition": {"linkSupport": True},
                    "references": {},
                    "hover": {"contentFormat": ["markdown", "plaintext"]},
                    "documentSymbol": {"hierarchicalDocumentSymbolSupport": True},
                    "implementation": {"linkSupport": True},
                    "callHierarchy": {}
                },
                "workspace": {
                    "symbol": {}
                }
            },
            "workspaceFolders": [{
                "uri": self.workspace_root.as_uri(),
                "name": self.workspace_root.name
            }]
        }
        
        result = await self._send_request("initialize", params)
        self.server_capabilities = result.get("capabilities", {})
        
        # Send initialized notification
        await self._send_notification("initialized", {})
        self._initialized = True
    
    async def _send_request(self, method: str, params: Dict[str, Any]) -> Any:
        """Send a JSON-RPC request and wait for response."""
        if self._endpoint is None:
            raise LSPClientError("LSP endpoint not available")
        
        request_id = self._next_id
        self._next_id += 1
        
        try:
            # Send request with timeout
            future = self._endpoint.request(method, params)
            result = await asyncio.wait_for(future, timeout=self.timeout)
            return result
        except asyncio.TimeoutError:
            raise LSPServerTimeoutError(f"LSP request '{method}' timed out after {self.timeout}s")
        except Exception as e:
            raise LSPServerCommunicationError(f"LSP request '{method}' failed: {e}")
    
    async def _send_notification(self, method: str, params: Dict[str, Any]) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        if self._endpoint is None:
            raise LSPClientError("LSP endpoint not available")
        
        try:
            self._endpoint.notify(method, params)
        except Exception as e:
            raise LSPServerCommunicationError(f"LSP notification '{method}' failed: {e}")
    
    def _normalize_locations(self, locations: Union[None, Dict, List]) -> List[Dict[str, Any]]:
        """Normalize location results to a consistent list format."""
        if locations is None:
            return []
        
        if isinstance(locations, dict):
            # Single location
            return [locations]
        
        if isinstance(locations, list):
            return locations
        
        return []
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        asyncio.create_task(self.stop())
