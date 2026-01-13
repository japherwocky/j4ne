"""
Tests for the edit_tool module.
"""

import pytest
import tempfile
import os
from pathlib import Path
from tools.edit_tool import (
    edit_file,
    EditToolError,
    replace_string,
    SimpleReplacer,
    LineTrimmedReplacer,
    WhitespaceNormalizedReplacer,
    IndentationFlexibleReplacer,
    BlockAnchorReplacer,
    MultiOccurrenceReplacer,
    create_diff,
    trim_diff
)


class TestEditTool:
    """Test suite for edit_tool functionality."""
    
    def test_simple_string_replacement(self, tmp_path):
        """Test basic string replacement."""
        test_file = tmp_path / "test.txt"
        content = "Hello world\nThis is a test\nGoodbye universe"
        test_file.write_text(content)
        
        result = edit_file(str(test_file), "world", "universe")
        
        # Check file was modified
        new_content = test_file.read_text()
        assert "Hello universe" in new_content
        assert "Goodbye universe" in new_content  # Other content preserved
        
        # Check result structure
        assert result['title'] is not None
        assert "File edited successfully" in result['output']
        assert result['metadata']['additions'] > 0
    
    def test_replace_all_functionality(self, tmp_path):
        """Test replaceAll parameter."""
        test_file = tmp_path / "test.txt"
        content = "Hello world\nThis is a test\nGoodbye world"
        test_file.write_text(content)
        
        result = edit_file(str(test_file), "world", "universe", replace_all=True)
        
        # Check all occurrences were replaced
        new_content = test_file.read_text()
        assert "Hello universe" in new_content
        assert "Goodbye universe" in new_content
        assert "world" not in new_content
    
    def test_multiline_replacement(self, tmp_path):
        """Test replacing multiline strings."""
        test_file = tmp_path / "test.py"
        content = """def hello():
    print("Hello")
    print("World")

def goodbye():
    print("Goodbye")"""
        test_file.write_text(content)
        
        old_string = """def hello():
    print("Hello")
    print("World")"""
        
        new_string = """def hello():
    print("Hi there")
    print("Universe")"""
        
        result = edit_file(str(test_file), old_string, new_string)
        
        new_content = test_file.read_text()
        assert 'print("Hi there")' in new_content
        assert 'print("Universe")' in new_content
        assert 'def goodbye():' in new_content  # Other content preserved
    
    def test_indentation_preservation(self, tmp_path):
        """Test that indentation is preserved correctly."""
        test_file = tmp_path / "test.py"
        content = """class MyClass:
    def method1(self):
        return "old"
    
    def method2(self):
        return "keep this\""""
        test_file.write_text(content)
        
        old_string = '        return "old"'
        new_string = '        return "new"'
        
        result = edit_file(str(test_file), old_string, new_string)
        
        new_content = test_file.read_text()
        assert 'return "new"' in new_content
        assert 'return "keep this"' in new_content
        # Check indentation is preserved
        lines = new_content.split('\n')
        for line in lines:
            if 'return "new"' in line:
                assert line.startswith('        ')  # 8 spaces
    
    def test_file_not_found(self, tmp_path):
        """Test error when file doesn't exist."""
        nonexistent = tmp_path / "nonexistent.txt"
        
        with pytest.raises(EditToolError) as exc_info:
            edit_file(str(nonexistent), "old", "new")
        
        assert "File not found" in str(exc_info.value)
    
    def test_directory_path_error(self, tmp_path):
        """Test error when path is a directory."""
        with pytest.raises(EditToolError) as exc_info:
            edit_file(str(tmp_path), "old", "new")
        
        assert "Path is a directory" in str(exc_info.value)
    
    def test_same_strings_error(self, tmp_path):
        """Test error when old and new strings are the same."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        with pytest.raises(EditToolError) as exc_info:
            edit_file(str(test_file), "same", "same")
        
        assert "must be different" in str(exc_info.value)
    
    def test_string_not_found(self, tmp_path):
        """Test error when old string is not found."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello world")
        
        with pytest.raises(EditToolError) as exc_info:
            edit_file(str(test_file), "nonexistent", "new")
        
        assert "oldString not found" in str(exc_info.value)
    
    def test_multiple_matches_error(self, tmp_path):
        """Test error when multiple matches found without replaceAll."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test test test")
        
        with pytest.raises(EditToolError) as exc_info:
            edit_file(str(test_file), "test", "new")
        
        assert "multiple matches" in str(exc_info.value).lower()
    
    def test_create_new_file_with_empty_old_string(self, tmp_path):
        """Test creating new file when old_string is empty."""
        test_file = tmp_path / "new.txt"
        
        result = edit_file(str(test_file), "", "New file content")
        
        assert test_file.exists()
        assert test_file.read_text() == "New file content"
        assert "File created successfully" in result['output']
    
    def test_relative_path_resolution(self, tmp_path):
        """Test that relative paths are resolved correctly."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("old content")
        
        # Change to tmp_path and use relative path
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = edit_file("test.txt", "old", "new")
            assert result['title'] == "test.txt"
            assert test_file.read_text() == "new content"
        finally:
            os.chdir(original_cwd)
    
    def test_diff_generation(self, tmp_path):
        """Test that diff is generated correctly."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("line1\nline2\nline3")
        
        result = edit_file(str(test_file), "line2", "modified_line2")
        
        diff = result['metadata']['diff']
        assert "-line2" in diff
        assert "+modified_line2" in diff
        assert "line1" in diff or "line3" in diff  # Context lines


class TestReplacers:
    """Test individual replacement strategies."""
    
    def test_simple_replacer(self):
        """Test SimpleReplacer."""
        content = "Hello world, this is a test"
        matches = list(SimpleReplacer.find_matches(content, "world"))
        assert matches == ["world"]
        
        matches = list(SimpleReplacer.find_matches(content, "nonexistent"))
        assert matches == []
    
    def test_line_trimmed_replacer(self):
        """Test LineTrimmedReplacer."""
        content = "  line1  \n    line2    \n  line3  "
        find = "line1\nline2"
        
        matches = list(LineTrimmedReplacer.find_matches(content, find))
        assert len(matches) == 1
        assert "line1" in matches[0] and "line2" in matches[0]
    
    def test_whitespace_normalized_replacer(self):
        """Test WhitespaceNormalizedReplacer."""
        content = "Hello    world\nThis  is   a    test"
        find = "Hello world"
        
        matches = list(WhitespaceNormalizedReplacer.find_matches(content, find))
        assert len(matches) == 1
        assert "Hello    world" in matches[0]
    
    def test_indentation_flexible_replacer(self):
        """Test IndentationFlexibleReplacer."""
        content = """    def method():
        return True
    
    def other():
        pass"""
        
        find = """def method():
    return True"""
        
        matches = list(IndentationFlexibleReplacer.find_matches(content, find))
        assert len(matches) == 1
        assert "def method():" in matches[0]
    
    def test_block_anchor_replacer(self):
        """Test BlockAnchorReplacer."""
        content = """def function():
    line1
    line2
    line3
    return result

def other():
    pass"""
        
        find = """def function():
    line1
    line2
    return result"""
        
        matches = list(BlockAnchorReplacer.find_matches(content, find))
        assert len(matches) == 1
        assert "def function():" in matches[0]
        assert "return result" in matches[0]
    
    def test_multi_occurrence_replacer(self):
        """Test MultiOccurrenceReplacer."""
        content = "test test test"
        matches = list(MultiOccurrenceReplacer.find_matches(content, "test"))
        assert len(matches) == 3
        assert all(match == "test" for match in matches)


class TestReplaceString:
    """Test the core replace_string function."""
    
    def test_simple_replacement(self):
        """Test basic string replacement."""
        content = "Hello world"
        result = replace_string(content, "world", "universe")
        assert result == "Hello universe"
    
    def test_replace_all(self):
        """Test replace_all functionality."""
        content = "test test test"
        result = replace_string(content, "test", "new", replace_all=True)
        assert result == "new new new"
    
    def test_unique_match_required(self):
        """Test that unique matches work without replace_all."""
        content = "Hello world, this is unique"
        result = replace_string(content, "unique", "special")
        assert result == "Hello world, this is special"
    
    def test_multiple_matches_error(self):
        """Test error on multiple matches without replace_all."""
        content = "test test test"
        with pytest.raises(EditToolError) as exc_info:
            replace_string(content, "test", "new", replace_all=False)
        
        assert "multiple matches" in str(exc_info.value).lower()
    
    def test_not_found_error(self):
        """Test error when string not found."""
        content = "Hello world"
        with pytest.raises(EditToolError):
            replace_string(content, "nonexistent", "new")


class TestDiffFunctions:
    """Test diff-related functions."""
    
    def test_create_diff(self):
        """Test diff creation."""
        old = "line1\nline2\nline3"
        new = "line1\nmodified\nline3"
        
        diff = create_diff("test.txt", old, new)
        assert "test.txt" in diff
        assert "-line2" in diff
        assert "+modified" in diff
    
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
        assert trimmed != diff


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
