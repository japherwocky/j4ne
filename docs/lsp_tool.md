# LSP Tool - Language Server Protocol Integration

The LSP Tool provides sophisticated code intelligence for AI agents through Language Server Protocol (LSP) servers. It offers the same code navigation and understanding capabilities that developers use in VS Code and other modern editors.

## 🎯 What LSP Provides

LSP is **not just linting** - it's sophisticated code intelligence that includes:

- **🎯 goToDefinition**: Jump to where symbols are defined
- **🔍 findReferences**: Find all usages of a symbol across the codebase  
- **📖 hover**: Get documentation, type info, and signatures
- **🗂️ documentSymbol**: List all functions, classes, variables in a file
- **🔎 workspaceSymbol**: Search symbols across entire project *(Phase 2)*
- **🎭 goToImplementation**: Find interface implementations *(Phase 2)*
- **📞 Call Hierarchy**: See what calls what *(Phase 2)*

These are the same features you use every day in your IDE - now available for AI code generation!

## 🚀 Quick Start

### Installation

First, install the required dependencies:

```bash
pip install pygls>=1.3.0 python-lsp-jsonrpc>=1.1.0 psutil>=5.9.0
```

Then install a Python LSP server:

```bash
# Option 1: Pyright (Microsoft) - Fast, accurate, TypeScript-based
npm install -g pyright

# Option 2: Python LSP Server - Pure Python, extensible
pip install python-lsp-server[all]
```

### Basic Usage

```python
import asyncio
from tools.lsp_tool import go_to_definition, find_references, hover, document_symbols

async def analyze_code():
    # Find where a symbol is defined
    result = await go_to_definition("src/main.py", 10, 5)
    print(f"Definition: {result}")
    
    # Find all references to a symbol
    result = await find_references("src/main.py", 10, 5)
    print(f"References: {result}")
    
    # Get documentation for a symbol
    result = await hover("src/main.py", 10, 5)
    print(f"Documentation: {result}")
    
    # List all symbols in a file
    result = await document_symbols("src/main.py")
    print(f"Symbols: {result}")

asyncio.run(analyze_code())
```

### Advanced Usage

```python
from tools.lsp_tool import LSPTool
from pathlib import Path

async def advanced_analysis():
    workspace = Path("/path/to/your/project")
    
    async with LSPTool(workspace) as lsp:
        # Get server information
        info = await lsp.get_server_info()
        print(f"Using server: {info['python']['active_server']}")
        
        # Multiple operations with same server instance
        symbols = await lsp.document_symbols("main.py")
        
        for symbol in symbols["symbols"]:
            # Get details for each symbol
            hover_info = await lsp.hover("main.py", 
                                       symbol["range"]["start"]["line"],
                                       symbol["range"]["start"]["character"])
            print(f"{symbol['name']}: {hover_info}")
```

## 📊 Response Format

All LSP operations return structured JSON responses:

### goToDefinition Response
```json
{
  "operation": "goToDefinition",
  "file": "src/main.py",
  "position": {"line": 10, "character": 5},
  "locations": [
    {
      "file": "src/utils.py",
      "uri": "file:///path/to/src/utils.py",
      "range": {
        "start": {"line": 15, "character": 1},
        "end": {"line": 15, "character": 13}
      }
    }
  ],
  "server": "pyright",
  "count": 1
}
```

### findReferences Response
```json
{
  "operation": "findReferences",
  "file": "src/main.py",
  "position": {"line": 10, "character": 5},
  "include_declaration": true,
  "references": [
    {
      "file": "src/main.py",
      "range": {"start": {"line": 10, "character": 5}, "end": {"line": 10, "character": 13}}
    },
    {
      "file": "src/test.py", 
      "range": {"start": {"line": 5, "character": 8}, "end": {"line": 5, "character": 16}}
    }
  ],
  "server": "pyright",
  "count": 2
}
```

### hover Response
```json
{
  "operation": "hover",
  "file": "src/main.py",
  "position": {"line": 10, "character": 5},
  "hover": {
    "contents": "```python\ndef calculate_sum(a: int, b: int) -> int\n```\nCalculate the sum of two integers.",
    "format": "markdown",
    "range": {
      "start": {"line": 10, "character": 1},
      "end": {"line": 10, "character": 13}
    }
  },
  "server": "pyright"
}
```

### documentSymbol Response
```json
{
  "operation": "documentSymbol",
  "file": "src/main.py",
  "symbols": [
    {
      "name": "Calculator",
      "kind": "Class",
      "kind_number": 5,
      "detail": "class Calculator",
      "range": {
        "start": {"line": 5, "character": 1},
        "end": {"line": 20, "character": 1}
      },
      "selectionRange": {
        "start": {"line": 5, "character": 7},
        "end": {"line": 5, "character": 17}
      },
      "children": [
        {
          "name": "__init__",
          "kind": "Method",
          "range": {"start": {"line": 6, "character": 5}, "end": {"line": 8, "character": 21}}
        }
      ]
    }
  ],
  "server": "pyright",
  "count": 1
}
```

## 🏗️ Architecture

The LSP tool is designed with a clean, layered architecture:

```
LSPTool (High-level API)
    ↓
PythonLSPServer (Language-specific management)
    ↓
LSPClient (Low-level JSON-RPC communication)
    ↓
LSP Server Process (pyright/pylsp)
```

### Key Components

- **`LSPTool`**: Main interface with convenience methods for each operation
- **`PythonLSPServer`**: Manages Python-specific LSP servers with automatic fallback
- **`LSPClient`**: Handles JSON-RPC communication and process management
- **`Position`**: Coordinate conversion between editor (1-based) and LSP (0-based)

## 🐍 Python Support

Currently supports Python with these LSP servers:

| Server | Description | Installation | Pros |
|--------|-------------|--------------|------|
| **Pyright** | Microsoft's TypeScript-based server | `npm install -g pyright` | Fast, accurate, used by Pylance |
| **Pylsp** | Pure Python server | `pip install python-lsp-server[all]` | Extensible, community-maintained |
| **Jedi** | Lightweight Jedi-based | `pip install jedi-language-server` | Simple, lightweight |

The tool automatically detects available servers and falls back gracefully.

### Python Project Detection

Automatically detects Python project types:

- **pyproject.toml** → Modern Python project
- **setup.py** → Setuptools project  
- **Pipfile** → Pipenv project
- **poetry.lock** → Poetry project
- **requirements.txt** → Requirements-based project
- **Virtual environments** → Automatic detection and configuration

## 🔧 Configuration

### Timeout Settings

```python
# Default timeout (30 seconds)
lsp = LSPTool(workspace_root)

# Custom timeout
lsp = LSPTool(workspace_root, timeout=60.0)
```

### Server Preference

```python
from tools.python_lsp_server import PythonLSPServer

# Prefer pylsp over pyright
server = PythonLSPServer(workspace_root, preferred_server="pylsp")
```

### Error Handling

All operations return error information in the response:

```python
result = await lsp.go_to_definition("main.py", 10, 5)

if "error" in result:
    print(f"Operation failed: {result['error']}")
    print(f"Error type: {result['error_type']}")
else:
    print(f"Found {result['count']} definitions")
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Unit tests (no LSP server required)
python -m pytest tests/test_lsp_tool.py -v

# Integration tests (requires LSP server)
python -m pytest tests/test_lsp_tool.py -v -m integration

# Run the demo
python examples/lsp_demo.py
```

## 🚀 Future Plans

### Phase 2: Advanced Operations
- **workspaceSymbol**: Search symbols across entire workspace
- **goToImplementation**: Find interface implementations  
- **prepareCallHierarchy**: Get call hierarchy information
- **incomingCalls**: Find callers of a function
- **outgoingCalls**: Find functions called by a function

### Phase 3: Multi-Language Support
- **JavaScript/TypeScript**: Using typescript-language-server
- **Go**: Using gopls
- **Rust**: Using rust-analyzer
- **Java**: Using jdtls

### Phase 4: Advanced Features
- **Diagnostics**: Real-time error and warning detection
- **Code Actions**: Automated refactoring suggestions
- **Formatting**: Code formatting integration
- **Completion**: Intelligent code completion

## 🆚 Comparison with OpenCode

Our implementation avoids the complexity issues found in OpenCode:

| Aspect | OpenCode | Our Implementation |
|--------|----------|-------------------|
| **Scope** | 2032 lines, 37 languages | ~1400 lines, Python-first |
| **Complexity** | High (JSON-RPC from scratch) | Low (wrapper around mature servers) |
| **Reliability** | "Pretty buggy" (user report) | Simple, tested, reliable |
| **Approach** | Custom everything | Leverage existing mature tools |
| **Maintenance** | High (37 language configs) | Low (opinionated choices) |

## 💡 Tips for AI Agents

### Best Practices

1. **Start with documentSymbol** to understand file structure
2. **Use hover** to get type information and documentation
3. **Use goToDefinition** to understand dependencies
4. **Use findReferences** to assess impact of changes

### Common Patterns

```python
# Pattern 1: Analyze a function's usage
async def analyze_function_usage(lsp, file_path, function_line):
    # Get function definition
    definition = await lsp.go_to_definition(file_path, function_line, 1)
    
    # Find all references
    references = await lsp.find_references(file_path, function_line, 1)
    
    # Get documentation
    docs = await lsp.hover(file_path, function_line, 1)
    
    return {
        "definition": definition,
        "usage_count": references["count"],
        "documentation": docs["hover"]["contents"] if docs.get("hover") else None
    }

# Pattern 2: Get file overview
async def get_file_overview(lsp, file_path):
    symbols = await lsp.document_symbols(file_path)
    
    overview = {
        "classes": [],
        "functions": [],
        "variables": []
    }
    
    for symbol in symbols["symbols"]:
        if symbol["kind"] == "Class":
            overview["classes"].append(symbol["name"])
        elif symbol["kind"] == "Function":
            overview["functions"].append(symbol["name"])
        elif symbol["kind"] == "Variable":
            overview["variables"].append(symbol["name"])
    
    return overview
```

## 🐛 Troubleshooting

### Common Issues

**"No Python LSP servers found"**
- Install pyright: `npm install -g pyright`
- Or install pylsp: `pip install python-lsp-server[all]`

**"LSP server not found"**
- Check that the server executable is in your PATH
- Try running `pyright --version` or `pylsp --help`

**"Communication failed"**
- Check that you're in a valid Python project directory
- Ensure the file you're analyzing exists
- Try increasing the timeout value

**"File not found"**
- Use paths relative to the workspace root
- Or use absolute paths within the workspace

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now LSP operations will show detailed logs
```

## 📚 References

- [Language Server Protocol Specification](https://microsoft.github.io/language-server-protocol/)
- [Pyright Documentation](https://github.com/microsoft/pyright)
- [Python LSP Server Documentation](https://github.com/python-lsp/python-lsp-server)
- [VS Code LSP Client](https://code.visualstudio.com/api/language-extensions/language-server-extension-guide)
