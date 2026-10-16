# J4NE - Agent Documentation

> A modern chat bot with CLI and web interfaces for IRC and Slack platforms. Built with Python, Starlette, and Typer.

## Roadmap and issue tracking

Work is tracked on the **j4ne** board (board `22`) at
https://pkanban.pearachute.com, not in this repo. Columns: `92` To Do,
`93` In Progress, `94` For Review, `95` Done. Check the board before starting,
and file a card for anything worth remembering after the session ends.

The board is driven by our own CLI, `pkanban`, pinned in `requirements.txt`
(nothing imports it; it is there so the command exists wherever this is
installed). Agents with the pkanban MCP tools can use those instead.

```bash
pkanban board get 22                       # columns and card ids
pkanban card get 983                       # a card's full description
pkanban card create 92 "Title" -D body.md  # body from a file, not the shell
pkanban card move 983 -c 95                # finished: move it to Done
pkanban search irc                         # every board, titles and bodies
```

Conventions, shared with wolverine and pearachute (their AGENTS.md has the
Windows details):

- Pass card bodies with `-D <file>`. PowerShell re-splits double quotes inside
  an argument, and Git Bash rewrites a leading `/`.
- Column ids are global: `card move` to another board's column id moves the
  card onto that board.
- Finished work moves to Done; do not delete cards. Card ids are stable and
  worth citing in commit messages, as `(card #983)`.

## Project Overview

**J4NE** is an AI-assisted chat bot that combines:
- **CLI Interface**: Interactive command-line chat with rich terminal output
- **Web Interface**: Starlette-based web server for HTTP interactions  
- **Multi-Platform Support**: IRC and Slack integrations
- **Tool Ecosystem**: File operations, Git, SQLite, web search, GitHub (see [Tools System](#tools-system))

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
├── proactive.py         # Proactive agent loop (reads SOUL.md on a timer)
├── memory.py            # Conversation archive and memories (memory.db)
│
├── tools/
│   ├── direct_client.py # The LLM loop, tool access per context, OpenCode settings
│   ├── direct_tools.py  # Live tools: filesystem, SQLite, git, slack_send_message
│   ├── web_search_tool.py # Live: web_search (Serper)
│   ├── github_tool.py   # Live: github_* (public repos)
│   │
│   │   # Not wired in: nothing registers these (card #987)
│   ├── read_tool.py, write_tool.py, edit_tool.py, multiedit_tool.py,
│   │   patch_tool.py, glob_tool.py, grep_tool.py, ls_tool.py, bash_tool.py
│   ├── lsp_client.py, lsp_tool.py, python_lsp_server.py  # does not import
│   └── mcp_client.py, mcp_registry.py, mcp_call_tool.py,
│       codesearch_tool.py, websearch_tool.py             # Exa over MCP
│
└── tests/              # Unit tests
```

## Key Entry Points

### j4ne.py
Main CLI application using Typer. Provides commands:
- `chat` - Interactive CLI chat (default)
- `greet <name>` - Send a greeting
- `web` - Start web server with network clients

### chatters/__init__.py
`EmCeePee()` starts the CLI: it builds a `DirectClient` and runs its `chat_loop`.
(`chatters/cli.py` is an older MCP client that nothing uses.)

### networks/
Platform clients:
- **IRC**: `IRCClient` - Connects to IRC servers, on the server's own event loop
- **Slack**: `SlackClient` - Supports both Socket Mode (dev) and HTTP (prod)

## Tools System

The LLM reaches only the tools `DirectClient` registers (`tools/direct_client.py`),
and which ones depends on the context the client was made for:

| Context | Who can talk to it | Tools |
|---------|-------------------|-------|
| `cli` | whoever runs `j4ne chat` | everything below |
| `proactive` | nobody: it runs on a timer (card #988) | everything below |
| `slack`, `irc` | anyone who can message the bot | `PUBLIC_TOOLS` only |

Public contexts never register the local providers, whatever `allowed_tools` says.

Tool names are snake_case, `<provider>_<tool>`: `ToolProvider.register_tool` adds
the prefix and raises on any other shape. The API allows no dots, and some of
OpenCode's upstreams refuse them.

**Local** (`direct_tools.py`, `cli` and `proactive` only):
- `filesystem_read_file`, `_list_files`, `_write_file`, `_delete_file`. Every path goes
  through `resolve_under_root` (realpath and commonpath, so symlinks and sibling
  directories cannot escape). Ignored paths, `.git` and `.env` included, are never
  written or deleted, and the root itself is never deleted.
- `sqlite_read_query` (a read-only SQLite authorizer, not a SELECT prefix check),
  `_write_query` (ATTACH and VACUUM denied), `_create_table`, `_list_tables`,
  `_describe_table`, `_append_insight`. The provider uses its own `db_path`.
- `git_status`, `_log`, `_diff`, `_add`, `_commit`, `_branch`. Paths resolve against the
  root, not the process cwd, and pathspecs follow `--`.
- `slack_send_message`, which waits for Slack's answer on the server's loop.

**Public** (every context):
- `web_search` (Serper, `web_search_tool.py`)
- `github_explore_repo`, `_search_repos`, `_get_file` (`github_tool.py`; names and
  paths are validated and URL-encoded)

The other modules in `tools/` (the OpenCode-port file tools, LSP, MCP/Exa) are not
registered anywhere. Card #987 lists what is wrong in each; do not wire one in as it is.

### The agent loop
`DirectClient.process_query` uses `AsyncOpenAI` and runs each tool in a worker
thread, so neither blocks the event loop that Slack, IRC and the web server share.
Tool calls go back as `role: tool` messages. A reply without tool calls is final,
whatever its finish reason. A query stops after `J4NE_MAX_TOOL_ROUNDS` rounds.
Errors raise; the caller decides what the user sees.

## Configuration

### Environment Variables
```bash
# OpenCode (the LLM). Go is the default plan; Zen's free models refuse
# callers outside OpenCode. Every request carries a User-Agent and an
# x-opencode-session (one per Slack thread, IRC channel or DM), which Go
# requires: without them it answers 400 MissingSessionID.
# OPENCODE_ZEN_MODEL names the model on either plan, despite its name. On Go,
# j4ne calls the chat-completions endpoint, which serves the GLM, Kimi and
# DeepSeek models; Go's docs put MiniMax and Qwen on Anthropic Messages.
# Current list: https://opencode.ai/inference/go/v1/models
OPENCODE_ZEN_API_KEY=...
OPENCODE_USE_GO=true                       # false for Zen
OPENCODE_ZEN_MODEL=glm-5.3                 # the default on Go
OPENCODE_ZEN_FOLLOWUP_MODEL=glm-5.3-flash  # rounds after a tool call; defaults to the model

# Slack (Socket Mode)
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...

# Slack (HTTP/Production)
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...

# Slack mode (auto/socket/http)
SLACK_MODE=auto

# IRC: off unless IRC_SERVER is set
IRC_SERVER=irc.libera.chat
IRC_NICKNAME=j4ne-bot
IRC_CHANNELS=#mychannel

# Web server (nginx proxies to 127.0.0.1:8000 in production)
J4NE_HOST=127.0.0.1
J4NE_PORT=8000
```

### mcp_config.yaml
MCP server configuration for external tools (Exa, custom servers).

## Development Notes

### Adding a New Tool

1. Subclass `DirectTool` (`tools/direct_tools.py`) with a snake_case name, a
   pydantic input model, and an `_execute(**args)` that returns a dict
   (`{"error": ...}` on failure)
2. Register it with a `ToolProvider` (whose prefix makes `<provider>_<name>`),
   and add the provider in `DirectClient.__init__`
3. Decide who gets it: anything that touches this machine stays inside the
   `LOCAL_CONTEXTS` branch; only tools safe for strangers go in `PUBLIC_TOOLS`
4. Resolve any path with `resolve_under_root`
5. Add tests in `tests/`, including the ways the arguments could be abused

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

# Tests that call real services (OpenCode, mcp.exa.ai) are marked `live` and
# skipped unless asked for, so a plain run spends no API calls
J4NE_LIVE_TESTS=1 pytest tests/ -m live -v
```

`tests/test_irc.py` runs the IRC client against a fake server on localhost, and
`tests/test_tool_guards.py` holds the boundary the local tools keep.

## Architecture Patterns

### Async/Await
The project uses Python's async throughout:
- `asyncio.run()` for entry points
- `async with` for context managers
- `await` for I/O operations

### Tool Interface
```python
class ToolName(DirectTool):
    def __init__(self, provider):
        super().__init__(name="tool-name", description="...", input_model=ToolArgs)
        self.provider = provider

    def _execute(self, **args) -> dict:
        """Run the tool; DirectTool.execute validates args first."""
        return {"result": ...}
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
