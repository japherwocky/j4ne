"""
Tests for the read_tool module.
"""

import pytest
import tempfile
import os
from pathlib import Path
from tools.read_tool import (
    read_file, 
    ReadToolError, 
    is_binary_file,
    get_file_suggestions,
    DEFAULT_READ_LIMIT,
    MAX_BYTES
)


class TestReadTool:
    """Test suite for read_tool functionality."""
    
    def test_read_simple_file(self, tmp_path):
        """Test reading a simple text file."""
        # Create test file
        test_file = tmp_path / "test.txt"
        content = "Line 1\nLine 2\nLine 3\n"
        test_file.write_text(content)
        
        # Read file
        result = read_file(str(test_file))
        
        # Verify
        assert result['title'] is not None
        assert "00001| Line 1" in result['output']
        assert "00002| Line 2" in result['output']
        assert "00003| Line 3" in result['output']
        assert "(End of file - total 4 lines)" in result['output']
        assert result['metadata']['truncated'] is False
    
    def test_read_with_offset(self, tmp_path):
        """Test reading file with offset."""
        test_file = tmp_path / "test.txt"
        lines = "\n".join([f"Line {i}" for i in range(1, 101)])
        test_file.write_text(lines)
        
        # Read starting from line 50
        result = read_file(str(test_file), offset=50, limit=10)
        
        # Should start at line 51 (0-based offset 50)
        assert "00051| Line 51" in result['output']
        assert "00060| Line 60" in result['output']
        assert "Line 1" not in result['output']
    
    def test_read_with_limit(self, tmp_path):
        """Test reading file with line limit."""
        test_file = tmp_path / "test.txt"
        lines = "\n".join([f"Line {i}" for i in range(1, 3001)])
        test_file.write_text(lines)
        
        # Read with default limit
        result = read_file(str(test_file))
        
        # Should only read DEFAULT_READ_LIMIT lines
        assert "02000|" in result['output']
        assert "02001|" not in result['output']
        assert result['metadata']['truncated'] is True
    
    def test_file_not_found(self, tmp_path):
        """Test error when file doesn't exist."""
        nonexistent = tmp_path / "nonexistent.txt"
        
        with pytest.raises(ReadToolError) as exc_info:
            read_file(str(nonexistent))
        
        assert "File not found" in str(exc_info.value)
    
    def test_file_not_found_with_suggestions(self, tmp_path):
        """Test file suggestions when similar files exist."""
        # Create similar files
        (tmp_path / "readme.txt").write_text("content")
        (tmp_path / "README.md").write_text("content")
        
        # Try to read non-existent but similar name
        with pytest.raises(ReadToolError) as exc_info:
            read_file(str(tmp_path / "readm"))
        
        assert "Did you mean" in str(exc_info.value)
    
    def test_binary_file_detection(self, tmp_path):
        """Test binary file detection."""
        # Create a binary file with null bytes
        binary_file = tmp_path / "test.bin"
        binary_file.write_bytes(b'\x00\x01\x02\x03\x04')
        
        with pytest.raises(ReadToolError) as exc_info:
            read_file(str(binary_file))
        
        assert "Cannot read binary file" in str(exc_info.value)
    
    def test_binary_extension_detection(self, tmp_path):
        """Test binary detection by file extension."""
        # Binary files
        assert is_binary_file(Path("test.exe")) is True
        assert is_binary_file(Path("test.zip")) is True
        assert is_binary_file(Path("test.pyc")) is True
        
        # Text files - need to create them first
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("content")
        assert is_binary_file(txt_file) is False
        
        py_file = tmp_path / "test.py"
        py_file.write_text("print('hello')")
        assert is_binary_file(py_file) is False
    
    def test_long_line_truncation(self, tmp_path):
        """Test that very long lines are truncated."""
        test_file = tmp_path / "long.txt"
        long_line = "x" * 3000
        test_file.write_text(long_line)
        
        result = read_file(str(test_file))
        
        # Line should be truncated with ellipsis
        assert "..." in result['output']
        assert len(result['output']) < 3000
    
    def test_byte_limit_truncation(self, tmp_path):
        """Test that files are truncated at MAX_BYTES."""
        test_file = tmp_path / "large.txt"
        # Create file larger than MAX_BYTES
        lines = "\n".join(["x" * 100 for _ in range(1000)])
        test_file.write_text(lines)
        
        result = read_file(str(test_file))
        
        # Should be truncated
        assert result['metadata']['truncated'] is True
        assert "Output truncated" in result['output']
    
    def test_empty_file(self, tmp_path):
        """Test reading an empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("")
        
        result = read_file(str(test_file))
        
        assert "(End of file - total 1 lines)" in result['output']
    
    def test_relative_path_resolution(self, tmp_path):
        """Test that relative paths are resolved correctly."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        # Change to tmp_path and use relative path
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = read_file("test.txt")
            assert result['title'] == "test.txt"
        finally:
            os.chdir(original_cwd)
    
    def test_line_numbering_format(self, tmp_path):
        """Test that line numbers are formatted correctly."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2")
        
        result = read_file(str(test_file))
        
        # Check 5-digit padding
        assert "00001| Line 1" in result['output']
        assert "00002| Line 2" in result['output']
    
    def test_preview_generation(self, tmp_path):
        """Test that preview is generated correctly."""
        test_file = tmp_path / "test.txt"
        lines = "\n".join([f"Line {i}" for i in range(1, 51)])
        test_file.write_text(lines)
        
        result = read_file(str(test_file))
        
        # Preview should contain first 20 lines (without line numbers)
        preview = result['metadata']['preview']
        assert "Line 1" in preview
        assert "Line 20" in preview
        # Line 21+ should not be in preview
        preview_lines = preview.split('\n')
        assert len(preview_lines) <= 20


class TestFileSuggestions:
    """Test file suggestion functionality."""
    
    def test_get_suggestions_partial_match(self, tmp_path):
        """Test getting suggestions with partial filename match."""
        (tmp_path / "config.yaml").write_text("content")
        (tmp_path / "config.json").write_text("content")
        (tmp_path / "settings.yaml").write_text("content")
        
        suggestions = get_file_suggestions(tmp_path / "conf")
        
        # Should find config files
        assert len(suggestions) > 0
        assert any("config" in s for s in suggestions)
    
    def test_get_suggestions_max_three(self, tmp_path):
        """Test that at most 3 suggestions are returned."""
        for i in range(10):
            (tmp_path / f"test{i}.txt").write_text("content")
        
        suggestions = get_file_suggestions(tmp_path / "test")
        
        assert len(suggestions) <= 3
    
    def test_get_suggestions_nonexistent_dir(self):
        """Test suggestions for file in non-existent directory."""
        suggestions = get_file_suggestions(Path("/nonexistent/dir/file.txt"))
        assert suggestions == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
