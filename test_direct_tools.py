#!/usr/bin/env python3
"""
Test script for the direct tools implementation.
"""

import os
import json
import asyncio
from tools.direct_tools import (
    DirectMultiplexer,
    FilesystemToolProvider,
    SQLiteToolProvider
)

async def test_filesystem_tools():
    """Test the filesystem tools"""
    print("\n=== Testing Filesystem Tools ===")
    
    # Create a test directory
    test_dir = "./test_direct_tools"
    os.makedirs(test_dir, exist_ok=True)
    
    # Create a multiplexer with filesystem tools
    multiplexer = DirectMultiplexer()
    fs_provider = FilesystemToolProvider(test_dir)
    multiplexer.add_provider(fs_provider)
    
    # List available tools
    tools = multiplexer.get_available_tools()
    print(f"Available tools: {len(tools)}")
    for tool in tools:
        print(f"  - {tool['function']['name']}: {tool['function']['description']}")
    
    # Write a test file
    print("\nWriting test file...")
    result = multiplexer.execute_tool(
        "filesystem.write-file",
        {
            "path": "test_file.txt",
            "content": "This is a test file.",
            "create_dirs": False
        }
    )
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # List files
    print("\nListing files...")
    result = multiplexer.execute_tool(
        "filesystem.list-files",
        {"directory": "."}
    )
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Read the test file
    print("\nReading test file...")
    result = multiplexer.execute_tool(
        "filesystem.read-file",
        {"path": "test_file.txt"}
    )
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Delete the test file
    print("\nDeleting test file...")
    result = multiplexer.execute_tool(
        "filesystem.delete-file",
        {"path": "test_file.txt", "recursive": False}
    )
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Clean up
    os.rmdir(test_dir)
    print("\nTest directory cleaned up.")

async def test_sqlite_tools():
    """Test the SQLite tools"""
    print("\n=== Testing SQLite Tools ===")
    
    # Create a test database
    test_db = "./test_direct_tools.db"
    
    # Create a multiplexer with SQLite tools
    multiplexer = DirectMultiplexer()
    sqlite_provider = SQLiteToolProvider(test_db)
    multiplexer.add_provider(sqlite_provider)
    
    # List available tools
    tools = [tool for tool in multiplexer.get_available_tools() 
             if tool['function']['name'].startswith('sqlite.')]
    print(f"Available tools: {len(tools)}")
    for tool in tools:
        print(f"  - {tool['function']['name']}: {tool['function']['description']}")
    
    # Create a test table
    print("\nCreating test table...")
    result = multiplexer.execute_tool(
        "sqlite.create-table",
        {
            "query": """
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                value REAL
            )
            """
        }
    )
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # List tables
    print("\nListing tables...")
    result = multiplexer.execute_tool(
        "sqlite.list-tables",
        {}
    )
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Describe the test table
    print("\nDescribing test table...")
    result = multiplexer.execute_tool(
        "sqlite.describe-table",
        {"table_name": "test_table"}
    )
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Insert data
    print("\nInserting data...")
    result = multiplexer.execute_tool(
        "sqlite.write-query",
        {
            "query": """
            INSERT INTO test_table (name, value) VALUES
            ('test1', 1.1),
            ('test2', 2.2),
            ('test3', 3.3)
            """
        }
    )
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Query data
    print("\nQuerying data...")
    result = multiplexer.execute_tool(
        "sqlite.read-query",
        {"query": "SELECT * FROM test_table"}
    )
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Add an insight
    print("\nAdding insight...")
    result = multiplexer.execute_tool(
        "sqlite.append-insight",
        {"insight": "Test insight from data analysis"}
    )
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Clean up
    os.remove(test_db)
    print("\nTest database cleaned up.")

async def main():
    """Main entry point"""
    print("Testing Direct Tools Implementation")
    
    await test_filesystem_tools()
    await test_sqlite_tools()
    
    print("\nAll tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
