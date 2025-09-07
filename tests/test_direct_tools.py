#!/usr/bin/env python3
"""
Test script for the direct tools implementation.
"""

import os
import json
import asyncio
import sys
import unittest
from pathlib import Path

# Add the parent directory to the path so we can import the tools module
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.direct_tools import (
    DirectMultiplexer,
    FilesystemToolProvider,
    SQLiteToolProvider
)

class TestDirectTools(unittest.TestCase):
    """Test cases for the direct tools implementation"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a test directory
        self.test_dir = Path("./test_direct_tools")
        self.test_dir.mkdir(exist_ok=True)
        
        # Create a test database path
        self.test_db = Path("./test_direct_tools.db")
        
        # Create a multiplexer with providers
        self.multiplexer = DirectMultiplexer()
        self.fs_provider = FilesystemToolProvider(str(self.test_dir))
        self.sqlite_provider = SQLiteToolProvider(str(self.test_db))
        
        self.multiplexer.add_provider(self.fs_provider)
        self.multiplexer.add_provider(self.sqlite_provider)
    
    def tearDown(self):
        """Clean up test environment"""
        # Remove test files
        if self.test_dir.exists():
            for file in self.test_dir.iterdir():
                file.unlink()
            self.test_dir.rmdir()
        
        # Remove test database
        if self.test_db.exists():
            self.test_db.unlink()
    
    def test_filesystem_tools(self):
        """Test filesystem tools"""
        # Write a test file
        result = self.multiplexer.execute_tool(
            "filesystem.write-file",
            {
                "path": "test_file.txt",
                "content": "This is a test file.",
                "create_dirs": False
            }
        )
        self.assertTrue(result.get("success", False))
        
        # Check if the file exists
        test_file = self.test_dir / "test_file.txt"
        self.assertTrue(test_file.exists())
        
        # List files
        result = self.multiplexer.execute_tool(
            "filesystem.list-files",
            {"directory": "."}
        )
        self.assertIn("files", result)
        self.assertIn("test_file.txt", result["files"])
        
        # Read the test file
        result = self.multiplexer.execute_tool(
            "filesystem.read-file",
            {"path": "test_file.txt"}
        )
        self.assertIn("content", result)
        self.assertEqual(result["content"], "This is a test file.")
        
        # Delete the test file
        result = self.multiplexer.execute_tool(
            "filesystem.delete-file",
            {"path": "test_file.txt", "recursive": False}
        )
        self.assertTrue(result.get("success", False))
        self.assertFalse(test_file.exists())
    
    def test_sqlite_tools(self):
        """Test SQLite tools"""
        # Create a test table
        result = self.multiplexer.execute_tool(
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
        self.assertTrue(result.get("success", False))
        
        # List tables
        result = self.multiplexer.execute_tool(
            "sqlite.list-tables",
            {}
        )
        self.assertIn("tables", result)
        self.assertIn("test_table", result["tables"])
        
        # Describe the test table
        result = self.multiplexer.execute_tool(
            "sqlite.describe-table",
            {"table_name": "test_table"}
        )
        self.assertIn("schema", result)
        
        # Insert data
        result = self.multiplexer.execute_tool(
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
        self.assertIn("results", result)
        
        # Query data
        result = self.multiplexer.execute_tool(
            "sqlite.read-query",
            {"query": "SELECT * FROM test_table"}
        )
        self.assertIn("results", result)
        self.assertEqual(len(result["results"]), 3)
        
        # Add an insight
        result = self.multiplexer.execute_tool(
            "sqlite.append-insight",
            {"insight": "Test insight from data analysis"}
        )
        self.assertTrue(result.get("success", False))

async def run_async_tests():
    """Run the tests asynchronously"""
    # Run the tests
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

if __name__ == "__main__":
    # Run the tests
    asyncio.run(run_async_tests())

