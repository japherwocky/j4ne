"""
Tests for the multiedit_tool module.
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from tools.multiedit_tool import (
    multiedit_file,
    MultiEditToolError,
    multiedit_tool_description
)


class TestMultiEditTool:
    """Test suite for multiedit_tool functionality."""

    def test_single_edit(self, tmp_path):
        """Test applying a single edit."""
        test_file = tmp_path / "test.txt"
        content = "Hello world\nThis is a test\nGoodbye universe"
        test_file.write_text(content)

        edits = [
            {
                'old_string': 'world',
                'new_string': 'universe'
            }
        ]

        result = multiedit_file(str(test_file), edits)

        # Check file was modified
        new_content = test_file.read_text()
        assert "Hello universe" in new_content
        assert "Goodbye universe" in new_content

        # Check result structure
        assert result['title'] is not None
        assert "1 edit" in result['output']
        assert result['metadata']['edit_count'] == 1

    def test_multiple_edits_same_line(self, tmp_path):
        """Test applying multiple edits to different parts of the same line."""
        test_file = tmp_path / "test.txt"
        content = "Hello world, how are you?"
        test_file.write_text(content)

        edits = [
            {
                'old_string': 'Hello',
                'new_string': 'Greetings'
            },
            {
                'old_string': 'world',
                'new_string': 'universe'
            }
        ]

        result = multiedit_file(str(test_file), edits)

        new_content = test_file.read_text()
        assert "Greetings universe, how are you?" in new_content

    def test_multiple_edits_different_lines(self, tmp_path):
        """Test applying edits to different lines."""
        test_file = tmp_path / "test.txt"
        content = "Line 1\nLine 2\nLine 3\nLine 4"
        test_file.write_text(content)

        edits = [
            {
                'old_string': 'Line 1',
                'new_string': 'First Line'
            },
            {
                'old_string': 'Line 3',
                'new_string': 'Third Line'
            }
        ]

        result = multiedit_file(str(test_file), edits)

        new_content = test_file.read_text()
        assert "First Line" in new_content
        assert "Line 2" in new_content
        assert "Third Line" in new_content
        assert "Line 4" in new_content

    def test_sequential_edits_dependent(self, tmp_path):
        """Test edits where later edits depend on earlier ones."""
        test_file = tmp_path / "test.txt"
        content = "function foo() {\n    return 42;\n}"
        test_file.write_text(content)

        # First rename the function, then change the return value
        edits = [
            {
                'old_string': 'function foo',
                'new_string': 'function bar'
            },
            {
                'old_string': 'return 42',
                'new_string': 'return 99'
            }
        ]

        result = multiedit_file(str(test_file), edits)

        new_content = test_file.read_text()
        assert "function bar" in new_content
        assert "return 99" in new_content

    def test_atomic_rollback_on_failure(self, tmp_path):
        """Test that all edits are rolled back if one fails."""
        test_file = tmp_path / "test.txt"
        content = "Hello world\nThis is a test\nGoodbye universe"
        test_file.write_text(content)

        original_content = content

        edits = [
            {
                'old_string': 'Hello',
                'new_string': 'Greetings'
            },
            {
                'old_string': 'NONEXISTENT TEXT',
                'new_string': 'Should fail'
            }
        ]

        # Second edit should fail
        with pytest.raises(MultiEditToolError):
            multiedit_file(str(test_file), edits)

        # File should be unchanged
        new_content = test_file.read_text()
        assert new_content == original_content

    def test_replace_all_in_multiedit(self, tmp_path):
        """Test replaceAll parameter within multiedit."""
        test_file = tmp_path / "test.txt"
        content = "foo bar foo baz foo"
        test_file.write_text(content)

        edits = [
            {
                'old_string': 'foo',
                'new_string': 'replaced',
                'replaceAll': True
            }
        ]

        result = multiedit_file(str(test_file), edits)

        new_content = test_file.read_text()
        assert new_content == "replaced bar replaced baz replaced"

    def test_empty_old_string_creation(self, tmp_path):
        """Test creating a new file using empty old_string."""
        test_file = tmp_path / "new_file.txt"
        test_file.write_text("")  # Create empty file first

        edits = [
            {
                'old_string': '',
                'new_string': 'New content\nLine 2\nLine 3'
            }
        ]

        result = multiedit_file(str(test_file), edits)

        new_content = test_file.read_text()
        assert "New content" in new_content
        assert "Line 2" in new_content

    def test_complex_python_code_edits(self, tmp_path):
        """Test applying multiple edits to Python code."""
        test_file = tmp_path / "test.py"
        content = """def hello():
    print("Hello")
    return 1

def goodbye():
    print("Goodbye")
    return 2
"""
        test_file.write_text(content)

        edits = [
            {
                'old_string': 'def hello',
                'new_string': 'def greet'
            },
            {
                'old_string': 'def goodbye',
                'new_string': 'def farewell'
            },
            {
                'old_string': 'print("Hello")',
                'new_string': 'print("Hello, World!")'
            }
        ]

        result = multiedit_file(str(test_file), edits)

        new_content = test_file.read_text()
        assert "def greet" in new_content
        assert "def farewell" in new_content
        assert 'print("Hello, World!")' in new_content

    def test_invalid_file_path(self, tmp_path):
        """Test error on non-existent file."""
        edits = [
            {
                'old_string': 'text',
                'new_string': 'new text'
            }
        ]

        with pytest.raises(MultiEditToolError):
            multiedit_file(str(tmp_path / "nonexistent.txt"), edits)

    def test_directory_path_error(self, tmp_path):
        """Test error when path is a directory."""
        edits = [
            {
                'old_string': 'text',
                'new_string': 'new text'
            }
        ]

        with pytest.raises(MultiEditToolError):
            multiedit_file(str(tmp_path), edits)

    def test_empty_edits_list(self, tmp_path):
        """Test error on empty edits list."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        with pytest.raises(MultiEditToolError):
            multiedit_file(str(test_file), [])

    def test_missing_old_string(self, tmp_path):
        """Test error when edit is missing old_string."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        edits = [
            {
                'new_string': 'new content'
            }
        ]

        with pytest.raises(MultiEditToolError):
            multiedit_file(str(test_file), edits)

    def test_missing_new_string(self, tmp_path):
        """Test error when edit is missing new_string."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        edits = [
            {
                'old_string': 'content'
            }
        ]

        with pytest.raises(MultiEditToolError):
            multiedit_file(str(test_file), edits)

    def test_same_old_and_new_string(self, tmp_path):
        """Test error when old_string and new_string are the same."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        edits = [
            {
                'old_string': 'content',
                'new_string': 'content'
            }
        ]

        with pytest.raises(MultiEditToolError):
            multiedit_file(str(test_file), edits)

    def test_metadata_structure(self, tmp_path):
        """Test that metadata contains expected fields."""
        test_file = tmp_path / "test.txt"
        content = "Line 1\nLine 2\nLine 3"
        test_file.write_text(content)

        edits = [
            {
                'old_string': 'Line 1',
                'new_string': 'Modified Line 1'
            },
            {
                'old_string': 'Line 3',
                'new_string': 'Modified Line 3'
            }
        ]

        result = multiedit_file(str(test_file), edits)

        assert 'metadata' in result
        assert 'diff' in result['metadata']
        assert 'edit_count' in result['metadata']
        assert result['metadata']['edit_count'] == 2
        assert 'additions' in result['metadata']
        assert 'deletions' in result['metadata']

    def test_relative_path(self, tmp_path):
        """Test with relative path (resolved from cwd)."""
        test_file = tmp_path / "test.txt"
        content = "Hello world"
        test_file.write_text(content)

        # Save current directory
        original_cwd = Path.cwd()

        try:
            # Change to tmp_path and use relative path
            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            edits = [
                {
                    'old_string': 'Hello',
                    'new_string': 'Greetings'
                }
            ]

            result = multiedit_file("test.txt", edits)

            new_content = test_file.read_text()
            assert "Greetings world" in new_content

        finally:
            os.chdir(original_cwd)

    def test_no_show_diff(self, tmp_path):
        """Test with show_diff=False."""
        test_file = tmp_path / "test.txt"
        content = "Hello world"
        test_file.write_text(content)

        edits = [
            {
                'old_string': 'Hello',
                'new_string': 'Greetings'
            }
        ]

        result = multiedit_file(str(test_file), edits, show_diff=False)

        # Output should not contain diff
        assert "---" not in result['output']
        assert "+++" not in result['output']

    def test_tool_description(self):
        """Test that tool description is returned."""
        description = multiedit_tool_description()

        assert "multiple edits" in description.lower()
        assert "atomic" in description.lower()
        assert "filePath" in description
        assert "edits" in description


class TestMultiEditToolEdgeCases:
    """Edge case tests for multiedit_tool."""

    def test_multiline_edits(self, tmp_path):
        """Test edits spanning multiple lines."""
        test_file = tmp_path / "test.txt"
        content = """def foo():
    x = 1
    y = 2
    return x + y

def bar():
    pass
"""
        test_file.write_text(content)

        edits = [
            {
                'old_string': 'def foo():\n    x = 1\n    y = 2',
                'new_string': 'def foo():\n    x = 10\n    y = 20'
            }
        ]

        result = multiedit_file(str(test_file), edits)

        new_content = test_file.read_text()
        assert "x = 10" in new_content
        assert "y = 20" in new_content

    def test_unicode_content(self, tmp_path):
        """Test with unicode characters."""
        test_file = tmp_path / "test.txt"
        content = "Hello世界\nEmoji: 😀 🎉\nGreek: Ωμέγα"
        test_file.write_text(content, encoding='utf-8')

        edits = [
            {
                'old_string': 'Hello',
                'new_string': '你好'
            }
        ]

        result = multiedit_file(str(test_file), edits)

        new_content = test_file.read_text(encoding='utf-8')
        assert "你好世界" in new_content

    def test_large_file_edits(self, tmp_path):
        """Test edits on a larger file."""
        test_file = tmp_path / "test.txt"
        # Create a file with 100 lines
        lines = [f"Line {i}: content here" for i in range(100)]
        content = "\n".join(lines)
        test_file.write_text(content)

        edits = [
            {
                'old_string': 'Line 0:',
                'new_string': 'Zero:'
            },
            {
                'old_string': 'Line 50:',
                'new_string': 'Fifty:'
            },
            {
                'old_string': 'Line 99:',
                'new_string': 'Last:'
            }
        ]

        result = multiedit_file(str(test_file), edits)

        new_content = test_file.read_text()
        assert "Zero:" in new_content
        assert "Fifty:" in new_content
        assert "Last:" in new_content

    def test_whitespace_variations(self, tmp_path):
        """Test handling of whitespace in edits."""
        test_file = tmp_path / "test.txt"
        content = "    indented content\n  more indented\n\t\ttab indented"
        test_file.write_text(content)

        edits = [
            {
                'old_string': 'indented content',
                'new_string': 'CHANGED'
            }
        ]

        result = multiedit_file(str(test_file), edits)

        new_content = test_file.read_text()
        # Original indentation should be preserved
        assert "    CHANGED" in new_content
