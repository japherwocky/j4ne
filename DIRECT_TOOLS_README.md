# Direct Tools Implementation

This is a simplified implementation of the tool architecture that eliminates the need for stdio communication between components. Instead of using the MCP protocol over stdio, tools are called directly as Python functions.

## Overview

The direct tools architecture consists of:

1. **DirectTool**: Base class for all tools
2. **ToolProvider**: Base class for tool providers that manage collections of related tools
3. **DirectMultiplexer**: Aggregates tools from different providers and provides a unified interface
4. **DirectClient**: Client that uses the DirectMultiplexer to call tools

## Benefits

- **Eliminates Process Boundaries**: No more subprocess communication or stdio overhead
- **Simplifies Error Handling**: Errors are handled directly in Python
- **Reduces Complexity**: No need for JSON serialization/deserialization or message parsing
- **Maintains Tool Structure**: Still preserves the tool discovery and execution patterns
- **Easier Debugging**: Direct function calls are much easier to debug
- **Better Performance**: Eliminates the overhead of process creation and IPC

## Files

- `direct_tools.py`: Contains the core implementation of the direct tools architecture
- `direct_client.py`: Client implementation that uses the direct tools
- `run_direct_client.py`: Entry point script for running the direct client

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

## Usage

### Running the Client

```bash
python run_direct_client.py --root-path="./" --db-path="./database.db"
```

### Environment Variables

The client requires the following environment variables to be set:

- `AZURE_OPENAI_ENDPOINT`: The endpoint URL for Azure OpenAI
- `AZURE_OPENAI_API_MODEL`: The model to use for Azure OpenAI
- `AZURE_OPENAI_API_VERSION`: The API version to use for Azure OpenAI
- `OPENAI_MODEL` (optional): The model to use for initial queries (default: "gpt-4")
- `OPENAI_FOLLOWUP_MODEL` (optional): The model to use for follow-up queries (default: "gpt-4.1-mini")

These can be set in a `.env` file in the same directory as the client.

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

## Comparison with MCP Implementation

The direct tools implementation eliminates the need for:

- Subprocess management
- Stdio communication
- JSON serialization/deserialization
- Message parsing
- Protocol handshaking

While maintaining the same functionality and tool discovery mechanism.

## Future Improvements

- Add support for asynchronous tool execution
- Implement a plugin system for dynamically loading tool providers
- Add support for tool dependencies and composition
- Implement a caching layer for tool results
- Add support for streaming responses from tools

