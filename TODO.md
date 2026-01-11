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

## Core Tools to Implement (Priority Order)

### Tier 1: Must-Have (Implement First)

1. **`read`** - Smart file reading
   - 50KB max, 2000 lines default
   - Line-based reading with offset/limit
   - File existence checking with suggestions
   - Location: `packages/opencode/src/tool/read.ts`

2. **`edit`** - Precise string find/replace
   - Exact string matching (not regex)
   - `replaceAll` option for batch renaming
   - Requires reading file first (safety)
   - Preserves indentation perfectly
   - Shows diffs before applying
   - Location: `packages/opencode/src/tool/edit.ts`
   - Note: Sources approaches from Cline and Gemini CLI

3. **`write`** - Create/overwrite files
   - Full file creation/replacement
   - Shows diff before writing
   - LSP integration for diagnostics
   - Location: `packages/opencode/src/tool/write.ts`

4. **`grep`** - Content search via ripgrep
   - Regex pattern search
   - File type filtering (`*.js`, `*.{ts,tsx}`)
   - Directory scoping
   - Location: `packages/opencode/src/tool/grep.ts`

5. **`bash`** - Shell command execution
   - Persistent shell session
   - Security validation using tree-sitter
   - Git operations, builds, testing
   - Location: `packages/opencode/src/tool/bash.ts`

### Tier 2: Very Useful (Implement Next)

6. **`lsp`** - Language Server Protocol integration
   - 9 operations: goToDefinition, findReferences, hover, documentSymbol, workspaceSymbol, goToImplementation, prepareCallHierarchy, incomingCalls, outgoingCalls
   - Massive value-add for code generation
   - Location: `packages/opencode/src/tool/lsp.ts`
   - LSP server implementation: `packages/opencode/src/lsp/server.ts` (~62KB)

7. **`multiedit`** - Multiple edits in single operation
   - Batch string replacements on same file
   - Atomic operation (all or nothing)
   - Location: `packages/opencode/src/tool/multiedit.ts`

8. **`glob`** - File pattern matching
   - Find files by patterns (`*.py`, `**/*.test.js`)
   - More discoverable than basic ls
   - Location: `packages/opencode/src/tool/glob.ts`

9. **`ls`** - Smart directory listing
   - Ignores common build/cache dirs
   - Pre-configured patterns: `node_modules`, `__pycache__`, `.git`, etc.
   - Limited results (100 files max)
   - Location: `packages/opencode/src/tool/ls.ts`

### Tier 3: Nice to Have (Implement Later)

10. **`patch`** - Apply unified diff patches
    - Multi-file changes in single operation
    - Complex parsing required
    - Location: `packages/opencode/src/tool/patch.ts`

11. **`codesearch`** - External code context via Exa API
    - Find API usage examples
    - External dependency (API key required)
    - Location: `packages/opencode/src/tool/codesearch.ts`

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

1. **Start with core 5 tools**: read, edit, write, grep, bash
2. **Add LSP integration** for code intelligence
3. **Add glob and multiedit** for batching
4. **Skip patch and codesearch** initially

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

