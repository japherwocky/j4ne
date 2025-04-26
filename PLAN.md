# Plan: Dual Server Access for MCP Chat Client

## Context
- The chat client (MCPClient) currently launches a single backend (either `filesystem.py` or `localsqlite.py`) as a subprocess and connects via stdio, using the MCP protocol to query available LLM tools and resources.
- Each backend provides a distinct set of tools:
  - **Filesystem**: list/read/write/delete files.
  - **Sqlite**: database queries, append/read insights, etc.
- The chat client discovers available tools at startup from the connected server.

## Goal
Allow the chat client and LLM to access *both* the filesystem and sqlite servers/tools simultaneously in a seamless way, without requiring manual server switching or client modification.

---

## Solution: MCP Multiplexer Server

### Overview
- Build a new "multiplexing" MCP server that launches *both* backends (`filesystem.py` and `localsqlite.py`) as subprocesses.
- The multiplexer will forward and merge tool/resource lists to the client, and route tool calls to the appropriate subprocess based on tool naming.

### Features & Behavior
1. **At startup:**
   - Launches both `filesystem.py` and `localsqlite.py` as child processes.

2. **Tool/resource exposure:**
   - Aggregates lists of tools/resources/prompts from both children.
   - Applies unique prefixes to tool/resource names (e.g., `fs_` for filesystem tools, `db_` for database tools) to avoid naming conflicts and indicate origin.
   - Presents the merged, prefixed tool/resource set to the client.

3. **Tool call routing:**
   - Receives `call_tool` requests from the client.
   - Based on the tool's prefix, dispatches the call to the correct child process and returns the result back to the client.

4. **Transparent for client/LLM:**
   - The chat client only connects to this multiplexer server as normal.
   - The LLM sees all tools as a single list, each with names indicating backend.
   - No changes required in chat client or LLM logic.

### Benefits
- **Transparency:** All tools are accessible at once from the client and LLM perspective.
- **Isolation:** Individual backends remain unchanged, running as separate processes.
- **Scalability:** New backends can be added by updating the multiplexer only, if desired.

---

## Implementation Steps
1. **Create `servers/multiplexer.py`:**
   - Use asyncio to launch and communicate with both `filesystem.py` and `localsqlite.py` as child processes.
   - Implement MCP protocol forwarding: collect, prefix, and merge tool/resource lists; route tool calls.

2. **Update `connect_to_server()` (client/cli.py):**
   - Change to launch/use the multiplexer server as the primary backend.

3. **Documentation:**
   - Clearly document tool naming conventions and multiplexing behavior for future maintainers.

---

## Other Context & Considerations
- The MCP protocol enables easy dynamic discovery and routing of tools/resources.
- Prefixes for tools (e.g., `fs_`, `db_`) should be chosen to avoid conflicts in future extensions.
- Make sure any error messages from child servers are transparently forwarded and correctly referenced with their tool names in responses.
- This approach keeps the core chat loop and LLM usage unchanged.

---