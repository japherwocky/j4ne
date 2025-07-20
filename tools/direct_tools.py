"""
Direct Tools Implementation - A simplified approach to tool execution without stdio communication.

This module provides a direct way to call tools as Python functions rather than through
subprocess communication, eliminating the overhead of the MCP protocol over stdio.
"""

from typing import Dict, List, Any, Optional, Union, Type
import os
import sqlite3
import json
import logging
import pathspec
import subprocess
import shlex
from pydantic import BaseModel, Field

# Import the global database connection
from db import db

# Configure logging
logger = logging.getLogger('direct_tools')

# ---- Tool Input Models ----

class FileRead(BaseModel):
    """Input model for reading a file"""
    path: str = Field(description="Path to the file to read")

class FileWrite(BaseModel):
    """Input model for writing to a file"""
    path: str = Field(description="Path to the file to write")
    content: str = Field(description="Content to write to the file")
    create_dirs: bool = Field(default=False, description="Create parent directories if they don't exist")

class FileDelete(BaseModel):
    """Input model for deleting a file or directory"""
    path: str = Field(description="Path to delete")
    recursive: bool = Field(default=False, description="Recursively delete directories")

class ListFiles(BaseModel):
    """Input model for listing files in a directory"""
    directory: str = Field(default=".", description="Directory to list files in")

class SqlQuery(BaseModel):
    """Input model for executing a SQL query"""
    query: str = Field(description="SQL query to execute")

class SqlCreateTable(BaseModel):
    """Input model for creating a SQL table"""
    query: str = Field(description="CREATE TABLE SQL statement")

class SqlDescribeTable(BaseModel):
    """Input model for describing a SQL table"""
    table_name: str = Field(description="Name of the table to describe")

# Add a new model for AppendInsight
class AppendInsight(BaseModel):
    """Input model for adding a business insight"""
    insight: str = Field(description="Business insight discovered from data analysis")

# Add an empty model for tools that don't need parameters
class EmptyModel(BaseModel):
    """Empty model for tools that don't need parameters"""
    pass

# ---- Git Input Models ----

class GitStatus(BaseModel):
    """Input model for git status command"""
    repository_path: str = Field(default=".", description="Path to the git repository")

class GitAdd(BaseModel):
    """Input model for git add command"""
    repository_path: str = Field(default=".", description="Path to the git repository")
    files: str = Field(description="Files to add (can be specific files or '.' for all)")

class GitCommit(BaseModel):
    """Input model for git commit command"""
    repository_path: str = Field(default=".", description="Path to the git repository")
    message: str = Field(description="Commit message")
    add_all: bool = Field(default=False, description="Add all modified files before committing")

class GitBranch(BaseModel):
    """Input model for git branch operations"""
    repository_path: str = Field(default=".", description="Path to the git repository")
    action: str = Field(default="list", description="Action: 'list', 'create', 'switch', or 'delete'")
    branch_name: str = Field(default="", description="Branch name for create/switch/delete operations")

class GitLog(BaseModel):
    """Input model for git log command"""
    repository_path: str = Field(default=".", description="Path to the git repository")
    max_count: int = Field(default=10, description="Maximum number of commits to show")
    oneline: bool = Field(default=True, description="Show commits in oneline format")

class GitDiff(BaseModel):
    """Input model for git diff command"""
    repository_path: str = Field(default=".", description="Path to the git repository")
    staged: bool = Field(default=False, description="Show staged changes (--cached)")
    file_path: str = Field(default="", description="Specific file to diff (optional)")

# ---- Base Classes ----

class DirectTool:
    """Base class for all direct tools"""
    
    def __init__(self, name: str, description: str, input_model: Type[BaseModel]):
        self.name = name
        self.description = description
        self.input_model = input_model
    
    def get_definition(self) -> Dict[str, Any]:
        """Return the tool definition in OpenAI-compatible format"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_model.model_json_schema()
            }
        }
    
    def validate_args(self, **kwargs) -> Dict[str, Any]:
        """Validate arguments against the input model"""
        try:
            validated = self.input_model(**kwargs)
            return validated.model_dump()
        except Exception as e:
            logger.error(f"Validation error for {self.name}: {str(e)}")
            raise ValueError(f"Invalid arguments for {self.name}: {str(e)}")
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with the given parameters"""
        # Validate arguments
        validated_args = self.validate_args(**kwargs)
        
        # Execute the tool implementation
        try:
            return self._execute(**validated_args)
        except Exception as e:
            logger.error(f"Error executing {self.name}: {str(e)}")
            return {"error": f"Tool execution error: {str(e)}"}
    
    def _execute(self, **kwargs) -> Dict[str, Any]:
        """Tool-specific implementation to be overridden by subclasses"""
        raise NotImplementedError("Subclasses must implement _execute()")

class ToolProvider:
    """Base class for tool providers"""
    
    def __init__(self, prefix: str):
        self.prefix = prefix
        self.tools: Dict[str, DirectTool] = {}
    
    def register_tool(self, tool: DirectTool) -> None:
        """Register a tool with this provider"""
        # Ensure the tool name has the provider prefix
        if not tool.name.startswith(f"{self.prefix}."):
            tool.name = f"{self.prefix}.{tool.name}"
        
        self.tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")
    
    def get_tools(self) -> Dict[str, DirectTool]:
        """Return all tools provided by this provider"""
        return self.tools

# ---- Filesystem Tool Provider ----

class FilesystemToolProvider(ToolProvider):
    """Provider for filesystem-related tools"""
    
    def __init__(self, root_path: str):
        super().__init__("filesystem")
        self.root_path = os.path.abspath(root_path)
        logger.info(f"Initializing FilesystemToolProvider with root path: {self.root_path}")
        
        # Setup gitignore patterns
        self._setup_ignore_patterns()
        
        # Register tools
        self._register_tools()
    
    def _setup_ignore_patterns(self) -> None:
        """Set up patterns for files to ignore"""
        default_patterns = [
            ".git", "__pycache__", "*.pyc", ".venv", "venv", ".env",
            ".idea", ".vscode", "*.egg-info", "dist", "build",
            ".pytest_cache", ".coverage", "htmlcov", ".DS_Store", "Thumbs.db"
        ]
        
        gitignore_path = os.path.join(self.root_path, ".gitignore")
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r") as f:
                patterns = f.readlines()
            logger.debug(f"Loaded {len(patterns)} patterns from .gitignore")
        else:
            patterns = default_patterns
            logger.debug(f"Using {len(patterns)} default ignore patterns")
        
        self.ignore_patterns = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    
    def _register_tools(self) -> None:
        """Register all filesystem tools"""
        self.register_tool(ReadFileTool(self))
        self.register_tool(WriteFileTool(self))
        self.register_tool(ListFilesTool(self))
        self.register_tool(DeleteFileTool(self))
    
    def is_safe_path(self, path: str) -> bool:
        """Check if a path is within the root directory"""
        abs_path = os.path.abspath(os.path.join(self.root_path, path))
        return abs_path.startswith(self.root_path)
    
    def is_ignored(self, path: str) -> bool:
        """Check if a path matches ignore patterns"""
        rel = os.path.relpath(path, self.root_path)
        return self.ignore_patterns.match_file(rel)

# ---- Filesystem Tools ----

class ReadFileTool(DirectTool):
    """Tool for reading file contents"""
    
    def __init__(self, provider: FilesystemToolProvider):
        super().__init__(
            name="read-file",
            description="Read the entire contents of a file",
            input_model=FileRead
        )
        self.provider = provider
    
    def _execute(self, path: str) -> Dict[str, Any]:
        """Read a file and return its contents"""
        if not self.provider.is_safe_path(path):
            return {"error": "Path is outside root directory"}
        
        full_path = os.path.join(self.provider.root_path, path)
        
        if not os.path.isfile(full_path):
            return {"error": f"File not found: {path}"}
        
        if self.provider.is_ignored(full_path):
            return {"error": f"File is ignored: {path}"}
        
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"content": content}
        except UnicodeDecodeError:
            return {"error": f"File is not text-based: {path}"}
        except Exception as e:
            return {"error": f"Read error: {str(e)}"}

class WriteFileTool(DirectTool):
    """Tool for writing to a file"""
    
    def __init__(self, provider: FilesystemToolProvider):
        super().__init__(
            name="write-file",
            description="Write content to a file",
            input_model=FileWrite
        )
        self.provider = provider
    
    def _execute(self, path: str, content: str, create_dirs: bool) -> Dict[str, Any]:
        """Write content to a file"""
        if not self.provider.is_safe_path(path):
            return {"error": "Path is outside root directory"}
        
        full_path = os.path.join(self.provider.root_path, path)
        
        try:
            if create_dirs:
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            return {"success": True, "message": f"Successfully wrote to {path}"}
        except Exception as e:
            return {"error": f"Failed to write file {path}: {str(e)}"}

class ListFilesTool(DirectTool):
    """Tool for listing files in a directory"""
    
    def __init__(self, provider: FilesystemToolProvider):
        super().__init__(
            name="list-files",
            description="List files and directories in a given directory",
            input_model=ListFiles
        )
        self.provider = provider
    
    def _execute(self, directory: str) -> Dict[str, Any]:
        """List files in a directory"""
        if not self.provider.is_safe_path(directory):
            return {"error": "Directory is outside root path"}
        
        abs_dir = os.path.abspath(os.path.join(self.provider.root_path, directory))
        
        if not os.path.exists(abs_dir) or not os.path.isdir(abs_dir):
            return {"error": f"Directory not found: {directory}"}
        
        files = []
        directories = []
        
        for entry in os.listdir(abs_dir):
            full_path = os.path.join(abs_dir, entry)
            
            if self.provider.is_ignored(full_path):
                continue
            
            if os.path.isdir(full_path):
                directories.append(f"{entry}/")
            else:
                files.append(entry)
        
        return {
            "directory": directory,
            "directories": sorted(directories),
            "files": sorted(files)
        }

class DeleteFileTool(DirectTool):
    """Tool for deleting a file or directory"""
    
    def __init__(self, provider: FilesystemToolProvider):
        super().__init__(
            name="delete-file",
            description="Delete a file or directory",
            input_model=FileDelete
        )
        self.provider = provider
    
    def _execute(self, path: str, recursive: bool) -> Dict[str, Any]:
        """Delete a file or directory"""
        if not self.provider.is_safe_path(path):
            return {"error": "Path is outside root directory"}
        
        full_path = os.path.join(self.provider.root_path, path)
        
        if not os.path.exists(full_path):
            return {"error": f"Path not found: {path}"}
        
        try:
            if os.path.isdir(full_path):
                if recursive:
                    import shutil
                    shutil.rmtree(full_path)
                else:
                    os.rmdir(full_path)
            else:
                os.remove(full_path)
            
            return {"success": True, "message": f"Successfully deleted {path}"}
        except Exception as e:
            return {"error": f"Failed to delete {path}: {str(e)}"}

# ---- SQLite Tool Provider ----

class SQLiteToolProvider(ToolProvider):
    """Provider for SQLite-related tools"""
    
    def __init__(self, db_path: str):
        super().__init__("sqlite")
        self.db_path = os.path.abspath(db_path)
        logger.info(f"Initializing SQLiteToolProvider with database: {self.db_path}")
        
        # Initialize database
        self._init_database()
        
        # Register tools
        self._register_tools()
        
        # Storage for business insights
        self.insights = []
    
    def _init_database(self) -> None:
        """Initialize the SQLite database"""
        # We don't need to initialize the database here anymore
        # since we're using the global database connection from db.py
        # The database is already initialized and connected in db.py
        pass
    
    def _register_tools(self) -> None:
        """Register all SQLite tools"""
        self.register_tool(ReadQueryTool(self))
        self.register_tool(WriteQueryTool(self))
        self.register_tool(CreateTableTool(self))
        self.register_tool(ListTablesTool(self))
        self.register_tool(DescribeTableTool(self))
        self.register_tool(AppendInsightTool(self))
    
    def _execute_query(self, query: str, params=None) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results"""
        try:
            # Use the global database connection
            # Convert the query to work with peewee's SqliteDatabase
            cursor = db.execute_sql(query, params)
            
            if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER')):
                affected = cursor.rowcount
                return [{"affected_rows": affected}]
            
            # Fetch results
            results = []
            for row in cursor.fetchall():
                # Convert sqlite3.Row to dict
                row_dict = {}
                for idx, col in enumerate(cursor.description):
                    row_dict[col[0]] = row[idx]
                results.append(row_dict)
            
            return results
        except Exception as e:
            logger.error(f"Database error executing query: {str(e)}")
            raise

# ---- SQLite Tools ----

class ReadQueryTool(DirectTool):
    """Tool for executing a SELECT query"""
    
    def __init__(self, provider: SQLiteToolProvider):
        super().__init__(
            name="read-query",
            description="Execute a SELECT query on the SQLite database",
            input_model=SqlQuery
        )
        self.provider = provider
    
    def _execute(self, query: str) -> Dict[str, Any]:
        """Execute a SELECT query"""
        if not query.strip().upper().startswith("SELECT"):
            return {"error": "Only SELECT queries are allowed for read-query"}
        
        try:
            results = self.provider._execute_query(query)
            return {"results": results}
        except Exception as e:
            return {"error": f"Database error: {str(e)}"}

class WriteQueryTool(DirectTool):
    """Tool for executing a write query (INSERT, UPDATE, DELETE)"""
    
    def __init__(self, provider: SQLiteToolProvider):
        super().__init__(
            name="write-query",
            description="Execute an INSERT, UPDATE, or DELETE query on the SQLite database",
            input_model=SqlQuery
        )
        self.provider = provider
    
    def _execute(self, query: str) -> Dict[str, Any]:
        """Execute a write query"""
        if query.strip().upper().startswith("SELECT"):
            return {"error": "SELECT queries are not allowed for write-query"}
        
        try:
            results = self.provider._execute_query(query)
            return {"results": results}
        except Exception as e:
            return {"error": f"Database error: {str(e)}"}

class CreateTableTool(DirectTool):
    """Tool for creating a table"""
    
    def __init__(self, provider: SQLiteToolProvider):
        super().__init__(
            name="create-table",
            description="Create a new table in the SQLite database",
            input_model=SqlCreateTable
        )
        self.provider = provider
    
    def _execute(self, query: str) -> Dict[str, Any]:
        """Create a table"""
        if not query.strip().upper().startswith("CREATE TABLE"):
            return {"error": "Only CREATE TABLE statements are allowed"}
        
        try:
            self.provider._execute_query(query)
            return {"success": True, "message": "Table created successfully"}
        except Exception as e:
            return {"error": f"Database error: {str(e)}"}

class ListTablesTool(DirectTool):
    """Tool for listing tables in the database"""
    
    def __init__(self, provider: SQLiteToolProvider):
        super().__init__(
            name="list-tables",
            description="List all tables in the SQLite database",
            input_model=EmptyModel
        )
        self.provider = provider
    
    def _execute(self) -> Dict[str, Any]:
        """List all tables"""
        try:
            results = self.provider._execute_query(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row["name"] for row in results]
            return {"tables": tables}
        except Exception as e:
            return {"error": f"Database error: {str(e)}"}

class DescribeTableTool(DirectTool):
    """Tool for describing a table's schema"""
    
    def __init__(self, provider: SQLiteToolProvider):
        super().__init__(
            name="describe-table",
            description="Get the schema information for a specific table",
            input_model=SqlDescribeTable
        )
        self.provider = provider
    
    def _execute(self, table_name: str) -> Dict[str, Any]:
        """Describe a table"""
        try:
            results = self.provider._execute_query(f"PRAGMA table_info({table_name})")
            return {"schema": results}
        except Exception as e:
            return {"error": f"Database error: {str(e)}"}

class AppendInsightTool(DirectTool):
    """Tool for adding a business insight to the memo"""
    
    def __init__(self, provider: SQLiteToolProvider):
        super().__init__(
            name="append-insight",
            description="Add a business insight to the memo",
            input_model=AppendInsight
        )
        self.provider = provider
    
    def _execute(self, insight: str) -> Dict[str, Any]:
        """Add an insight to the memo"""
        self.provider.insights.append(insight)
        return {"success": True, "message": "Insight added to memo"}

# ---- Git Tool Provider ----

class GitToolProvider(ToolProvider):
    """Provider for git-related tools"""
    
    def __init__(self, root_path: str = "."):
        super().__init__("git")
        self.root_path = os.path.abspath(root_path)
        logger.info(f"Initializing GitToolProvider with root path: {self.root_path}")
        
        # Register tools
        self._register_tools()
    
    def _register_tools(self) -> None:
        """Register all git tools"""
        self.register_tool(GitStatusTool(self))
        self.register_tool(GitAddTool(self))
        self.register_tool(GitCommitTool(self))
        self.register_tool(GitBranchTool(self))
        self.register_tool(GitLogTool(self))
        self.register_tool(GitDiffTool(self))
    
    def is_git_repository(self, path: str) -> bool:
        """Check if a path is a git repository"""
        abs_path = os.path.abspath(path)
        return os.path.exists(os.path.join(abs_path, '.git'))
    
    def is_safe_path(self, path: str) -> bool:
        """Check if a path is within the root directory"""
        abs_path = os.path.abspath(path)
        return abs_path.startswith(self.root_path)
    
    def execute_git_command(self, command: List[str], cwd: str) -> Dict[str, Any]:
        """Execute a git command safely"""
        if not self.is_safe_path(cwd):
            return {"error": "Path is outside root directory"}
        
        if not self.is_git_repository(cwd):
            return {"error": "Not a git repository"}
        
        try:
            # Execute the git command with timeout
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                check=False  # Don't raise exception on non-zero exit
            )
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip()
            }
        
        except subprocess.TimeoutExpired:
            return {"error": "Git command timed out"}
        except Exception as e:
            return {"error": f"Failed to execute git command: {str(e)}"}

# ---- Git Tools ----

class GitStatusTool(DirectTool):
    """Tool for git status command"""
    
    def __init__(self, provider: GitToolProvider):
        super().__init__(
            name="status",
            description="Show the working tree status",
            input_model=GitStatus
        )
        self.provider = provider
    
    def _execute(self, repository_path: str) -> Dict[str, Any]:
        """Execute git status"""
        result = self.provider.execute_git_command(
            ["git", "status", "--porcelain"],
            repository_path
        )
        
        if "error" in result:
            return result
        
        if not result["success"]:
            return {"error": f"Git status failed: {result['stderr']}"}
        
        # Parse the porcelain output for better formatting
        status_lines = result["stdout"].split('\n') if result["stdout"] else []
        files = []
        for line in status_lines:
            if line.strip():
                status = line[:2]
                filename = line[3:]
                files.append({"status": status, "file": filename})
        
        return {
            "success": True,
            "files": files,
            "raw_output": result["stdout"]
        }

class GitAddTool(DirectTool):
    """Tool for git add command"""
    
    def __init__(self, provider: GitToolProvider):
        super().__init__(
            name="add",
            description="Add file contents to the index",
            input_model=GitAdd
        )
        self.provider = provider
    
    def _execute(self, repository_path: str, files: str) -> Dict[str, Any]:
        """Execute git add"""
        # Sanitize the files parameter
        if files == ".":
            git_files = ["."]
        else:
            # Split files by spaces and validate each one
            git_files = shlex.split(files)
        
        command = ["git", "add"] + git_files
        result = self.provider.execute_git_command(command, repository_path)
        
        if "error" in result:
            return result
        
        if not result["success"]:
            return {"error": f"Git add failed: {result['stderr']}"}
        
        return {
            "success": True,
            "message": f"Added files: {files}",
            "output": result["stdout"]
        }

class GitCommitTool(DirectTool):
    """Tool for git commit command"""
    
    def __init__(self, provider: GitToolProvider):
        super().__init__(
            name="commit",
            description="Record changes to the repository",
            input_model=GitCommit
        )
        self.provider = provider
    
    def _execute(self, repository_path: str, message: str, add_all: bool = False) -> Dict[str, Any]:
        """Execute git commit"""
        # Optionally add all files first
        if add_all:
            add_result = self.provider.execute_git_command(
                ["git", "add", "-A"],
                repository_path
            )
            if "error" in add_result or not add_result["success"]:
                return {"error": f"Failed to add files: {add_result.get('stderr', 'Unknown error')}"}
        
        # Execute the commit
        result = self.provider.execute_git_command(
            ["git", "commit", "-m", message],
            repository_path
        )
        
        if "error" in result:
            return result
        
        if not result["success"]:
            return {"error": f"Git commit failed: {result['stderr']}"}
        
        return {
            "success": True,
            "message": "Commit successful",
            "output": result["stdout"]
        }

class GitBranchTool(DirectTool):
    """Tool for git branch operations"""
    
    def __init__(self, provider: GitToolProvider):
        super().__init__(
            name="branch",
            description="List, create, switch, or delete branches",
            input_model=GitBranch
        )
        self.provider = provider
    
    def _execute(self, repository_path: str, action: str = "list", branch_name: str = "") -> Dict[str, Any]:
        """Execute git branch operations"""
        if action == "list":
            command = ["git", "branch", "-a"]
        elif action == "create":
            if not branch_name:
                return {"error": "Branch name required for create action"}
            command = ["git", "branch", branch_name]
        elif action == "switch":
            if not branch_name:
                return {"error": "Branch name required for switch action"}
            command = ["git", "checkout", branch_name]
        elif action == "delete":
            if not branch_name:
                return {"error": "Branch name required for delete action"}
            command = ["git", "branch", "-d", branch_name]
        else:
            return {"error": f"Unknown action: {action}. Use 'list', 'create', 'switch', or 'delete'"}
        
        result = self.provider.execute_git_command(command, repository_path)
        
        if "error" in result:
            return result
        
        if not result["success"]:
            return {"error": f"Git branch {action} failed: {result['stderr']}"}
        
        return {
            "success": True,
            "action": action,
            "output": result["stdout"]
        }

class GitLogTool(DirectTool):
    """Tool for git log command"""
    
    def __init__(self, provider: GitToolProvider):
        super().__init__(
            name="log",
            description="Show commit logs",
            input_model=GitLog
        )
        self.provider = provider
    
    def _execute(self, repository_path: str, max_count: int = 10, oneline: bool = True) -> Dict[str, Any]:
        """Execute git log"""
        command = ["git", "log", f"--max-count={max_count}"]
        if oneline:
            command.append("--oneline")
        
        result = self.provider.execute_git_command(command, repository_path)
        
        if "error" in result:
            return result
        
        if not result["success"]:
            return {"error": f"Git log failed: {result['stderr']}"}
        
        return {
            "success": True,
            "commits": result["stdout"].split('\n') if result["stdout"] else [],
            "raw_output": result["stdout"]
        }

class GitDiffTool(DirectTool):
    """Tool for git diff command"""
    
    def __init__(self, provider: GitToolProvider):
        super().__init__(
            name="diff",
            description="Show changes between commits, commit and working tree, etc",
            input_model=GitDiff
        )
        self.provider = provider
    
    def _execute(self, repository_path: str, staged: bool = False, file_path: str = "") -> Dict[str, Any]:
        """Execute git diff"""
        command = ["git", "diff"]
        if staged:
            command.append("--cached")
        if file_path:
            command.append(file_path)
        
        result = self.provider.execute_git_command(command, repository_path)
        
        if "error" in result:
            return result
        
        if not result["success"]:
            return {"error": f"Git diff failed: {result['stderr']}"}
        
        return {
            "success": True,
            "diff": result["stdout"],
            "has_changes": bool(result["stdout"].strip())
        }

# ---- Direct Multiplexer ----

class DirectMultiplexer:
    """A multiplexer that directly calls tools without using stdio"""
    
    def __init__(self):
        self.providers = []
        self.all_tools = {}
        logger.info("Initializing DirectMultiplexer")
    
    def add_provider(self, provider: ToolProvider) -> None:
        """Add a tool provider to the multiplexer"""
        self.providers.append(provider)
        self.all_tools.update(provider.get_tools())
        logger.info(f"Added provider '{provider.prefix}' with {len(provider.get_tools())} tools")
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get definitions of all available tools"""
        return [tool.get_definition() for tool in self.all_tools.values()]
    
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with the given arguments"""
        if tool_name not in self.all_tools:
            logger.error(f"Unknown tool: {tool_name}")
            return {"error": f"Unknown tool: {tool_name}"}
        
        logger.info(f"Executing tool: {tool_name}")
        try:
            return self.all_tools[tool_name].execute(**arguments)
        except Exception as e:
            logger.error(f"Error executing {tool_name}: {str(e)}")
            return {"error": f"Tool execution error: {str(e)}"}
