# Direct Tools Implementation

This directory contains the implementation of the direct tools architecture for tool integration and execution.

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

- `filesystem_read_file`: Read the entire contents of a file
- `filesystem_write_file`: Write content to a file
- `filesystem_list_files`: List files and directories in a given directory
- `filesystem_delete_file`: Delete a file or directory

### SQLite Tools

- `sqlite_read_query`: Execute a SELECT query on the SQLite database
- `sqlite_write_query`: Execute an INSERT, UPDATE, or DELETE query on the SQLite database
- `sqlite_create_table`: Create a new table in the SQLite database
- `sqlite_list_tables`: List all tables in the SQLite database
- `sqlite_describe_table`: Get the schema information for a specific table
- `sqlite_append_insight`: Add a business insight to the memo

### Git Tools

- `git_status`: Show the working tree status
- `git_add`: Add file contents to the index
- `git_commit`: Record changes to the repository
- `git_branch`: List, create, switch, or delete branches
- `git_log`: Show commit logs
- `git_diff`: Show changes between commits, commit and working tree, etc

## Extending the Architecture

### Adding a New Tool

To add a new tool, create a new class that inherits from `DirectTool` and implement the `_execute` method:

```python
class MyNewTool(DirectTool):
    def __init__(self, provider):
        super().__init__(
            name="my_new_tool",  # snake_case; registered as my_provider_my_new_tool
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
        super().__init__("my_provider")
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