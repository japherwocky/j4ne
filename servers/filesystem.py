import argparse
import asyncio
import logging
from typing import Annotated, Optional, List
import os
import pathspec
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.types as types
import mcp.server.stdio
from pydantic import BaseModel, Field
from mcp.shared.exceptions import McpError

DEFAULT_IGNORE_PATTERNS = [
    ".git",
    "__pycache__",
    "*.pyc",
    ".venv",
    "venv",
    ".env",
    ".idea",
    ".vscode",
    "*.egg-info",
    "dist",
    "build",
    ".pytest_cache",
    ".coverage",
    "htmlcov",
    ".DS_Store",  # macOS
    "Thumbs.db",  # Windows
]

class FileAccess(BaseModel):
    path: Annotated[str, Field(description="Path to the file")]
    pattern: Annotated[
        str,
        Field(default="*", description="File pattern for search (e.g., *.py for Python files)")
    ]

class FileSearch(BaseModel):
    query: Annotated[str, Field(description="Text to search for")]
    file_pattern: Annotated[
        str,
        Field(default="*", description="File pattern to filter search (e.g., *.py for Python files)")
    ]

class FileWrite(BaseModel):
    path: Annotated[str, Field(description="Path to the file")]
    content: Annotated[str, Field(description="Content to write")]
    create_dirs: Annotated[bool, Field(default=False, description="Create parent directories if they don't exist")]

class FileDelete(BaseModel):
    path: Annotated[str, Field(description="Path to delete")]
    recursive: Annotated[bool, Field(default=False, description="Recursively delete directories")]

class ListFiles(BaseModel):
    directory: Annotated[str, Field(default='.', description='Directory to list files in')]

class ReadFile(BaseModel):
    path: Annotated[str, Field(description='Path to the file to read')]

class FilesystemServer:
    def __init__(self, root_path: str, custom_ignore_patterns: Optional[list[str]] = None):
        self.root_path = os.path.abspath(root_path)
        if not os.path.exists(self.root_path):
            raise ValueError(f"Directory does not exist: {self.root_path}")

        gitignore_path = os.path.join(self.root_path, ".gitignore")
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r") as f:
                patterns = f.readlines()
        else:
            patterns = DEFAULT_IGNORE_PATTERNS.copy()

        if custom_ignore_patterns:
            patterns.extend(custom_ignore_patterns)

        self.ignore_patterns = pathspec.PathSpec.from_lines("gitwildmatch", patterns)

    def is_safe_path(self, path: str) -> bool:
        abs_path = os.path.abspath(os.path.join(self.root_path, path))
        return abs_path.startswith(self.root_path)

    def is_ignored(self, path: str) -> bool:
        if not self.ignore_patterns:
            return False
        rel = os.path.relpath(path, self.root_path)
        return self.ignore_patterns.match_file(rel)

    def get_mime_type(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        mime_types = {
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".py": "text/x-python",
            ".js": "text/javascript",
            ".json": "application/json",
            ".html": "text/html",
            ".css": "text/css",
            ".csv": "text/csv",
            ".xml": "application/xml",
            ".yaml": "application/x-yaml",
            ".yml": "application/x-yaml",
        }
        return mime_types.get(ext, "application/octet-stream")
    
    # Tool: List Project Structure
    async def tool_list_project_structure(self, args: ListFiles) -> List[types.TextContent]:
        """
        Recursively list the folder structure of the project.
        """
        start_directory = args.directory
        abs_start_directory = os.path.abspath(os.path.join(self.root_path, start_directory))
        
        if not abs_start_directory.startswith(self.root_path):
            raise McpError(types.ErrorData(code=types.INVALID_PARAMS, message="Directory is outside root directory"))
        if not os.path.exists(abs_start_directory) or not os.path.isdir(abs_start_directory):
            raise McpError(types.ErrorData(code=types.INVALID_PARAMS, message=f"Directory not found: {start_directory}"))

        def gather_structure(directory, prefix=""):
            output = []
            entries = sorted(os.listdir(directory))  # Sorted to have consistent results
            for entry in entries:
                abs_path = os.path.join(directory, entry)
                
                if self.is_ignored(abs_path):
                    continue

                if os.path.isdir(abs_path):
                    output.append(f"{prefix}{entry}/")  # Add trailing slash for directories
                    output.extend(gather_structure(abs_path, prefix=prefix + "    "))  # Indent child entries
                else:
                    output.append(f"{prefix}{entry}")
            return output

        # Begin gathering structure
        complete_structure = f"Project Directory Structure from {start_directory}:\n"
        structure_lines = gather_structure(abs_start_directory)
        # Join results for hierarchy
        complete_project_tree = complete_structure + "\n".join(structure_lines)
        
        if not structure_lines:
            complete_project_tree += "[Empty Project Directory]"
        
        return [
            types.TextContent(
                type="text",
                text=complete_project_tree
            )
        ]

    async def tool_list_files(self, args: ListFiles) -> List[types.TextContent]:
        directory = args.directory
        abs_dir = os.path.abspath(os.path.join(self.root_path, directory))
        if not abs_dir.startswith(self.root_path):
            raise McpError(types.ErrorData(code=types.INVALID_PARAMS, message="Directory is outside root path"))
        if not os.path.exists(abs_dir) or not os.path.isdir(abs_dir):
            raise McpError(types.ErrorData(code=types.INVALID_PARAMS, message=f"Directory not found: {directory}"))
        files = []
        for entry in os.listdir(abs_dir):
            full_path = os.path.join(abs_dir, entry)
            if self.is_ignored(full_path):
                continue
            item_type = "dir" if os.path.isdir(full_path) else "file"
            files.append(f"{entry}/" if item_type == "dir" else entry)
        files.sort()
        return [
            types.TextContent(
                type="text",
                text=f"Files in {directory}:\n" + ("\n".join(files) if files else "[Empty]"),
            )
        ]

    async def tool_read_file(self, args: ReadFile) -> List[types.TextContent]:
        if not self.is_safe_path(args.path):
            raise McpError(types.ErrorData(code=types.INVALID_PARAMS, message="Path is outside root directory"))
        full_path = os.path.join(self.root_path, args.path)
        if not os.path.isfile(full_path):
            raise McpError(types.ErrorData(code=types.INVALID_PARAMS, message="File not found"))
        if self.is_ignored(full_path):
            raise McpError(types.ErrorData(code=types.INVALID_PARAMS, message="File is ignored"))
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                # You may wish to limit output size for huge files!
                content = f.read()
            return [types.TextContent(type="text", text=content)]
        except Exception as e:
            raise McpError(types.ErrorData(code=types.INTERNAL_ERROR, message=f"Read error: {e}"))

    async def read_resource(self, uri: types.AnyUrl) -> str:
        if uri.scheme != "file":
            raise McpError(types.ErrorData(
                code=types.INVALID_PARAMS,
                message="Invalid URI scheme - only file:// URIs are supported"
            ))
        path = str(uri).replace("file://", "", 1)
        if not self.is_safe_path(path):
            raise McpError(types.ErrorData(
                code=types.INVALID_PARAMS, message="Path is outside root directory"
            ))
        full_path = os.path.join(self.root_path, path)
        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            raise McpError(types.ErrorData(
                code=types.INVALID_PARAMS, message="File not found: {}".format(path)
            ))
        if self.is_ignored(full_path):
            raise McpError(types.ErrorData(
                code=types.INVALID_PARAMS,
                message="File is ignored: {}".format(path)
            ))
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            raise McpError(types.ErrorData(
                code=types.INVALID_PARAMS,
                message="File is not text-based: {}".format(path)
            ))
        except IOError as e:
            raise McpError(types.ErrorData(
                code=types.INTERNAL_ERROR,
                message="Failed to read file {}: {}".format(path, str(e))
            ))

    async def tool_search_files(self, args: FileSearch) -> list[types.TextContent]:
        results = []
        for root, _, files in os.walk(self.root_path):
            for file in files:
                full_path = os.path.join(root, file)
                if self.is_ignored(full_path):
                    continue
                if not pathspec.Pattern(args.file_pattern).match_file(file):
                    continue
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if args.query.lower() in content.lower():
                            rel_path = os.path.relpath(full_path, self.root_path)
                            results.append(f"Found in {rel_path}")
                except (UnicodeDecodeError, IOError):
                    continue
        if not results:
            return [types.TextContent(type="text", text="No matches found")]
        return [
            types.TextContent(
                type="text", text="Search results:\n" + "\n".join(results)
            )
        ]

    async def tool_write_file(self, args: FileWrite) -> list[types.TextContent]:
        if not self.is_safe_path(args.path):
            raise McpError(types.ErrorData(
                code=types.INVALID_PARAMS, message="Path is outside root directory"
            ))
        full_path = os.path.join(self.root_path, args.path)
        try:
            if args.create_dirs:
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(args.content)
            return [types.TextContent(type="text", text=f"Successfully wrote to {args.path}")]
        except IOError as e:
            raise McpError(types.ErrorData(
                code=types.INTERNAL_ERROR,
                message=f"Failed to write file {args.path}: {str(e)}",
            ))

    async def tool_delete_file(self, args: FileDelete) -> list[types.TextContent]:
        if not self.is_safe_path(args.path):
            raise McpError(types.ErrorData(
                code=types.INVALID_PARAMS, message="Path is outside root directory"
            ))
        full_path = os.path.join(self.root_path, args.path)
        try:
            if os.path.isdir(full_path):
                if args.recursive:
                    import shutil
                    shutil.rmtree(full_path)
                else:
                    os.rmdir(full_path)
            else:
                os.remove(full_path)
            return [types.TextContent(type="text", text=f"Successfully deleted {args.path}")]
        except IOError as e:
            raise McpError(types.ErrorData(
                code=types.INTERNAL_ERROR,
                message=f"Failed to delete {args.path}: {str(e)}",
            ))

    async def list_tools(self) -> list[types.Tool]:
        return [
            types.Tool(
                name="search-files",
                description="Search for files containing specific text",
                inputSchema=FileSearch.model_json_schema(),
            ),
            types.Tool(
                name="list-files",
                description="List files and directories in a given directory (default: ./)",
                inputSchema=ListFiles.model_json_schema(),
            ),
            types.Tool(
                name="list-project-structure",
                description="Recursively list the folder structure of the entire project directory",
                inputSchema=ListFiles.model_json_schema(),
            ),
            types.Tool(
                name="read-file",
                description="Read the entire contents of a file",
                inputSchema=ReadFile.model_json_schema(),
            ),            
            types.Tool(
                name="write-file",
                description="Write content to a file",
                inputSchema=FileWrite.model_json_schema(),
            ),
            types.Tool(
                name="delete-file",
                description="Delete a file or directory",
                inputSchema=FileDelete.model_json_schema(),
            ),
        ]

    async def call_tool(
        self, name: str, arguments: dict | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        if not arguments:
            raise McpError(types.ErrorData(code=types.INVALID_PARAMS, message="Missing arguments"))
        if name == "list-files":
            args = ListFiles(**arguments)
            return await self.tool_list_files(args)
        elif name == "read-file":
            args = ReadFile(**arguments)
            return await self.tool_read_file(args)
        elif name == "list-project-structure":
            args = ListFiles(**arguments)
            return await self.tool_list_project_structure(args)
        elif name == "search-files":
            try:
                args = FileSearch(**arguments)
            except ValueError as e:
                raise McpError(types.ErrorData(code=types.INVALID_PARAMS, message=str(e)))
            return await self.tool_search_files(args)
        elif name == "write-file":
            try:
                args = FileWrite(**arguments)
            except ValueError as e:
                raise McpError(types.ErrorData(code=types.INVALID_PARAMS, message=str(e)))
            return await self.tool_write_file(args)
        elif name == "delete-file":
            try:
                args = FileDelete(**arguments)
            except ValueError as e:
                raise McpError(types.ErrorData(code=types.INVALID_PARAMS, message=str(e)))
            return await self.tool_delete_file(args)
        raise McpError(types.ErrorData(code=types.INVALID_PARAMS, message=f"Unknown tool: {name}"))
    
    async def list_resources(self):
        return await self.tool_list_files(ListFiles(directory='.'))

    async def read_resource(self, uri: types.AnyUrl):
        # expects uri like file://some/path
        path = str(uri).replace("file://", "", 1)
        return await self.tool_read_file(ReadFile(path=path))


async def serve(root_path: str, custom_ignore_patterns: Optional[list[str]] = None) -> None:
    fs_server = FilesystemServer(root_path, custom_ignore_patterns)
    server = Server("filesystem")

    @server.list_resources()
    async def handle_list_resources():
        return await fs_server.list_resources()

    @server.read_resource()
    async def handle_read_resource(uri: types.AnyUrl):
        return await fs_server.read_resource(uri)

    @server.list_tools()
    async def handle_list_tools():
        return await fs_server.list_tools()

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None):
        return await fs_server.call_tool(name, arguments)

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="filesystem",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python server.py <root_directory>", file=sys.stderr)
        sys.exit(1)
    asyncio.run(serve(sys.argv[1]))