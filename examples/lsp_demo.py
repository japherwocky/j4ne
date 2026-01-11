#!/usr/bin/env python3
"""
LSP Tool Demo

Demonstrates the capabilities of the LSP tool with real Python code.
This script shows how AI agents can use LSP for sophisticated code intelligence.

Run this script to see LSP operations in action (requires LSP server installation).
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the tools directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from tools.lsp_tool import LSPTool


async def demo_lsp_operations():
    """Demonstrate LSP operations on this very file."""
    
    print("🔍 LSP Tool Demo - Code Intelligence for AI Agents")
    print("=" * 60)
    
    # Use the current directory as workspace
    workspace = Path(__file__).parent.parent
    
    async with LSPTool(workspace, timeout=15.0) as lsp:
        print(f"📁 Workspace: {workspace}")
        
        # Get server information
        print("\n🖥️  Server Information:")
        server_info = await lsp.get_server_info()
        print(f"   Supported languages: {server_info['supported_languages']}")
        print(f"   Supported extensions: {server_info['supported_extensions']}")
        
        if "python" in server_info and "active_server" in server_info["python"]:
            print(f"   Active Python server: {server_info['python']['active_server']}")
        else:
            print("   ⚠️  No Python LSP server available")
            print("\n📋 Installation Instructions:")
            if "python" in server_info and "installation_instructions" in server_info["python"]:
                print(server_info["python"]["installation_instructions"])
            return
        
        # Demo file to analyze
        demo_file = "examples/lsp_demo.py"
        
        print(f"\n📄 Analyzing file: {demo_file}")
        
        # 1. Document Symbols - Get overview of file structure
        print("\n🗂️  Document Symbols (File Structure):")
        symbols_result = await lsp.document_symbols(demo_file)
        
        if "error" in symbols_result:
            print(f"   ❌ Error: {symbols_result['error']}")
        else:
            print(f"   Found {symbols_result['count']} symbols:")
            for symbol in symbols_result["symbols"][:5]:  # Show first 5
                line = symbol["range"]["start"]["line"]
                print(f"   • {symbol['kind']}: {symbol['name']} (line {line})")
        
        # 2. Hover Information - Get details about a function
        print("\n📖 Hover Information (Function Documentation):")
        # Try to hover over the 'demo_lsp_operations' function name
        hover_result = await lsp.hover(demo_file, 18, 10)  # Approximate position
        
        if "error" in hover_result:
            print(f"   ❌ Error: {hover_result['error']}")
        elif hover_result.get("hover"):
            contents = hover_result["hover"].get("contents", "No documentation available")
            print(f"   📝 {contents[:200]}...")  # Show first 200 chars
        else:
            print("   ℹ️  No hover information available at this position")
        
        # 3. Go to Definition - Find where something is defined
        print("\n🎯 Go to Definition (Symbol Lookup):")
        # Try to find definition of 'Path' import
        definition_result = await lsp.go_to_definition(demo_file, 6, 25)  # Approximate position
        
        if "error" in definition_result:
            print(f"   ❌ Error: {definition_result['error']}")
        elif definition_result["count"] > 0:
            location = definition_result["locations"][0]
            if "file" in location:
                line = location["range"]["start"]["line"]
                print(f"   🔗 Found definition in: {location['file']} (line {line})")
            else:
                print(f"   🔗 Found definition: {location.get('uri', 'Unknown location')}")
        else:
            print("   ℹ️  No definition found at this position")
        
        # 4. Find References - Find all usages
        print("\n🔍 Find References (Usage Analysis):")
        # Try to find references to 'lsp' variable
        references_result = await lsp.find_references(demo_file, 25, 20)  # Approximate position
        
        if "error" in references_result:
            print(f"   ❌ Error: {references_result['error']}")
        elif references_result["count"] > 0:
            print(f"   📍 Found {references_result['count']} references:")
            for ref in references_result["references"][:3]:  # Show first 3
                if "file" in ref:
                    line = ref["range"]["start"]["line"]
                    print(f"   • {ref['file']} (line {line})")
        else:
            print("   ℹ️  No references found at this position")
        
        print("\n✨ Demo completed! LSP provides the same code intelligence")
        print("   that developers use in VS Code - now available for AI agents!")


def print_usage_examples():
    """Print usage examples for the LSP tool."""
    
    print("\n📚 Usage Examples:")
    print("-" * 40)
    
    print("""
# Basic usage with convenience functions
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

# Advanced usage with LSPTool class
async def advanced_analysis():
    async with LSPTool("/path/to/project") as lsp:
        # Multiple operations with same server instance
        symbols = await lsp.document_symbols("main.py")
        for symbol in symbols["symbols"]:
            # Get details for each symbol
            hover_info = await lsp.hover("main.py", 
                                       symbol["range"]["start"]["line"],
                                       symbol["range"]["start"]["character"])
            print(f"{symbol['name']}: {hover_info}")

asyncio.run(analyze_code())
""")


async def main():
    """Main demo function."""
    try:
        await demo_lsp_operations()
        print_usage_examples()
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("\nThis might happen if:")
        print("• No Python LSP server is installed (pyright or pylsp)")
        print("• The current directory doesn't contain Python files")
        print("• LSP server failed to start")
        
        print("\n💡 To install a Python LSP server:")
        print("   npm install -g pyright  # Fast, accurate")
        print("   pip install python-lsp-server[all]  # Pure Python")


if __name__ == "__main__":
    asyncio.run(main())
