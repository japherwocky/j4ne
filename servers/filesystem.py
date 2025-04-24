from typing import Annotated, Optional
import os
import pathspec
import asyncio
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.shared.exceptions import McpError
import mcp.types as types
import mcp.server.stdio
from pydantic import BaseModel, Field

# Configuration constants
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
    """Parameters for accessing a file."""

    path: Annotated[str, Field(description="Path to the file")]
    pattern: Annotated[
        str,
        Field(
            default="*",
            description="File pattern for search (e.g., *.py for Python files)",
        ),
    ]


class FileSearch(BaseModel):
    """Parameters for searching files."""

    query: Annotated[str, Field(description="Text to search for")]
    file_pattern: Annotated[
        str,
        Field(
            default="*",
            description="File pattern to filter search (e.g., *.py for Python files)",
        ),
    ]


class FileWrite(BaseModel):
    """Parameters for writing to a file."""

    path: Annotated[str, Field(description="Path to the file")]
    content: Annotated[str, Field(description="Content to write")]
    create_dirs: Annotated[
        bool,
        Field(
            default=False, description="Create parent directories if they don't exist"
        ),
    ]


class FileDelete(BaseModel):
    """Parameters for deleting a file or directory."""

    path: Annotated[str, Field(description="Path to delete")]
    recursive: Annotated[
        bool, Field(default=False, description="Recursively delete directories")
    ]


def is_safe_path(root_path: str, path: str) -> bool:
    """Check if a path is safe to access.

    Args:
        root_path: Base directory path.
        path: Path to check.

    Returns:
        True if path is within root directory.
    """
    if not root_path:
        return False

    abs_path = os.path.abspath(os.path.join(root_path, path))
    return abs_path.startswith(root_path)


def is_ignored(
    root_path: str, path: str, ignore_patterns: Optional[pathspec.PathSpec]
) -> bool:
    """Check if path matches ignore patterns.

    Args:
        root_path: Base directory path.
        path: Path to check
        ignore_patterns: PathSpec patterns to check against

    Returns:
        True if path should be ignored
    """
    if not ignore_patterns:
        return False
    relative_path = os.path.relpath(path, root_path)
    return ignore_patterns.match_file(relative_path)


def get_mime_type(file_path: str) -> str:
    """Get MIME type based on file extension.

    Args:
        file_path: Path to the file

    Returns:
        MIME type string
    """
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


async def serve(
    root_path: str, custom_ignore_patterns: Optional[list[str]] = None
) -> None:
    """Run the filesystem MCP server.

    Args:
        root_path: Base directory to serve files from
        custom_ignore_patterns: Optional list of patterns to ignore
    """
    if not os.path.exists(root_path):
        raise ValueError(f"Directory does not exist: {root_path}")

    root_path = os.path.abspath(root_path)
    ignore_patterns = None

    # Initialize ignore patterns
    gitignore_path = os.path.join(root_path, ".gitignore")
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            patterns = f.readlines()
    else:
        patterns = DEFAULT_IGNORE_PATTERNS

    if custom_ignore_patterns:
        patterns.extend(custom_ignore_patterns)

    ignore_patterns = pathspec.PathSpec.from_lines("gitwildmatch", patterns)

    server = Server("filesystem")

    @server.list_resources()
    async def handle_list_resources() -> list[types.Resource]:
        """List all files in the root directory."""
        resources = []

        for root, _, files in os.walk(root_path):
            for file in files:
                full_path = os.path.join(root, file)

                if is_ignored(root_path, full_path, ignore_patterns):
                    continue

                rel_path = os.path.relpath(full_path, root_path)
                uri = f"file://{rel_path}"

                resources.append(
                    types.Resource(
                        uri=uri,
                        name=rel_path,
                        description=f"File: {rel_path}",
                        mimeType=get_mime_type(full_path),
                    )
                )

        return resources

    @server.read_resource()
    async def handle_read_resource(uri: types.AnyUrl) -> str:
        """Read contents of a specific file.

        Args:
            uri: The URI of the file to read

        Returns:
            The contents of the file as a string

        Raises:
            McpError: If file access fails
        """
        if uri.scheme != "file":
            raise McpError(
                types.ErrorData(
                    code=types.INVALID_PARAMS,
                    message="Invalid URI scheme - only file:// URIs are supported",
                )
            )

        path = str(uri).replace("file://", "", 1)

        if not is_safe_path(root_path, path):
            raise McpError(
                types.ErrorData(
                    code=types.INVALID_PARAMS, message="Path is outside root directory"
                )
            )

        full_path = os.path.join(root_path, path)

        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            raise McpError(
                types.ErrorData(
                    code=types.INVALID_PARAMS, message="File not found: {}".format(path)
                )
            )

        if is_ignored(root_path, full_path, ignore_patterns):
            raise McpError(
                types.ErrorData(
                    code=types.INVALID_PARAMS,
                    message="File is ignored: {}".format(path),
                )
            )

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            raise McpError(
                types.ErrorData(
                    code=types.INVALID_PARAMS,
                    message="File is not text-based: {}".format(path),
                )
            )
        except IOError as e:
            raise McpError(
                types.ErrorData(
                    code=types.INTERNAL_ERROR,
                    message="Failed to read file {}: {}".format(path, str(e)),
                )
            )

    @server.list_prompts()
    async def handle_list_prompts() -> list[types.Prompt]:
        """List available prompts."""
        return [
            types.Prompt(
                name="analyze-file",
                description="Get a summary analysis of a file's contents",
                arguments=[
                    types.PromptArgument(
                        name="path",
                        description="Path to the file to analyze",
                        required=True,
                    )
                ],
            )
        ]

    @server.get_prompt()
    async def handle_get_prompt(
        name: str, arguments: dict[str, str] | None
    ) -> types.GetPromptResult:
        """Get a specific prompt template.

        Args:
            name: Name of the prompt to retrieve
            arguments: Optional arguments for the prompt

        Returns:
            The prompt template with arguments filled in

        Raises:
            McpError: If prompt or arguments are invalid
        """
        if name != "analyze-file":
            raise McpError(
                types.ErrorData(
                    code=types.INVALID_PARAMS, message="Unknown prompt: {}".format(name)
                )
            )

        if not arguments or "path" not in arguments:
            raise McpError(
                types.ErrorData(
                    code=types.INVALID_PARAMS, message="Path argument is required"
                )
            )

        path = arguments["path"]
        if not is_safe_path(root_path, path):
            raise McpError(
                types.ErrorData(
                    code=types.INVALID_PARAMS, message="Path is outside root directory"
                )
            )

        full_path = os.path.join(root_path, path)
        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            raise McpError(
                types.ErrorData(
                    code=types.INVALID_PARAMS, message=f"File not found: {path}"
                )
            )

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            return types.GetPromptResult(
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(
                            type="text",
                            text=f"Please analyze this file ({path}):\n\n{content}",
                        ),
                    )
                ]
            )
        except UnicodeDecodeError:
            raise McpError(
                types.ErrorData(
                    code=types.INVALID_PARAMS, message=f"File is not text-based:{path}"
                )
            )
        except IOError:
            raise McpError(
                types.ErrorData(
                    code=types.INTERNAL_ERROR,
                    message="Failed to read file {path}: {str(e)}",
                )
            )

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """List available tools."""
        return [
            types.Tool(
                name="search-files",
                description="Search for files containing specific text",
                inputSchema=FileSearch.model_json_schema(),
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

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handle tool execution."""
        if not arguments:
            raise McpError(
                types.ErrorData(code=types.INVALID_PARAMS, message="Missing arguments")
            )

        if name == "search-files":
            try:
                args = FileSearch(**arguments)
            except ValueError as e:
                raise McpError(
                    types.ErrorData(code=types.INVALID_PARAMS, message=str(e))
                )

            results = []

            for root, _, files in os.walk(root_path):
                for file in files:
                    full_path = os.path.join(root, file)

                    if is_ignored(root_path, full_path, ignore_patterns):
                        continue

                    if not pathspec.Pattern(args.file_pattern).match_file(file):
                        continue

                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            if args.query.lower() in content.lower():
                                rel_path = os.path.relpath(full_path, root_path)
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

        elif name == "write-file":
            try:
                args = FileWrite(**arguments)
            except ValueError as e:
                raise McpError(
                    types.ErrorData(code=types.INVALID_PARAMS, message=str(e))
                )

            if not is_safe_path(root_path, args.path):
                raise McpError(
                    types.ErrorData(
                        code=types.INVALID_PARAMS,
                        message="Path is outside root directory",
                    )
                )

            full_path = os.path.join(root_path, args.path)

            try:
                if args.create_dirs:
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)

                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(args.content)

                return [
                    types.TextContent(
                        type="text", text=f"Successfully wrote to {args.path}"
                    )
                ]
            except IOError as e:
                raise McpError(
                    types.ErrorData(
                        code=types.INTERNAL_ERROR,
                        message=f"Failed to write file {args.path}: {str(e)}",
                    )
                )

        elif name == "delete-file":
            try:
                args = FileDelete(**arguments)
            except ValueError as e:
                raise McpError(
                    types.ErrorData(code=types.INVALID_PARAMS, message=str(e))
                )

            if not is_safe_path(root_path, args.path):
                raise McpError(
                    types.ErrorData(
                        code=types.INVALID_PARAMS,
                        message="Path is outside root directory",
                    )
                )

            full_path = os.path.join(root_path, args.path)

            try:
                if os.path.isdir(full_path):
                    if args.recursive:
                        import shutil

                        shutil.rmtree(full_path)
                    else:
                        os.rmdir(full_path)  # Only removes empty directories
                else:
                    os.remove(full_path)

                return [
                    types.TextContent(
                        type="text", text=f"Successfully deleted {args.path}"
                    )
                ]
            except IOError as e:
                raise McpError(
                    types.ErrorData(
                        code=types.INTERNAL_ERROR,
                        message=f"Failed to delete {args.path}: {str(e)}",
                    )
                )

        raise McpError(
            types.ErrorData(code=types.INVALID_PARAMS, message=f"Unknown tool: {name}")
        )

    # Run the server
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