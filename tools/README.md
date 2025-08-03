# Direct Tools Implementation

This directory contains the implementation of the direct tools architecture, which replaces the stdio-based MCP implementation with direct Python function calls.

## Files

- `direct_tools.py`: Core implementation of the direct tools architecture
- `direct_client.py`: Client implementation that uses the direct tools

## Architecture

The direct tools architecture consists of:

1. **DirectTool**: Base class for all tools with validation and execution methods
2. **ToolProvider**: Base class for tool providers that manage collections of related tools
3. **DirectMultiplexer**: Aggregates tools from different providers and provides a unified interface
4. **DirectClient**: Client that uses the DirectMultiplexer to call tools directly

## Benefits

- **Eliminates Process Boundaries**: No more subprocess communication or stdio overhead
- **Simplifies Error Handling**: Errors are handled directly in Python
- **Reduces Complexity**: No need for JSON serialization/deserialization or message parsing
- **Maintains Tool Structure**: Still preserves the tool discovery and execution patterns
- **Easier Debugging**: Direct function calls are much easier to debug
- **Better Performance**: Eliminates the overhead of process creation and IPC

## Available Tools

### Filesystem Tools

- `filesystem.read-file`: Read the entire contents of a file
- `filesystem.write-file`: Write content to a file
- `filesystem.list-files`: List files and directories in a given directory
- `filesystem.delete-file`: Delete a file or directory

### SQLite Tools

- `sqlite.read-query`: Execute a SELECT query on the SQLite database
- `sqlite.write-query`: Execute an INSERT, UPDATE, or DELETE query on the SQLite database
- `sqlite.create-table`: Create a new table in the SQLite database
- `sqlite.list-tables`: List all tables in the SQLite database
- `sqlite.describe-table`: Get the schema information for a specific table
- `sqlite.append-insight`: Add a business insight to the memo

### Git Tools

- `git.status`: Show the working tree status
- `git.add`: Add file contents to the index
- `git.commit`: Record changes to the repository
- `git.branch`: List, create, switch, or delete branches
- `git.log`: Show commit logs
- `git.diff`: Show changes between commits, commit and working tree, etc

## Extending the Architecture

### Adding a New Tool

To add a new tool, create a new class that inherits from `DirectTool` and implement the `_execute` method:

```python
class MyNewTool(DirectTool):
    def __init__(self, provider):
        super().__init__(
            name="my-new-tool",
            description="Description of my new tool",
            input_model=MyInputModel
        )
        self.provider = provider
    
    def _execute(self, **kwargs):
        # Implement the tool logic here
        return {"result": "Tool executed successfully"}
```

### Adding a New Tool Provider

To add a new tool provider, create a new class that inherits from `ToolProvider` and register your tools:

```python
class MyNewProvider(ToolProvider):
    def __init__(self, config):
        super().__init__("my-provider")
        self.config = config
        self._register_tools()
    
    def _register_tools(self):
        self.register_tool(MyNewTool(self))
        # Register more tools as needed
```

Then add the provider to the multiplexer:

```python
multiplexer = DirectMultiplexer()
my_provider = MyNewProvider(config)
multiplexer.add_provider(my_provider)
```
