"""
Tests for the grep_tool module.
"""

import pytest
import tempfile
import os
import shutil
from pathlib import Path
from tools.grep_tool import (
    grep_search,
    GrepToolError,
    find_ripgrep,
    parse_ripgrep_output,
    sort_matches_by_mtime,
    format_matches,
)


class TestGrepTool:
    """Test suite for grep_tool functionality."""

    def test_find_ripgrep(self):
        """Test finding ripgrep executable."""
        rg_path = find_ripgrep()
        assert rg_path is not None
        assert os.path.exists(rg_path)
        # Handle both Windows (.EXE) and Unix extensions
        basename = os.path.basename(rg_path)
        assert basename.lower() in ("rg", "rg.exe")

    def test_simple_pattern_search(self, tmp_path):
        """Test basic pattern search."""
        # Create test files
        (tmp_path / "test1.txt").write_text("Hello world\nThis is a test")
        (tmp_path / "test2.txt").write_text("Another file\nHello universe")
        (tmp_path / "test3.txt").write_text("No match here")

        result = grep_search("Hello", str(tmp_path))

        assert result["title"] == "Hello"
        assert result["metadata"]["matches"] == 2
        assert result["metadata"]["truncated"] is False
        assert "test1.txt" in result["output"]
        assert "test2.txt" in result["output"]
        assert "test3.txt" not in result["output"]

    def test_regex_pattern_search(self, tmp_path):
        """Test regex pattern search."""
        # Create test files with different patterns
        (tmp_path / "func1.py").write_text("def test_function():\n    pass")
        (tmp_path / "func2.py").write_text("function myFunc() {\n    return true;\n}")
        (tmp_path / "other.py").write_text("class MyClass:\n    pass")

        result = grep_search(r"function.*\(", str(tmp_path))

        assert result["metadata"]["matches"] >= 1
        assert "func2.py" in result["output"] or "func1.py" in result["output"]

    def test_file_pattern_filtering(self, tmp_path):
        """Test file pattern filtering with include parameter."""
        # Create test files with different extensions
        (tmp_path / "test.py").write_text("import os\nprint('hello')")
        (tmp_path / "test.js").write_text(
            "const fs = require('fs');\nconsole.log('hello');"
        )
        (tmp_path / "test.txt").write_text("hello world")

        # Search only Python files
        result = grep_search("hello", str(tmp_path), include="*.py")

        assert result["metadata"]["matches"] >= 1
        assert "test.py" in result["output"]
        assert "test.js" not in result["output"]
        assert "test.txt" not in result["output"]

    def test_multiple_file_patterns(self, tmp_path):
        """Test multiple file pattern filtering."""
        # Create test files
        (tmp_path / "test.ts").write_text("interface Test { hello: string; }")
        (tmp_path / "test.tsx").write_text("const Hello = () => <div>hello</div>")
        (tmp_path / "test.js").write_text("console.log('hello');")
        (tmp_path / "test.py").write_text("print('hello')")

        # Search TypeScript files only
        result = grep_search("hello", str(tmp_path), include="*.{ts,tsx}")

        assert result["metadata"]["matches"] >= 1
        output_lower = result["output"].lower()
        assert "test.ts" in output_lower or "test.tsx" in output_lower
        assert "test.js" not in result["output"]
        assert "test.py" not in result["output"]

    def test_no_matches_found(self, tmp_path):
        """Test when no matches are found."""
        (tmp_path / "test.txt").write_text("Hello world")

        result = grep_search("nonexistent", str(tmp_path))

        assert result["title"] == "nonexistent"
        assert result["metadata"]["matches"] == 0
        assert result["metadata"]["truncated"] is False
        assert result["output"] == "No files found"

    def test_empty_directory(self, tmp_path):
        """Test searching in empty directory."""
        result = grep_search("anything", str(tmp_path))

        assert result["metadata"]["matches"] == 0
        assert result["output"] == "No files found"

    def test_invalid_search_path(self):
        """Test error with invalid search path."""
        with pytest.raises(GrepToolError) as exc_info:
            grep_search("pattern", "/nonexistent/path")

        assert "does not exist" in str(exc_info.value)

    def test_search_path_is_file(self, tmp_path):
        """Test error when search path is a file, not directory."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        with pytest.raises(GrepToolError) as exc_info:
            grep_search("pattern", str(test_file))

        assert "not a directory" in str(exc_info.value)

    def test_empty_pattern(self):
        """Test error with empty pattern."""
        with pytest.raises(GrepToolError) as exc_info:
            grep_search("")

        assert "pattern is required" in str(exc_info.value)

    def test_line_number_display(self, tmp_path):
        """Test that line numbers are correctly displayed."""
        content = "line 1\nline 2 with pattern\nline 3\nline 4 with pattern"
        (tmp_path / "test.txt").write_text(content)

        result = grep_search("pattern", str(tmp_path))

        assert "Line 2:" in result["output"]
        assert "Line 4:" in result["output"]
        assert "line 2 with pattern" in result["output"]
        assert "line 4 with pattern" in result["output"]

    def test_hidden_files(self, tmp_path):
        """Test that hidden files are searched."""
        (tmp_path / ".hidden").write_text("secret pattern here")
        (tmp_path / "normal.txt").write_text("normal file")

        result = grep_search("secret", str(tmp_path))

        assert result["metadata"]["matches"] >= 1
        assert ".hidden" in result["output"]

    def test_subdirectory_search(self, tmp_path):
        """Test searching in subdirectories."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("nested pattern")
        (tmp_path / "root.txt").write_text("root file")

        result = grep_search("nested", str(tmp_path))

        assert result["metadata"]["matches"] >= 1
        assert "nested.txt" in result["output"]

    def test_max_results_truncation(self, tmp_path):
        """Test result truncation with max_results."""
        # Create many files with matches
        for i in range(150):
            (tmp_path / f"file{i}.txt").write_text(f"pattern in file {i}")

        result = grep_search("pattern", str(tmp_path), max_results=50)

        assert result["metadata"]["matches"] == 50
        assert result["metadata"]["truncated"] is True
        assert "Results are truncated" in result["output"]

    def test_long_line_truncation(self, tmp_path):
        """Test truncation of long lines."""
        long_line = "pattern " + "x" * 3000  # Very long line
        (tmp_path / "long.txt").write_text(long_line)

        result = grep_search("pattern", str(tmp_path), max_line_length=100)

        assert result["metadata"]["matches"] >= 1
        assert "..." in result["output"]  # Should be truncated

    def test_default_search_path(self):
        """Test using default search path (current directory)."""
        # This test runs in the current directory
        result = grep_search("def test_default_search_path")

        # Should find this test function
        assert result["metadata"]["matches"] >= 1
        assert "test_grep_tool.py" in result["output"]


class TestUtilityFunctions:
    """Test utility functions."""

    def test_parse_ripgrep_output(self):
        """Test parsing ripgrep output."""
        output = """file1.txt|1|first line with pattern
file1.txt|3|third line with pattern
file2.txt|2|second file pattern"""

        matches = parse_ripgrep_output(output, 2000)

        assert len(matches) == 3
        assert matches[0]["path"] == "file1.txt"
        assert matches[0]["line_num"] == 1
        assert matches[0]["line_text"] == "first line with pattern"
        assert matches[2]["path"] == "file2.txt"

    def test_parse_ripgrep_output_with_pipes(self):
        """Test parsing output that contains pipe characters in content."""
        output = "file.txt|1|line with | pipe character"

        matches = parse_ripgrep_output(output, 2000)

        assert len(matches) == 1
        assert matches[0]["line_text"] == "line with | pipe character"

    def test_parse_ripgrep_output_line_truncation(self):
        """Test line truncation in parsing."""
        long_content = "pattern " + "x" * 100
        output = f"file.txt|1|{long_content}"

        matches = parse_ripgrep_output(output, 50)

        assert len(matches) == 1
        assert matches[0]["line_text"].endswith("...")
        assert len(matches[0]["line_text"]) <= 53  # 50 + "..."

    def test_sort_matches_by_mtime(self, tmp_path):
        """Test sorting matches by modification time."""
        # Create files with different modification times
        file1 = tmp_path / "old.txt"
        file2 = tmp_path / "new.txt"

        file1.write_text("content")
        file2.write_text("content")

        # Make file2 newer by touching it
        import time

        time.sleep(0.1)
        file2.touch()

        matches = [
            {"path": str(file1), "line_num": 1, "line_text": "content"},
            {"path": str(file2), "line_num": 1, "line_text": "content"},
        ]

        sorted_matches = sort_matches_by_mtime(matches)

        # Newer file should come first
        assert sorted_matches[0]["path"] == str(file2)
        assert sorted_matches[1]["path"] == str(file1)

    def test_format_matches(self):
        """Test formatting matches for display."""
        matches = [
            {"path": "file1.txt", "line_num": 1, "line_text": "first match"},
            {"path": "file1.txt", "line_num": 3, "line_text": "second match"},
            {"path": "file2.txt", "line_num": 2, "line_text": "third match"},
        ]

        output = format_matches(matches, "pattern", False)

        assert "Found 3 matches" in output
        assert "file1.txt:" in output
        assert "file2.txt:" in output
        assert "Line 1: first match" in output
        assert "Line 3: second match" in output
        assert "Line 2: third match" in output

    def test_format_matches_truncated(self):
        """Test formatting with truncation message."""
        matches = [{"path": "file.txt", "line_num": 1, "line_text": "match"}]

        output = format_matches(matches, "pattern", True)

        assert "Results are truncated" in output

    def test_format_matches_empty(self):
        """Test formatting empty matches."""
        output = format_matches([], "pattern", False)
        assert output == "No files found"


class TestCLIInterface:
    """Test command-line interface."""

    def test_cli_basic_usage(self, tmp_path):
        """Test basic CLI usage."""
        (tmp_path / "test.txt").write_text("CLI test pattern")

        # Test would require subprocess, but we can test the logic
        from tools.grep_tool import grep_search

        result = grep_search("CLI", str(tmp_path))
        assert result["metadata"]["matches"] >= 1
        assert "test.txt" in result["output"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
