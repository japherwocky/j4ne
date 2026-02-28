# J4NE - Agent Documentation

> A modern chat bot with CLI and web interfaces for IRC and Slack platforms. Built with Python, Starlette, and Typer.

## Project Overview

**J4NE** is an AI-assisted chat bot that combines:
- **CLI Interface**: Interactive command-line chat with rich terminal output
- **Web Interface**: Starlette-based web server for HTTP interactions  
- **Multi-Platform Support**: IRC and Slack integrations
- **Tool Ecosystem**: File operations, Git, SQLite, LSP code intelligence, MCP integration

## Quick Start

```bash
# Interactive chat
python j4ne.py chat

# Start web server (with IRC/Slack clients)
python j4ne.py web

# Send a greeting
python j4ne.py greet "Your Name"

# With verbose logging
python j4ne.py chat --verbose
```

## Project Structure

```
.
├── j4ne.py              # Main entry point (CLI + web server)
├── db.py                # Database utilities
├── mcp_config.yaml      # MCP server configuration
│
├── api/                 # API routes (minimal)
├── chatters/            # Chat loop and CLI interface
│   ├── cli.py          # Interactive chat implementation
│   └── bot_commands.py # Bot command handlers
│
├── commands/            # Command processing
│   ├── handler.py      # Command routing
│   ├── core.py         # Core command logic
│   └── models.py       # Command models
│
├── networks/            # Platform integrations
│   ├── irc.py          # IRC client
│   ├── slack.py        # Slack client (Socket Mode)
│   └── slack_http.py   # Slack HTTP/webhook mode
│
├── tools/               # Tool implementations (MCP-style)
│   ├── read_tool.py    # File reading
│   ├── write_tool.py   # File writing
│   ├── edit_tool.py    # String find/replace
│   ├── glob_tool.py    # Pattern matching
│   ├── ls_tool.py      # Directory listing
│   ├── grep_tool.py    # Content search
│   ├── bash_tool.py    # Shell execution
│   ├── multiedit_tool.py    # Multi-file edits
│   ├── patch_tool.py   # Unified diff patches
│   │
│   ├── git_tools/      # Git operations (via direct_tools.py)
│   ├── database_tools/ # SQLite operations (via direct_tools.py)
│   │
│   ├── lsp_client.py   # LSP protocol handler
│   ├── lsp_tool.py    # Language Server Protocol tools
│   ├── python_lsp_server.py # Python LSP wrapper (pyright)
│   │
│   ├── mcp_client.py   # MCP protocol client
│   ├── mcp_registry.py # MCP server registry
│   ├── mcp_call_tool.py # Generic MCP tool caller
│   ├── codesearch_tool.py  # Exa code search wrapper
│   ├── websearch_tool.py   # Exa web search wrapper
│   └── github_tool.py  # GitHub API integration
│
└── tests/              # Unit tests
```

## Key Entry Points

### j4ne.py
Main CLI application using Typer. Provides commands:
- `chat` - Interactive CLI chat (default)
- `greet <name>` - Send a greeting
- `web` - Start web server with network clients

### chatters/cli.py
The `EmCeePee` class implements the main chat loop. Handles user input and bot responses.

### networks/
Platform clients:
- **IRC**: `IRCClient` - Connects to IRC servers
- **Slack**: `SlackClient` - Supports both Socket Mode (dev) and HTTP (prod)

## Tools System

Tools are implemented following the MCP (Model Context Protocol) pattern. Each tool is a class with a `run()` method.

### File Tools (in tools/)
| Tool | Purpose |
|------|---------|
| `ReadTool` | Read file contents with smart truncation |
| `WriteTool` | Create/overwrite files |
| `EditTool` | String find/replace with diff preview |
| `GlobTool` | Pattern matching for files |
| `LsTool` | Tree-like directory listing |
| `GrepTool` | Content search (via ripgrep) |
| `BashTool` | Shell command execution |
| `MultiEditTool` | Batch edits to single file |
| `PatchTool` | Apply unified diff patches |

### Database Tools
Available via `direct_tools.py`:
- `ReadQueryTool` - SELECT queries
- `WriteQueryTool` - INSERT/UPDATE/DELETE
- `CreateTableTool` - DDL operations
- `ListTablesTool` - Schema inspection
- `DescribeTableTool` - Table details

### Git Tools
Available via `direct_tools.py`:
- `GitStatusTool`, `GitAddTool`, `GitCommitTool`
- `GitBranchTool`, `GitLogTool`, `GitDiffTool`

### Code Intelligence
- **LSP Tools** (`lsp_tool.py`): goToDefinition, findReferences, hover, documentSymbol, workspaceSymbol
- **Python LSP**: Uses pyright for Python code intelligence

### Web/MCP Tools
- **WebSearch**: Exa-powered web search
- **CodeSearch**: Exa-powered code search
- **GitHub**: Repository exploration and file access

## Configuration

### Environment Variables
```bash
# Slack (Socket Mode)
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...

# Slack (HTTP/Production)
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...

# Slack mode (auto/socket/http)
SLACK_MODE=auto

# IRC
IRC_SERVER=irc.libera.chat
IRC_NICK=j4ne-bot
IRC_CHANNEL=#mychannel
```

### mcp_config.yaml
MCP server configuration for external tools (Exa, custom servers).

## Development Notes

### Adding a New Tool

1. Create tool class in `tools/` inheriting from base pattern
2. Implement `run(**kwargs)` method
3. Register in `tools/__init__.py` if exposed
4. Add tests in `tests/`

### Logging
- Logs written to `logs/j4ne.log`
- Rotating handler (10MB, 5 files)
- Use `setup_logging(verbose=True, console_output=True)` for web server

### Testing
```bash
# Run tests
pytest tests/ -v

# Specific tool
pytest tests/test_read_tool.py -v
```

## Architecture Patterns

### Async/Await
The project uses Python's async throughout:
- `asyncio.run()` for entry points
- `async with` for context managers
- `await` for I/O operations

### Tool Interface
```python
class ToolName:
    def run(self, **kwargs) -> str:
        """Execute the tool with given parameters."""
        # Implementation
        return result
```

### Client Pattern
Network clients follow:
```python
class PlatformClient:
    async def connect(self) -> bool:
        """Establish connection."""
        
    async def disconnect(self):
        """Clean up resources."""
```

## Dependencies

- **typer** - CLI framework
- **starlette** - Web framework
- **uvicorn** - ASGI server
- **rich** - Terminal output
- **mcp** - MCP protocol
- **openai** - LLM integration
- **pathspec** - Path matching

## License

MIT License
