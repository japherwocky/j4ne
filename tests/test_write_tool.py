"""
Tests for the write_tool module.
"""

import pytest
import tempfile
import os
from pathlib import Path
from tools.write_tool import (
    write_file,
    WriteToolError,
    create_diff,
    trim_diff,
    normalize_line_endings
)


class TestWriteTool:
    """Test suite for write_tool functionality."""
    
    def test_create_new_file(self, tmp_path):
        """Test creating a new file."""
        test_file = tmp_path / "new_file.txt"
        content = "Hello, world!\nThis is a new file."
        
        result = write_file(str(test_file), content)
        
        # Check file was created
        assert test_file.exists()
        assert test_file.read_text() == content
        
        # Check result structure
        assert result['title'] is not None
        assert "File created successfully" in result['output']
        assert result['metadata']['exists'] is False
        assert result['metadata']['additions'] > 0
        assert result['metadata']['deletions'] == 0
    
    def test_overwrite_existing_file(self, tmp_path):
        """Test overwriting an existing file."""
        test_file = tmp_path / "existing.txt"
        old_content = "Old content\nLine 2"
        new_content = "New content\nDifferent line 2"
        
        # Create initial file
        test_file.write_text(old_content)
        
        result = write_file(str(test_file), new_content)
        
        # Check file was overwritten
        assert test_file.read_text() == new_content
        
        # Check result structure
        assert "File overwritten successfully" in result['output']
        assert result['metadata']['exists'] is True
        assert result['metadata']['additions'] > 0
        assert result['metadata']['deletions'] > 0
    
    def test_create_file_with_parent_directories(self, tmp_path):
        """Test creating a file with non-existent parent directories."""
        test_file = tmp_path / "nested" / "deep" / "file.txt"
        content = "Content in nested directory"
        
        result = write_file(str(test_file), content)
        
        # Check file and directories were created
        assert test_file.exists()
        assert test_file.read_text() == content
        assert test_file.parent.exists()
        assert test_file.parent.parent.exists()
    
    def test_relative_path_resolution(self, tmp_path):
        """Test that relative paths are resolved correctly."""
        test_file = tmp_path / "relative.txt"
        content = "Relative path content"
        
        # Change to tmp_path and use relative path
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = write_file("relative.txt", content)
            
            assert result['title'] == "relative.txt"
            assert test_file.exists()
            assert test_file.read_text() == content
        finally:
            os.chdir(original_cwd)
    
    def test_absolute_path_handling(self, tmp_path):
        """Test handling of absolute paths."""
        test_file = tmp_path / "absolute.txt"
        content = "Absolute path content"
        
        result = write_file(str(test_file), content)
        
        assert test_file.exists()
        assert test_file.read_text() == content
        assert result['metadata']['filepath'] == str(test_file)
    
    def test_empty_content(self, tmp_path):
        """Test writing empty content."""
        test_file = tmp_path / "empty.txt"
        content = ""
        
        result = write_file(str(test_file), content)
        
        assert test_file.exists()
        assert test_file.read_text() == ""
        assert "File created successfully" in result['output']
    
    def test_unicode_content(self, tmp_path):
        """Test writing Unicode content."""
        test_file = tmp_path / "unicode.txt"
        content = "Hello 世界! 🌍\nUnicode test: αβγ"
        
        result = write_file(str(test_file), content)
        
        assert test_file.exists()
        assert test_file.read_text(encoding='utf-8') == content
    
    def test_large_content(self, tmp_path):
        """Test writing large content."""
        test_file = tmp_path / "large.txt"
        content = "Line {}\n".format("x" * 100) * 1000  # ~100KB
        
        result = write_file(str(test_file), content)
        
        assert test_file.exists()
        assert test_file.read_text() == content
        assert result['metadata']['additions'] > 900  # Should have many lines
    
    def test_directory_path_error(self, tmp_path):
        """Test error when trying to write to a directory."""
        directory = tmp_path / "test_dir"
        directory.mkdir()
        
        with pytest.raises(WriteToolError) as exc_info:
            write_file(str(directory), "content")
        
        assert "Path is a directory" in str(exc_info.value)
    
    def test_invalid_file_path(self):
        """Test error with invalid file path."""
        with pytest.raises(WriteToolError) as exc_info:
            write_file("", "content")
        
        assert "filePath is required" in str(exc_info.value)
    
    def test_diff_generation(self, tmp_path):
        """Test that diff is generated correctly."""
        test_file = tmp_path / "diff_test.txt"
        old_content = "line1\nline2\nline3"
        new_content = "line1\nmodified_line2\nline3\nnew_line4"
        
        # Create initial file
        test_file.write_text(old_content)
        
        result = write_file(str(test_file), new_content)
        
        diff = result['metadata']['diff']
        assert "-line2" in diff
        assert "+modified_line2" in diff
        assert "+new_line4" in diff
    
    def test_no_diff_when_content_same(self, tmp_path):
        """Test that no meaningful diff is shown when content is the same."""
        test_file = tmp_path / "same.txt"
        content = "Same content\nLine 2"
        
        # Create initial file
        test_file.write_text(content)
        
        result = write_file(str(test_file), content)
        
        # Should still succeed but with minimal diff
        assert "File overwritten successfully" in result['output']
        assert result['metadata']['additions'] == 0
        assert result['metadata']['deletions'] == 0
    
    def test_working_directory_parameter(self, tmp_path):
        """Test the working_directory parameter."""
        test_file = tmp_path / "workdir_test.txt"
        content = "Working directory test"
        
        result = write_file("workdir_test.txt", content, working_directory=str(tmp_path))
        
        assert test_file.exists()
        assert test_file.read_text() == content
    
    def test_show_diff_parameter(self, tmp_path):
        """Test the show_diff parameter."""
        test_file = tmp_path / "no_diff.txt"
        old_content = "old"
        new_content = "new"
        
        test_file.write_text(old_content)
        
        # Test with show_diff=False
        result = write_file(str(test_file), new_content, show_diff=False)
        
        assert "File overwritten successfully" in result['output']
        assert result['metadata']['diff']  # Diff still in metadata
        # But not in output
        assert "old" not in result['output']
        assert "new" not in result['output']


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_normalize_line_endings(self):
        """Test line ending normalization."""
        windows_text = "line1\r\nline2\r\n"
        unix_text = "line1\nline2\n"
        
        assert normalize_line_endings(windows_text) == unix_text
        assert normalize_line_endings(unix_text) == unix_text
    
    def test_create_diff(self):
        """Test diff creation."""
        old = "line1\nline2\nline3"
        new = "line1\nmodified\nline3"
        
        diff = create_diff("test.txt", old, new)
        assert "test.txt" in diff
        assert "-line2" in diff
        assert "+modified" in diff
    
    def test_create_diff_new_file(self):
        """Test diff creation for new file."""
        old = ""
        new = "new content\nline2"
        
        diff = create_diff("new.txt", old, new)
        assert "new.txt" in diff
        assert "+new content" in diff
        assert "+line2" in diff
    
    def test_trim_diff(self):
        """Test diff trimming."""
        diff = """--- a/test.txt
+++ b/test.txt
@@ -1,3 +1,3 @@
     line1
-    line2
+    modified
     line3"""
        
        trimmed = trim_diff(diff)
        # Should remove common indentation
        assert "line1" in trimmed
        assert "modified" in trimmed
    
    def test_trim_diff_no_common_indent(self):
        """Test diff trimming with no common indentation."""
        diff = """--- a/test.txt
+++ b/test.txt
@@ -1,2 +1,2 @@
-old
+new"""
        
        trimmed = trim_diff(diff)
        # Should remain unchanged
        assert trimmed == diff


class TestCLIInterface:
    """Test command-line interface."""
    
    def test_cli_basic_usage(self, tmp_path):
        """Test basic CLI usage."""
        test_file = tmp_path / "cli_test.txt"
        
        # Test would require subprocess, but we can test the logic
        from tools.write_tool import write_file
        
        result = write_file(str(test_file), "CLI test content")
        assert test_file.exists()
        assert "File created successfully" in result['output']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

