# OpenCode Analysis & Python Implementation TODO

## Context for Other Agents

This document contains comprehensive analysis of the OpenCode repository to guide implementation of a Python-based alternative with better Windows support.

### How to Get Context

1. **Switch to OpenCode repo**: Use `set_active_codebase("opencode")` 
2. **Key directories to explore**:
   - `packages/opencode/src/tool/` - Core tools (23 tools total)
   - `packages/opencode/src/lsp/` - Language Server Protocol integration
   - `packages/opencode/src/session/` - Session management
   - `packages/opencode/src/server/` - Client/server architecture

### Architecture Decision: Monolithic CLI vs Client/Server

**DECISION: Use monolithic CLI architecture for Python version**

**Why OpenCode uses client/server**:
- Multiple UI support (TUI, Desktop, Web)
- Session persistence across disconnections
- Real-time communication (WebSocket, SSE)
- Remote development capabilities
- Event bus coordination

**Why we DON'T need it**:
- Single interface (CLI only)
- Local development focus
- Simple session model
- No real-time updates needed
- Much simpler implementation

**Approach**: Build clean monolithic CLI with typer, design core logic for future extraction if needed.

## Core Tools Status

### ✅ Additional Tools Already Implemented (Not in OpenCode)

**Filesystem Tools** (in `tools/direct_tools.py`):
- ✅ **`ReadFileTool`** - File reading via MCP protocol
- ✅ **`WriteFileTool`** - File writing via MCP protocol  
- ✅ **`ListFilesTool`** - Directory listing (similar to `ls`)
- ✅ **`DeleteFileTool`** - File deletion

**Database Tools** (in `tools/direct_tools.py`):
- ✅ **`ReadQueryTool`** - SQLite query execution
- ✅ **`WriteQueryTool`** - SQLite data modification
- ✅ **`CreateTableTool`** - SQLite table creation
- ✅ **`ListTablesTool`** - SQLite schema inspection
- ✅ **`DescribeTableTool`** - SQLite table description
- ✅ **`AppendInsightTool`** - Data insights logging

**Git Tools** (in `tools/direct_tools.py`):
- ✅ **`GitStatusTool`** - Git status checking
- ✅ **`GitAddTool`** - Git staging
- ✅ **`GitCommitTool`** - Git commits
- ✅ **`GitBranchTool`** - Git branch management
- ✅ **`GitLogTool`** - Git history
- ✅ **`GitDiffTool`** - Git diff viewing

## Core Tools to Implement (Priority Order)

### Tier 1: Must-Have (Implement First)

1. ✅ **`read`** - Smart file reading **[COMPLETED]**
   - ✅ 50KB max, 2000 lines default
   - ✅ Line-based reading with offset/limit
   - ✅ File existence checking with suggestions
   - ✅ Binary file detection and blocking
   - ✅ Image/PDF base64 encoding support
   - ✅ Line numbering in cat -n format
   - ✅ UTF-8 encoding with proper error handling
   - ✅ Implementation: `tools/read_tool.py` (350+ lines)
   - ✅ Tests: `tests/test_read_tool.py` (16 tests, all passing)
   - Location: `packages/opencode/src/tool/read.ts`

2. ✅ **`edit`** - Precise string find/replace **[COMPLETED]**
   - ✅ Exact string matching (not regex)
   - ✅ `replaceAll` option for batch renaming
   - ✅ Requires reading file first (safety)
   - ✅ Preserves indentation perfectly
   - ✅ Shows diffs before applying
   - ✅ Multiple sophisticated replacement strategies
   - ✅ Safety features through unique match detection
   - ✅ Support for creating new files
   - ✅ Implementation: `tools/edit_tool.py` (500+ lines)
   - ✅ Tests: `tests/test_edit_tool.py` (25 tests, all passing)
   - Location: `packages/opencode/src/tool/edit.ts`
   - Note: Sources approaches from Cline and Gemini CLI

3. ✅ **`write`** - Create/overwrite files **[COMPLETED]**
   - ✅ Full file creation/replacement
   - ✅ Shows diff before writing
   - ✅ Absolute and relative path handling
   - ✅ Parent directory creation if needed
   - ✅ UTF-8 encoding support with error handling
   - ✅ Implementation: `tools/write_tool.py` (200+ lines)
   - ✅ Tests: `tests/test_write_tool.py` (20 tests, all passing)
   - Location: `packages/opencode/src/tool/write.ts`

4. ✅ **`grep`** - Content search via ripgrep **[COMPLETED]**
   - ✅ Regex pattern search with full regex syntax support
   - ✅ File type filtering (`*.js`, `*.{ts,tsx}`)
   - ✅ Directory scoping and subdirectory search
   - ✅ Results sorted by modification time (most recent first)
   - ✅ Line number and content display
   - ✅ Hidden file search support
   - ✅ Result truncation with configurable limits
   - ✅ Long line truncation for readability
   - ✅ Implementation: `tools/grep_tool.py` (300+ lines)
   - ✅ Tests: `tests/test_grep_tool.py` (24 tests, all passing)
   - Location: `packages/opencode/src/tool/grep.ts`

5. ✅ **`bash`** - Shell command execution **[COMPLETED]**
   - ✅ Command execution with configurable timeout
   - ✅ Working directory support
   - ✅ Cross-platform process termination
   - ✅ Output truncation for large outputs
   - ✅ Basic security validation for dangerous commands
   - ✅ Proper error handling and exit code capture
   - ✅ Implementation: `tools/bash_tool.py` (375+ lines)
   - ✅ Tests: `tests/test_bash_tool.py` (25+ test cases)
   - Location: `packages/opencode/src/tool/bash.ts`

### Tier 2: Very Useful (Implement Next)

6. 🚧 **`lsp`** - Language Server Protocol integration **[HIGH PRIORITY - MASSIVE VALUE-ADD]**
    
   **Core Operations (from OpenCode analysis):**
   1. **`goToDefinition`** - Find where a symbol is defined
   2. **`findReferences`** - Find all references to a symbol  
   3. **`hover`** - Get hover information (documentation, type info) for a symbol
   4. **`documentSymbol`** - Get all symbols (functions, classes, variables) in a document
   5. **`workspaceSymbol`** - Search for symbols across the entire workspace
   6. **`goToImplementation`** - Find implementations of an interface or abstract method
   7. **`prepareCallHierarchy`** - Get call hierarchy item at a position (functions/methods)
   8. **`incomingCalls`** - Find all functions/methods that call the function at a position
   9. **`outgoingCalls`** - Find all functions/methods called by the function at a position

   **OpenCode Implementation Analysis:**
   - **Massive scope**: 2032 lines in `server.ts`, supports 37 language servers
   - **Complex architecture**: JSON-RPC communication, process management, server spawning
   - **Known issues**: User reports it's "pretty buggy" - likely due to complexity
   - **Languages supported**: Deno, TypeScript, Vue, ESLint, Oxlint, Biome, Gopls (Go), Rubocop (Ruby), Pyright (Python), ElixirLS, Zls (Zig), C#, F#, Swift, Rust, Clangd (C/C++), Svelte, Astro, Java, Kotlin, YAML, Lua, PHP, Prisma, Dart, OCaml, Bash, Terraform, LaTeX, Docker, Gleam, Clojure, Nix, Typst, Haskell

   **Our Approach:**
   - Start with **Python-only** using Pyright or Pylsp
   - Use **wrapper approach** around existing mature LSP servers
   - **Opinionated**: One LSP server per language (avoid OpenCode's complexity)
   - **Planned languages**: Python → JavaScript/TypeScript → C++
   - **Phase 1**: Core 4 operations (goToDefinition, findReferences, hover, documentSymbol)
   - **Phase 2**: Advanced 5 operations (workspace, implementation, call hierarchy)
    
   **Python LSP Server Options:**
   - **Pyright** (Microsoft) - Fast, accurate, TypeScript-based, used by Pylance
   - **Pylsp** (Python LSP Server) - Pure Python, extensible, community-maintained
   - **Jedi Language Server** - Based on Jedi library, lightweight
   - **Recommendation**: Start with Pyright for speed/accuracy, fallback to Pylsp
    
   **Key Insights from OpenCode:**
   - LSP provides sophisticated code intelligence (not just linting)
   - Critical for AI code generation (same features as VS Code)
   - Complexity is the enemy - simpler approach needed
   - Process management and JSON-RPC are the hard parts
   - Project root detection is crucial for each language
   - Uses `vscode-jsonrpc` for JSON-RPC communication
   - Each language has custom spawn logic and configuration
   - File watching and diagnostics add significant complexity
   - Timeout handling is critical (LSP servers can hang)
   - Position conversion between 1-based (editor) and 0-based (LSP) is error-prone
    
   Location: `packages/opencode/src/tool/lsp.ts`
   LSP server implementation: `packages/opencode/src/lsp/server.ts` (2032 lines)

7. ✅ **`multiedit`** - Multiple edits in single operation **[COMPLETED]**
     - Batch string replacements on same file
     - Atomic operation (all or nothing)
     - Shows combined diff before applying
     - Implementation: `tools/multiedit_tool.py` (290+ lines)
     - Tests: `tests/test_multiedit_tool.py` (22 tests, all passing)
     - Location: `packages/opencode/src/tool/multiedit.ts`

8. ✅ **`glob`** - File pattern matching **[COMPLETED]**
    - Fast file pattern matching using pathlib
    - Supports glob patterns like "**/*.js" or "src/**/*.ts"
    - Returns matching files sorted by modification time (most recent first)
    - 100 result limit with truncation notice
    - Implementation: `tools/glob_tool.py` (80+ lines)
    - Tests: `tests/test_glob_tool.py` (12 tests, all passing)
    - Location: `packages/opencode/src/tool/glob.ts`

9. ✅ **`ls`** - Smart directory listing **[COMPLETED]**
    - Tree-like directory listing structure
    - Ignores common build/cache directories (node_modules, __pycache__, etc.)
    - Custom ignore pattern support
    - 100 file limit with truncation
    - Implementation: `tools/ls_tool.py` (150+ lines)
    - Tests: `tests/test_ls_tool.py` (10 tests, all passing)
    - Location: `packages/opencode/src/tool/ls.ts`

### Tier 3: Nice to Have (Implement Later)

10. **`patch`** - Apply unified diff patches
    - Multi-file changes in single operation
    - Complex parsing required
    - Location: `packages/opencode/src/tool/patch.ts`

11. **`codesearch`** - External code context via Exa API
    - Find API usage examples
    - External dependency (API key required)
    - **Requires MCP infrastructure** (see Phase 3 below)
    - Location: `packages/opencode/src/tool/codesearch.ts`

## Phase 3: MCP Integration (Future)

### MCP (Model Context Protocol) Overview
MCP is a protocol for connecting AI assistants to external tools and data sources.
OpenCode uses MCP to integrate with services like Exa's code search API.

### Why MCP is Complex
- JSON-RPC 2.0 communication layer
- Server spawning and lifecycle management
- Request/response handling with proper error codes
- Server-Sent Events (SSE) for streaming responses
- Protocol negotiation and capability exchange

### Implementation Plan
1. Create `tools/mcp_client.py` - Generic MCP client infrastructure
2. Create `tools/mcp_server.py` - Allow j4ne to act as MCP server
3. Refactor `codesearch_tool.py` to use MCP client
4. Support additional MCP servers for extensibility

### Benefits of MCP Support
- Access to Exa code search (codesearch tool)
- Database connections via MCP
- Web APIs and services
- Custom tool integrations
- Interoperability with other MCP-compatible tools

## Technology Stack Analysis

### OpenCode Current Stack
- **Runtime**: Bun (TypeScript ESM)
- **Frontend**: React + SolidJS with OpenTUI
- **Desktop**: Tauri
- **API Server**: Hono with OpenAPI
- **Communication**: WebSocket + SSE
- **LLM Integration**: @ai-sdk packages (15+ providers)

### Recommended Python Stack
- **CLI Framework**: Typer or Click
- **LLM Abstraction**: LiteLLM (unified API for all providers)
- **Configuration**: Pydantic + YAML/TOML
- **File Operations**: pathlib
- **Content Search**: ripgrep via subprocess
- **LSP Support**: pygls (optional but valuable)

## LLM Provider Support

OpenCode supports 15+ providers via @ai-sdk:
- Anthropic (Claude)
- OpenAI
- Google (Gemini, Vertex)
- Azure OpenAI
- Amazon Bedrock
- Groq, Mistral, Cohere, Cerebras
- Together AI, DeepInfra, Perplexity
- xAI, Vercel, OpenRouter
- Generic OpenAI-compatible endpoints

**For Python**: Use LiteLLM for same provider coverage with unified interface.

## Key Implementation Insights

### Safety First Philosophy
- OpenCode requires reading files before editing (prevents mistakes)
- Diff previews before destructive operations
- Permission system asks before changes
- Smart truncation for large files

### The Real Magic
- Not fancy UI (can be replaced)
- Not client/server complexity (not needed)
- **It's the precise, safe file manipulation tools**
- **Combined with LSP code intelligence**

## Repository Structure (OpenCode)

```
packages/
├── opencode/           # Core backend (~37 subdirectories)
│   ├── src/tool/      # 23 core tools
│   ├── src/lsp/       # LSP integration
│   ├── src/session/   # Session management
│   └── src/server/    # API server
├── app/               # Shared SolidJS components
├── desktop/           # Tauri desktop app
├── console/           # Console/web interface
├── plugin/            # Plugin system
├── sdk/               # TypeScript SDK
└── web/               # Web interface
```

## Next Steps for Implementation

1. **Core 5 tools**: read, edit, write, grep, bash ✅ COMPLETED
2. **LSP integration**: ✅ COMPLETED (analysis and implementation)
3. **glob and ls tools**: ✅ COMPLETED
4. **multiedit tool**: ✅ COMPLETED
5. **Future (Phase 3)**: MCP integration for codesearch and other external tools
6. **Skip patch initially** - complex parsing, low priority

## Benefits of Python Approach

- Much better Windows compatibility
- 20-30% of codebase but 80% of core value
- Clean, maintainable Python code
- Easy to extend and customize
- Leverages existing OpenCode Zen infrastructure

## Notes for Future Sessions

- This analysis provides foundation for multi-session implementation
- Focus on core tools first, add complexity incrementally
- Design for simplicity while maintaining extensibility
- Remember: the value is in safe, intelligent file manipulation + LSP
