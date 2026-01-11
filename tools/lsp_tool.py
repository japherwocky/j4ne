"""
LSP Tool - Language Server Protocol Integration

Provides sophisticated code intelligence for AI agents through LSP servers.
This tool offers the same code navigation and understanding capabilities
that developers use in VS Code and other modern editors.

Core Operations (Phase 1):
- goToDefinition: Find where symbols are defined
- findReferences: Find all references to symbols  
- hover: Get documentation and type information
- documentSymbol: List all symbols in a file

Based on analysis of OpenCode's implementation, this provides a simpler,
more reliable approach focused on Python with plans for multi-language support.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .lsp_client import Position, LSPClientError, LSPServerNotFoundError, LSPServerTimeoutError
from .python_lsp_server import PythonLSPServer


logger = logging.getLogger(__name__)


class LSPTool:
    """
    Language Server Protocol tool for code intelligence.
    
    Provides sophisticated code analysis capabilities including:
    - Symbol definition lookup
    - Reference finding
    - Hover information (documentation, types)
    - Document symbol listing
    
    Currently supports Python with Pyright/Pylsp servers.
    Designed for easy extension to other languages.
    """
    
    def __init__(self, workspace_root: Optional[Path] = None, timeout: float = 30.0):
        """
        Initialize LSP tool.
        
        Args:
            workspace_root: Root directory of the project (defaults to current directory)
            timeout: Timeout for LSP operations in seconds
        """
        self.workspace_root = Path(workspace_root or Path.cwd()).resolve()
        self.timeout = timeout
        
        # Language server instances
        self._python_server: Optional[PythonLSPServer] = None
        
        # Supported file extensions and their language servers
        self._language_map = {
            ".py": "python",
            ".pyi": "python",
        }
    
    async def go_to_definition(self, file_path: str, line: int, character: int) -> Dict[str, Any]:
        """
        Find the definition of a symbol at the given position.
        
        Args:
            file_path: Path to the file (relative to workspace or absolute)
            line: Line number (1-based, as shown in editors)
            character: Character position (1-based, as shown in editors)
            
        Returns:
            Dictionary with 'locations' key containing list of definition locations,
            or 'error' key if operation failed.
            
        Example:
            {
                "operation": "goToDefinition",
                "file": "src/main.py",
                "position": {"line": 10, "character": 5},
                "locations": [
                    {
                        "uri": "file:///path/to/src/utils.py",
                        "range": {
                            "start": {"line": 15, "character": 0},
                            "end": {"line": 15, "character": 12}
                        }
                    }
                ],
                "server": "pyright"
            }
        """
        try:
            file_path_obj = self._resolve_file_path(file_path)
            language = self._detect_language(file_path_obj)
            
            if language != "python":
                return {
                    "operation": "goToDefinition",
                    "error": f"Language '{language}' not supported yet. Currently supports: Python"
                }
            
            # Get or start Python server
            server = await self._get_python_server()
            
            # Convert to 0-based coordinates for LSP
            position = Position.from_editor(line, character)
            
            # Execute LSP request
            locations = await server.client.go_to_definition(file_path_obj, position)
            
            return {
                "operation": "goToDefinition",
                "file": str(file_path_obj.relative_to(self.workspace_root)),
                "position": {"line": line, "character": character},
                "locations": self._format_locations(locations),
                "server": server.active_server,
                "count": len(locations)
            }
            
        except Exception as e:
            return {
                "operation": "goToDefinition",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def find_references(self, file_path: str, line: int, character: int, include_declaration: bool = True) -> Dict[str, Any]:
        """
        Find all references to a symbol at the given position.
        
        Args:
            file_path: Path to the file (relative to workspace or absolute)
            line: Line number (1-based, as shown in editors)
            character: Character position (1-based, as shown in editors)
            include_declaration: Whether to include the symbol declaration in results
            
        Returns:
            Dictionary with 'references' key containing list of reference locations,
            or 'error' key if operation failed.
        """
        try:
            file_path_obj = self._resolve_file_path(file_path)
            language = self._detect_language(file_path_obj)
            
            if language != "python":
                return {
                    "operation": "findReferences",
                    "error": f"Language '{language}' not supported yet. Currently supports: Python"
                }
            
            # Get or start Python server
            server = await self._get_python_server()
            
            # Convert to 0-based coordinates for LSP
            position = Position.from_editor(line, character)
            
            # Execute LSP request
            references = await server.client.find_references(file_path_obj, position, include_declaration)
            
            return {
                "operation": "findReferences",
                "file": str(file_path_obj.relative_to(self.workspace_root)),
                "position": {"line": line, "character": character},
                "include_declaration": include_declaration,
                "references": self._format_locations(references),
                "server": server.active_server,
                "count": len(references)
            }
            
        except Exception as e:
            return {
                "operation": "findReferences",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def hover(self, file_path: str, line: int, character: int) -> Dict[str, Any]:
        """
        Get hover information (documentation, type info) for a symbol at the given position.
        
        Args:
            file_path: Path to the file (relative to workspace or absolute)
            line: Line number (1-based, as shown in editors)
            character: Character position (1-based, as shown in editors)
            
        Returns:
            Dictionary with 'hover' key containing hover information,
            or 'error' key if operation failed.
        """
        try:
            file_path_obj = self._resolve_file_path(file_path)
            language = self._detect_language(file_path_obj)
            
            if language != "python":
                return {
                    "operation": "hover",
                    "error": f"Language '{language}' not supported yet. Currently supports: Python"
                }
            
            # Get or start Python server
            server = await self._get_python_server()
            
            # Convert to 0-based coordinates for LSP
            position = Position.from_editor(line, character)
            
            # Execute LSP request
            hover_info = await server.client.hover(file_path_obj, position)
            
            result = {
                "operation": "hover",
                "file": str(file_path_obj.relative_to(self.workspace_root)),
                "position": {"line": line, "character": character},
                "server": server.active_server
            }
            
            if hover_info:
                result["hover"] = self._format_hover(hover_info)
            else:
                result["hover"] = None
                result["message"] = "No hover information available"
            
            return result
            
        except Exception as e:
            return {
                "operation": "hover",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def document_symbols(self, file_path: str) -> Dict[str, Any]:
        """
        Get all symbols (functions, classes, variables) in a document.
        
        Args:
            file_path: Path to the file (relative to workspace or absolute)
            
        Returns:
            Dictionary with 'symbols' key containing list of symbols,
            or 'error' key if operation failed.
        """
        try:
            file_path_obj = self._resolve_file_path(file_path)
            language = self._detect_language(file_path_obj)
            
            if language != "python":
                return {
                    "operation": "documentSymbol",
                    "error": f"Language '{language}' not supported yet. Currently supports: Python"
                }
            
            # Get or start Python server
            server = await self._get_python_server()
            
            # Execute LSP request
            symbols = await server.client.document_symbols(file_path_obj)
            
            return {
                "operation": "documentSymbol",
                "file": str(file_path_obj.relative_to(self.workspace_root)),
                "symbols": self._format_symbols(symbols),
                "server": server.active_server,
                "count": len(symbols)
            }
            
        except Exception as e:
            return {
                "operation": "documentSymbol",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def workspace_symbols(self, query: str) -> Dict[str, Any]:
        """
        Search for symbols across the entire workspace.
        
        Args:
            query: Search query string
            
        Returns:
            Dictionary with 'symbols' key containing list of matching symbols,
            or 'error' key if operation failed.
        """
        try:
            # Get or start Python server
            server = await self._get_python_server()
            
            # Execute LSP request
            symbols = await server.client.workspace_symbols(query)
            
            return {
                "operation": "workspaceSymbol",
                "query": query,
                "symbols": self._format_workspace_symbols(symbols),
                "server": server.active_server,
                "count": len(symbols)
            }
            
        except Exception as e:
            return {
                "operation": "workspaceSymbol",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def go_to_implementation(self, file_path: str, line: int, character: int) -> Dict[str, Any]:
        """
        Find implementations of an interface or abstract method at the given position.
        
        Args:
            file_path: Path to the file (relative to workspace or absolute)
            line: Line number (1-based, as shown in editors)
            character: Character position (1-based, as shown in editors)
            
        Returns:
            Dictionary with 'implementations' key containing list of implementation locations,
            or 'error' key if operation failed.
        """
        try:
            file_path_obj = self._resolve_file_path(file_path)
            language = self._detect_language(file_path_obj)
            
            if language != "python":
                return {
                    "operation": "goToImplementation",
                    "error": f"Language '{language}' not supported yet. Currently supports: Python"
                }
            
            # Get or start Python server
            server = await self._get_python_server()
            
            # Convert to 0-based coordinates for LSP
            position = Position.from_editor(line, character)
            
            # Execute LSP request
            implementations = await server.client.go_to_implementation(file_path_obj, position)
            
            return {
                "operation": "goToImplementation",
                "file": str(file_path_obj.relative_to(self.workspace_root)),
                "position": {"line": line, "character": character},
                "implementations": self._format_locations(implementations),
                "server": server.active_server,
                "count": len(implementations)
            }
            
        except Exception as e:
            return {
                "operation": "goToImplementation",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def prepare_call_hierarchy(self, file_path: str, line: int, character: int) -> Dict[str, Any]:
        """
        Prepare call hierarchy items at the given position.
        
        Args:
            file_path: Path to the file (relative to workspace or absolute)
            line: Line number (1-based, as shown in editors)
            character: Character position (1-based, as shown in editors)
            
        Returns:
            Dictionary with 'items' key containing list of call hierarchy items,
            or 'error' key if operation failed.
        """
        try:
            file_path_obj = self._resolve_file_path(file_path)
            language = self._detect_language(file_path_obj)
            
            if language != "python":
                return {
                    "operation": "prepareCallHierarchy",
                    "error": f"Language '{language}' not supported yet. Currently supports: Python"
                }
            
            # Get or start Python server
            server = await self._get_python_server()
            
            # Convert to 0-based coordinates for LSP
            position = Position.from_editor(line, character)
            
            # Execute LSP request
            items = await server.client.prepare_call_hierarchy(file_path_obj, position)
            
            return {
                "operation": "prepareCallHierarchy",
                "file": str(file_path_obj.relative_to(self.workspace_root)),
                "position": {"line": line, "character": character},
                "items": self._format_call_hierarchy_items(items),
                "server": server.active_server,
                "count": len(items)
            }
            
        except Exception as e:
            return {
                "operation": "prepareCallHierarchy",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def incoming_calls(self, call_hierarchy_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find all functions/methods that call the given call hierarchy item.
        
        Args:
            call_hierarchy_item: Call hierarchy item from prepare_call_hierarchy
            
        Returns:
            Dictionary with 'calls' key containing list of incoming calls,
            or 'error' key if operation failed.
        """
        try:
            # Get or start Python server
            server = await self._get_python_server()
            
            # Execute LSP request
            calls = await server.client.incoming_calls(call_hierarchy_item)
            
            return {
                "operation": "incomingCalls",
                "item": call_hierarchy_item,
                "calls": self._format_incoming_calls(calls),
                "server": server.active_server,
                "count": len(calls)
            }
            
        except Exception as e:
            return {
                "operation": "incomingCalls",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def outgoing_calls(self, call_hierarchy_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find all functions/methods called by the given call hierarchy item.
        
        Args:
            call_hierarchy_item: Call hierarchy item from prepare_call_hierarchy
            
        Returns:
            Dictionary with 'calls' key containing list of outgoing calls,
            or 'error' key if operation failed.
        """
        try:
            # Get or start Python server
            server = await self._get_python_server()
            
            # Execute LSP request
            calls = await server.client.outgoing_calls(call_hierarchy_item)
            
            return {
                "operation": "outgoingCalls",
                "item": call_hierarchy_item,
                "calls": self._format_outgoing_calls(calls),
                "server": server.active_server,
                "count": len(calls)
            }
            
        except Exception as e:
            return {
                "operation": "outgoingCalls",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def get_server_info(self) -> Dict[str, Any]:
        """
        Get information about available and active LSP servers.
        
        Returns:
            Dictionary with server status and configuration information.
        """
        info = {
            "workspace_root": str(self.workspace_root),
            "timeout": self.timeout,
            "supported_languages": list(set(self._language_map.values())),
            "supported_extensions": list(self._language_map.keys())
        }
        
        # Python server info
        if self._python_server:
            info["python"] = self._python_server.get_server_info()
        else:
            # Get installation instructions without starting server
            temp_server = PythonLSPServer(self.workspace_root)
            info["python"] = {
                "status": "not_started",
                "installation_instructions": temp_server.get_installation_instructions()
            }
        
        return info
    
    async def stop_all_servers(self) -> None:
        """Stop all running LSP servers and clean up resources."""
        if self._python_server:
            await self._python_server.stop()
            self._python_server = None
        
        logger.info("All LSP servers stopped")
    
    def _resolve_file_path(self, file_path: str) -> Path:
        """Resolve file path relative to workspace root."""
        path = Path(file_path)
        
        if path.is_absolute():
            # Make sure absolute path is within workspace
            try:
                path.relative_to(self.workspace_root)
                return path
            except ValueError:
                raise ValueError(f"File path {file_path} is outside workspace {self.workspace_root}")
        else:
            # Resolve relative to workspace root
            resolved = (self.workspace_root / path).resolve()
            if not resolved.exists():
                raise FileNotFoundError(f"File not found: {resolved}")
            return resolved
    
    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension."""
        suffix = file_path.suffix.lower()
        return self._language_map.get(suffix, "unknown")
    
    async def _get_python_server(self) -> PythonLSPServer:
        """Get or start the Python LSP server."""
        if self._python_server is None:
            self._python_server = PythonLSPServer(self.workspace_root, timeout=self.timeout)
            await self._python_server.start()
        return self._python_server
    
    def _format_locations(self, locations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format location results for consistent output."""
        formatted = []
        for location in locations:
            if "uri" in location and "range" in location:
                # Convert URI to relative path
                uri = location["uri"]
                if uri.startswith("file://"):
                    file_path = Path(uri[7:])  # Remove "file://" prefix
                    try:
                        relative_path = file_path.relative_to(self.workspace_root)
                        location["file"] = str(relative_path)
                    except ValueError:
                        location["file"] = str(file_path)
                
                # Convert LSP positions to editor positions (0-based to 1-based)
                if "range" in location:
                    range_data = location["range"]
                    if "start" in range_data:
                        start = range_data["start"]
                        range_data["start"] = {
                            "line": start["line"] + 1,
                            "character": start["character"] + 1
                        }
                    if "end" in range_data:
                        end = range_data["end"]
                        range_data["end"] = {
                            "line": end["line"] + 1,
                            "character": end["character"] + 1
                        }
                
                formatted.append(location)
        
        return formatted
    
    def _format_hover(self, hover_info: Dict[str, Any]) -> Dict[str, Any]:
        """Format hover information for consistent output."""
        formatted = {}
        
        if "contents" in hover_info:
            contents = hover_info["contents"]
            if isinstance(contents, str):
                formatted["contents"] = contents
            elif isinstance(contents, list):
                # Join multiple content items
                formatted["contents"] = "\n".join(str(item) for item in contents)
            elif isinstance(contents, dict):
                # Handle MarkupContent format
                if "value" in contents:
                    formatted["contents"] = contents["value"]
                    if "kind" in contents:
                        formatted["format"] = contents["kind"]
                else:
                    formatted["contents"] = str(contents)
            else:
                formatted["contents"] = str(contents)
        
        if "range" in hover_info:
            # Convert LSP range to editor coordinates
            range_data = hover_info["range"]
            if "start" in range_data and "end" in range_data:
                formatted["range"] = {
                    "start": {
                        "line": range_data["start"]["line"] + 1,
                        "character": range_data["start"]["character"] + 1
                    },
                    "end": {
                        "line": range_data["end"]["line"] + 1,
                        "character": range_data["end"]["character"] + 1
                    }
                }
        
        return formatted
    
    def _format_symbols(self, symbols: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format document symbols for consistent output."""
        formatted = []
        
        for symbol in symbols:
            formatted_symbol = {}
            
            # Basic symbol information
            if "name" in symbol:
                formatted_symbol["name"] = symbol["name"]
            if "kind" in symbol:
                formatted_symbol["kind"] = self._symbol_kind_to_string(symbol["kind"])
                formatted_symbol["kind_number"] = symbol["kind"]
            if "detail" in symbol:
                formatted_symbol["detail"] = symbol["detail"]
            
            # Convert ranges to editor coordinates
            if "range" in symbol:
                range_data = symbol["range"]
                formatted_symbol["range"] = {
                    "start": {
                        "line": range_data["start"]["line"] + 1,
                        "character": range_data["start"]["character"] + 1
                    },
                    "end": {
                        "line": range_data["end"]["line"] + 1,
                        "character": range_data["end"]["character"] + 1
                    }
                }
            
            if "selectionRange" in symbol:
                sel_range = symbol["selectionRange"]
                formatted_symbol["selectionRange"] = {
                    "start": {
                        "line": sel_range["start"]["line"] + 1,
                        "character": sel_range["start"]["character"] + 1
                    },
                    "end": {
                        "line": sel_range["end"]["line"] + 1,
                        "character": sel_range["end"]["character"] + 1
                    }
                }
            
            # Handle nested symbols (children)
            if "children" in symbol and symbol["children"]:
                formatted_symbol["children"] = self._format_symbols(symbol["children"])
            
            formatted.append(formatted_symbol)
        
        return formatted
    
    def _symbol_kind_to_string(self, kind: int) -> str:
        """Convert LSP symbol kind number to human-readable string."""
        # LSP SymbolKind enumeration
        symbol_kinds = {
            1: "File", 2: "Module", 3: "Namespace", 4: "Package", 5: "Class",
            6: "Method", 7: "Property", 8: "Field", 9: "Constructor", 10: "Enum",
            11: "Interface", 12: "Function", 13: "Variable", 14: "Constant", 15: "String",
            16: "Number", 17: "Boolean", 18: "Array", 19: "Object", 20: "Key",
            21: "Null", 22: "EnumMember", 23: "Struct", 24: "Event", 25: "Operator",
            26: "TypeParameter"
        }
        return symbol_kinds.get(kind, f"Unknown({kind})")
    
    def _format_workspace_symbols(self, symbols: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format workspace symbol results for consistent output."""
        formatted = []
        
        for symbol in symbols:
            formatted_symbol = {}
            
            # Basic symbol information
            if "name" in symbol:
                formatted_symbol["name"] = symbol["name"]
            if "kind" in symbol:
                formatted_symbol["kind"] = self._symbol_kind_to_string(symbol["kind"])
                formatted_symbol["kind_number"] = symbol["kind"]
            if "containerName" in symbol:
                formatted_symbol["container"] = symbol["containerName"]
            
            # Location information
            if "location" in symbol:
                location = symbol["location"]
                if "uri" in location:
                    uri = location["uri"]
                    if uri.startswith("file://"):
                        file_path = Path(uri[7:])  # Remove "file://" prefix
                        try:
                            relative_path = file_path.relative_to(self.workspace_root)
                            formatted_symbol["file"] = str(relative_path)
                        except ValueError:
                            formatted_symbol["file"] = str(file_path)
                
                if "range" in location:
                    range_data = location["range"]
                    formatted_symbol["range"] = {
                        "start": {
                            "line": range_data["start"]["line"] + 1,
                            "character": range_data["start"]["character"] + 1
                        },
                        "end": {
                            "line": range_data["end"]["line"] + 1,
                            "character": range_data["end"]["character"] + 1
                        }
                    }
            
            formatted.append(formatted_symbol)
        
        return formatted
    
    def _format_call_hierarchy_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format call hierarchy items for consistent output."""
        formatted = []
        
        for item in items:
            formatted_item = {}
            
            # Basic item information
            if "name" in item:
                formatted_item["name"] = item["name"]
            if "kind" in item:
                formatted_item["kind"] = self._symbol_kind_to_string(item["kind"])
                formatted_item["kind_number"] = item["kind"]
            if "detail" in item:
                formatted_item["detail"] = item["detail"]
            
            # URI and file information
            if "uri" in item:
                uri = item["uri"]
                if uri.startswith("file://"):
                    file_path = Path(uri[7:])  # Remove "file://" prefix
                    try:
                        relative_path = file_path.relative_to(self.workspace_root)
                        formatted_item["file"] = str(relative_path)
                    except ValueError:
                        formatted_item["file"] = str(file_path)
            
            # Range information
            if "range" in item:
                range_data = item["range"]
                formatted_item["range"] = {
                    "start": {
                        "line": range_data["start"]["line"] + 1,
                        "character": range_data["start"]["character"] + 1
                    },
                    "end": {
                        "line": range_data["end"]["line"] + 1,
                        "character": range_data["end"]["character"] + 1
                    }
                }
            
            if "selectionRange" in item:
                sel_range = item["selectionRange"]
                formatted_item["selectionRange"] = {
                    "start": {
                        "line": sel_range["start"]["line"] + 1,
                        "character": sel_range["start"]["character"] + 1
                    },
                    "end": {
                        "line": sel_range["end"]["line"] + 1,
                        "character": sel_range["end"]["character"] + 1
                    }
                }
            
            # Keep original item for use in subsequent calls
            formatted_item["_original"] = item
            
            formatted.append(formatted_item)
        
        return formatted
    
    def _format_incoming_calls(self, calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format incoming call results for consistent output."""
        formatted = []
        
        for call in calls:
            formatted_call = {}
            
            # From information (who is calling)
            if "from" in call:
                from_item = call["from"]
                formatted_call["from"] = {
                    "name": from_item.get("name", "Unknown"),
                    "kind": self._symbol_kind_to_string(from_item.get("kind", 0)),
                    "detail": from_item.get("detail", "")
                }
                
                if "uri" in from_item:
                    uri = from_item["uri"]
                    if uri.startswith("file://"):
                        file_path = Path(uri[7:])
                        try:
                            relative_path = file_path.relative_to(self.workspace_root)
                            formatted_call["from"]["file"] = str(relative_path)
                        except ValueError:
                            formatted_call["from"]["file"] = str(file_path)
                
                if "range" in from_item:
                    range_data = from_item["range"]
                    formatted_call["from"]["range"] = {
                        "start": {
                            "line": range_data["start"]["line"] + 1,
                            "character": range_data["start"]["character"] + 1
                        },
                        "end": {
                            "line": range_data["end"]["line"] + 1,
                            "character": range_data["end"]["character"] + 1
                        }
                    }
            
            # From ranges (where the calls occur)
            if "fromRanges" in call:
                formatted_ranges = []
                for range_data in call["fromRanges"]:
                    formatted_ranges.append({
                        "start": {
                            "line": range_data["start"]["line"] + 1,
                            "character": range_data["start"]["character"] + 1
                        },
                        "end": {
                            "line": range_data["end"]["line"] + 1,
                            "character": range_data["end"]["character"] + 1
                        }
                    })
                formatted_call["fromRanges"] = formatted_ranges
            
            formatted.append(formatted_call)
        
        return formatted
    
    def _format_outgoing_calls(self, calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format outgoing call results for consistent output."""
        formatted = []
        
        for call in calls:
            formatted_call = {}
            
            # To information (who is being called)
            if "to" in call:
                to_item = call["to"]
                formatted_call["to"] = {
                    "name": to_item.get("name", "Unknown"),
                    "kind": self._symbol_kind_to_string(to_item.get("kind", 0)),
                    "detail": to_item.get("detail", "")
                }
                
                if "uri" in to_item:
                    uri = to_item["uri"]
                    if uri.startswith("file://"):
                        file_path = Path(uri[7:])
                        try:
                            relative_path = file_path.relative_to(self.workspace_root)
                            formatted_call["to"]["file"] = str(relative_path)
                        except ValueError:
                            formatted_call["to"]["file"] = str(file_path)
                
                if "range" in to_item:
                    range_data = to_item["range"]
                    formatted_call["to"]["range"] = {
                        "start": {
                            "line": range_data["start"]["line"] + 1,
                            "character": range_data["start"]["character"] + 1
                        },
                        "end": {
                            "line": range_data["end"]["line"] + 1,
                            "character": range_data["end"]["character"] + 1
                        }
                    }
            
            # From ranges (where the calls are made from)
            if "fromRanges" in call:
                formatted_ranges = []
                for range_data in call["fromRanges"]:
                    formatted_ranges.append({
                        "start": {
                            "line": range_data["start"]["line"] + 1,
                            "character": range_data["start"]["character"] + 1
                        },
                        "end": {
                            "line": range_data["end"]["line"] + 1,
                            "character": range_data["end"]["character"] + 1
                        }
                    })
                formatted_call["fromRanges"] = formatted_ranges
            
            formatted.append(formatted_call)
        
        return formatted
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_all_servers()


# Convenience functions for direct usage
async def go_to_definition(file_path: str, line: int, character: int, workspace_root: Optional[str] = None) -> Dict[str, Any]:
    """Find the definition of a symbol at the given position."""
    async with LSPTool(workspace_root and Path(workspace_root)) as lsp:
        return await lsp.go_to_definition(file_path, line, character)


async def find_references(file_path: str, line: int, character: int, workspace_root: Optional[str] = None, include_declaration: bool = True) -> Dict[str, Any]:
    """Find all references to a symbol at the given position."""
    async with LSPTool(workspace_root and Path(workspace_root)) as lsp:
        return await lsp.find_references(file_path, line, character, include_declaration)


async def hover(file_path: str, line: int, character: int, workspace_root: Optional[str] = None) -> Dict[str, Any]:
    """Get hover information for a symbol at the given position."""
    async with LSPTool(workspace_root and Path(workspace_root)) as lsp:
        return await lsp.hover(file_path, line, character)


async def document_symbols(file_path: str, workspace_root: Optional[str] = None) -> Dict[str, Any]:
    """Get all symbols in a document."""
    async with LSPTool(workspace_root and Path(workspace_root)) as lsp:
        return await lsp.document_symbols(file_path)


async def get_server_info(workspace_root: Optional[str] = None) -> Dict[str, Any]:
    """Get information about available LSP servers."""
    async with LSPTool(workspace_root and Path(workspace_root)) as lsp:
        return await lsp.get_server_info()


async def workspace_symbols(query: str, workspace_root: Optional[str] = None) -> Dict[str, Any]:
    """Search for symbols across the entire workspace."""
    async with LSPTool(workspace_root and Path(workspace_root)) as lsp:
        return await lsp.workspace_symbols(query)


async def go_to_implementation(file_path: str, line: int, character: int, workspace_root: Optional[str] = None) -> Dict[str, Any]:
    """Find implementations of an interface or abstract method at the given position."""
    async with LSPTool(workspace_root and Path(workspace_root)) as lsp:
        return await lsp.go_to_implementation(file_path, line, character)


async def prepare_call_hierarchy(file_path: str, line: int, character: int, workspace_root: Optional[str] = None) -> Dict[str, Any]:
    """Prepare call hierarchy items at the given position."""
    async with LSPTool(workspace_root and Path(workspace_root)) as lsp:
        return await lsp.prepare_call_hierarchy(file_path, line, character)


async def incoming_calls(call_hierarchy_item: Dict[str, Any], workspace_root: Optional[str] = None) -> Dict[str, Any]:
    """Find all functions/methods that call the given call hierarchy item."""
    async with LSPTool(workspace_root and Path(workspace_root)) as lsp:
        return await lsp.incoming_calls(call_hierarchy_item)


async def outgoing_calls(call_hierarchy_item: Dict[str, Any], workspace_root: Optional[str] = None) -> Dict[str, Any]:
    """Find all functions/methods called by the given call hierarchy item."""
    async with LSPTool(workspace_root and Path(workspace_root)) as lsp:
        return await lsp.outgoing_calls(call_hierarchy_item)
