"""
Python LSP Server Integration

Handles Python-specific LSP server management and configuration.
Supports both Pyright and Python LSP Server (pylsp) with automatic fallback.

This module provides:
- Python project detection
- Virtual environment detection
- Server-specific configuration
- Automatic server selection and fallback
"""

import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .lsp_client import LSPClient, LSPClientError, LSPServerNotFoundError


logger = logging.getLogger(__name__)


class PythonLSPServer:
    """
    Python Language Server manager with support for multiple LSP servers.
    
    Supports:
    - Pyright (Microsoft) - Fast, accurate, TypeScript-based
    - Python LSP Server (pylsp) - Pure Python, extensible
    
    Automatically detects Python projects and configures the appropriate server.
    """
    
    # Server configurations
    SERVERS = {
        "pyright": {
            "command": ["pyright-langserver", "--stdio"],
            "install_command": ["npm", "install", "-g", "pyright"],
            "check_command": ["pyright", "--version"],
            "description": "Pyright (Microsoft) - Fast, accurate, TypeScript-based"
        },
        "pylsp": {
            "command": ["pylsp"],
            "install_command": ["pip", "install", "python-lsp-server[all]"],
            "check_command": ["pylsp", "--help"],
            "description": "Python LSP Server - Pure Python, extensible"
        }
    }
    
    def __init__(self, workspace_root: Path, preferred_server: str = "pyright", timeout: float = 30.0):
        """
        Initialize Python LSP server manager.
        
        Args:
            workspace_root: Root directory of the Python project
            preferred_server: Preferred LSP server ("pyright" or "pylsp")
            timeout: Timeout for LSP operations in seconds
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.preferred_server = preferred_server
        self.timeout = timeout
        
        self._client: Optional[LSPClient] = None
        self._active_server: Optional[str] = None
        
        # Project information
        self.project_info = self._detect_python_project()
    
    async def start(self) -> None:
        """Start the Python LSP server with automatic fallback."""
        if self._client is not None:
            raise LSPClientError("Python LSP server is already running")
        
        # Try preferred server first, then fallback
        servers_to_try = [self.preferred_server]
        if self.preferred_server != "pylsp":
            servers_to_try.append("pylsp")
        if self.preferred_server != "pyright":
            servers_to_try.append("pyright")
        
        last_error = None
        for server_name in servers_to_try:
            try:
                await self._start_server(server_name)
                self._active_server = server_name
                logger.info(f"Started Python LSP server: {server_name}")
                return
            except LSPServerNotFoundError as e:
                last_error = e
                logger.warning(f"Server {server_name} not available: {e}")
                continue
            except Exception as e:
                last_error = e
                logger.error(f"Failed to start server {server_name}: {e}")
                continue
        
        # If we get here, no server could be started
        available_servers = self._get_available_servers()
        if not available_servers:
            raise LSPServerNotFoundError(
                f"No Python LSP servers found. Please install one of: {list(self.SERVERS.keys())}\n"
                f"Installation commands:\n" +
                "\n".join(f"  {name}: {' '.join(config['install_command'])}" 
                         for name, config in self.SERVERS.items())
            )
        else:
            raise LSPClientError(f"Failed to start any Python LSP server. Last error: {last_error}")
    
    async def stop(self) -> None:
        """Stop the Python LSP server."""
        if self._client is not None:
            await self._client.stop()
            self._client = None
            self._active_server = None
            logger.info("Python LSP server stopped")
    
    @property
    def client(self) -> LSPClient:
        """Get the active LSP client."""
        if self._client is None:
            raise LSPClientError("Python LSP server not started")
        return self._client
    
    @property
    def active_server(self) -> Optional[str]:
        """Get the name of the active LSP server."""
        return self._active_server
    
    def get_server_info(self) -> Dict[str, str]:
        """Get information about the active server and project."""
        info = {
            "active_server": self._active_server or "None",
            "workspace_root": str(self.workspace_root),
            "project_type": self.project_info["type"],
            "python_executable": self.project_info["python_executable"],
        }
        
        if self.project_info["virtual_env"]:
            info["virtual_env"] = str(self.project_info["virtual_env"])
        
        if self._active_server:
            server_config = self.SERVERS[self._active_server]
            info["server_description"] = server_config["description"]
            info["server_command"] = " ".join(server_config["command"])
        
        return info
    
    async def _start_server(self, server_name: str) -> None:
        """Start a specific LSP server."""
        if server_name not in self.SERVERS:
            raise ValueError(f"Unknown server: {server_name}")
        
        server_config = self.SERVERS[server_name]
        
        # Check if server is available
        if not self._is_server_available(server_name):
            raise LSPServerNotFoundError(f"Server {server_name} not found")
        
        # Create and configure client
        command = server_config["command"].copy()
        
        # Add server-specific configuration
        if server_name == "pyright":
            command = self._configure_pyright(command)
        elif server_name == "pylsp":
            command = self._configure_pylsp(command)
        
        # Create and start client
        self._client = LSPClient(command, self.workspace_root, self.timeout)
        await self._client.start()
    
    def _configure_pyright(self, command: List[str]) -> List[str]:
        """Configure Pyright-specific settings."""
        # Pyright reads configuration from pyrightconfig.json or pyproject.toml
        # We'll let it use default configuration for now
        return command
    
    def _configure_pylsp(self, command: List[str]) -> List[str]:
        """Configure Python LSP Server specific settings."""
        # pylsp can be configured via command line or configuration files
        # We'll use default configuration for now
        return command
    
    def _detect_python_project(self) -> Dict[str, any]:
        """Detect Python project type and configuration."""
        project_info = {
            "type": "unknown",
            "python_executable": sys.executable,
            "virtual_env": None,
            "config_files": []
        }
        
        # Check for various Python project indicators
        config_files = [
            "pyproject.toml",
            "setup.py", 
            "setup.cfg",
            "requirements.txt",
            "Pipfile",
            "poetry.lock",
            "pyrightconfig.json",
            ".pylintrc"
        ]
        
        found_configs = []
        for config_file in config_files:
            config_path = self.workspace_root / config_file
            if config_path.exists():
                found_configs.append(config_file)
        
        project_info["config_files"] = found_configs
        
        # Determine project type
        if "pyproject.toml" in found_configs:
            project_info["type"] = "pyproject"
        elif "setup.py" in found_configs:
            project_info["type"] = "setuptools"
        elif "Pipfile" in found_configs:
            project_info["type"] = "pipenv"
        elif "poetry.lock" in found_configs:
            project_info["type"] = "poetry"
        elif "requirements.txt" in found_configs:
            project_info["type"] = "requirements"
        elif any(p.suffix == ".py" for p in self.workspace_root.rglob("*.py")):
            project_info["type"] = "python"
        
        # Detect virtual environment
        venv_paths = [
            self.workspace_root / "venv",
            self.workspace_root / ".venv", 
            self.workspace_root / "env",
            self.workspace_root / ".env"
        ]
        
        for venv_path in venv_paths:
            if venv_path.exists() and (venv_path / "pyvenv.cfg").exists():
                project_info["virtual_env"] = venv_path
                # Update Python executable to use venv
                if sys.platform == "win32":
                    python_exe = venv_path / "Scripts" / "python.exe"
                else:
                    python_exe = venv_path / "bin" / "python"
                
                if python_exe.exists():
                    project_info["python_executable"] = str(python_exe)
                break
        
        return project_info
    
    def _is_server_available(self, server_name: str) -> bool:
        """Check if a specific LSP server is available."""
        if server_name not in self.SERVERS:
            return False
        
        server_config = self.SERVERS[server_name]
        
        # Check if the main executable is available
        if not shutil.which(server_config["command"][0]):
            return False
        
        # Try to run the check command
        try:
            result = subprocess.run(
                server_config["check_command"],
                capture_output=True,
                timeout=5.0,
                check=False
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False
    
    def _get_available_servers(self) -> List[str]:
        """Get list of available LSP servers."""
        available = []
        for server_name in self.SERVERS:
            if self._is_server_available(server_name):
                available.append(server_name)
        return available
    
    def get_installation_instructions(self) -> str:
        """Get installation instructions for Python LSP servers."""
        instructions = ["Python LSP Server Installation Instructions:", ""]
        
        for name, config in self.SERVERS.items():
            available = "✅" if self._is_server_available(name) else "❌"
            instructions.append(f"{available} {name}: {config['description']}")
            instructions.append(f"   Install: {' '.join(config['install_command'])}")
            instructions.append("")
        
        return "\n".join(instructions)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
