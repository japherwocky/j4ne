"""
Tests for the multiedit_tool module.
"""

import pytest
import tempfile
import os
from pathlib import Path
from tools.multiedit_tool import (
    multiedit_file,
    apply_edits_sequentially,
    validate_edit_operations,
    detect_edit_conflicts,
    MultiEditToolError,
    EditOperation,
    EditResult,
    MultiEditResult
)


class TestMultiEditTool:
    """Test suite for multiedit_tool functionality."""
    
    def test_simple_multiple_edits(self, tmp_path):
        """Test basic multiple edits on a file."""
        test_file = tmp_path / "test.py"
        content = """def hello():
    print("Hello")
    return "world"

def goodbye():
    print("Goodbye")
    return "universe"
"""
        test_file.write_text(content)
        
        edits = [
            {'old_string': 'print("Hello")', 'new_string': 'print("Hi there")', 'replace_all': False},
            {'old_string': 'return "world"', 'new_string': 'return "planet"', 'replace_all': False},
            {'old_string': 'print("Goodbye")', 'new_string': 'print("See you later")', 'replace_all': False}
        ]
        
        result = multiedit_file(str(test_file), edits)
        
        assert result['metadata']['success'] is True
        assert result['metadata']['total_edits'] == 3
        assert result['metadata']['successful_edits'] == 3
        assert "Applied multiple edits successfully" in result['output']
        
        # Check file was actually modified
        new_content = test_file.read_text()
        assert 'print("Hi there")' in new_content
        assert 'return "planet"' in new_content
        assert 'print("See you later")' in new_content
        assert 'print("Hello")' not in new_content
        assert 'return "world"' not in new_content
        assert 'print("Goodbye")' not in new_content
    
    def test_replace_all_functionality(self, tmp_path):
        """Test replace_all parameter in multiple edits."""
        test_file = tmp_path / "test.txt"
        content = "test test test\nother test content\ntest again"
        test_file.write_text(content)
        
        edits = [
            {'old_string': 'test', 'new_string': 'exam', 'replace_all': True},
            {'old_string': 'other', 'new_string': 'different', 'replace_all': False}
        ]
        
        result = multiedit_file(str(test_file), edits)
        
        assert result['metadata']['success'] is True
        assert result['metadata']['total_edits'] == 2
        assert result['metadata']['successful_edits'] == 2
        
        new_content = test_file.read_text()
        assert new_content == "exam exam exam\ndifferent exam content\nexam again"
    
    def test_file_creation_with_empty_old_string(self, tmp_path):
        """Test creating a new file using empty old_string."""
        test_file = tmp_path / "new_file.txt"
        
        edits = [
            {'old_string': '', 'new_string': 'Hello World\nThis is a new file', 'replace_all': False},
            {'old_string': 'Hello World', 'new_string': 'Hello Universe', 'replace_all': False}
        ]
        
        result = multiedit_file(str(test_file), edits)
        
        assert result['metadata']['success'] is True
        assert result['metadata']['total_edits'] == 2
        assert result['metadata']['successful_edits'] == 2
        assert test_file.exists()
        
        content = test_file.read_text()
        assert content == "Hello Universe\nThis is a new file"
    
    def test_edit_failure_atomicity(self, tmp_path):
        """Test that if one edit fails, no changes are applied."""
        test_file = tmp_path / "test.txt"
        original_content = "line1\nline2\nline3"
        test_file.write_text(original_content)
        
        edits = [
            {'old_string': 'line1', 'new_string': 'modified1', 'replace_all': False},
            {'old_string': 'nonexistent', 'new_string': 'modified2', 'replace_all': False},  # This will fail
            {'old_string': 'line3', 'new_string': 'modified3', 'replace_all': False}
        ]
        
        result = multiedit_file(str(test_file), edits)
        
        assert result['metadata']['success'] is False
        assert result['metadata']['total_edits'] == 3
        assert result['metadata']['successful_edits'] == 1  # Only first edit succeeded before failure
        assert "Multi-edit failed" in result['output']
        
        # File should remain unchanged due to atomicity
        content = test_file.read_text()
        assert content == original_content
    
    def test_conflict_detection(self, tmp_path):
        """Test detection of overlapping edits."""
        test_file = tmp_path / "test.txt"
        content = "Hello world, this is a test"
        test_file.write_text(content)
        
        # These edits overlap
        edits = [
            {'old_string': 'Hello world', 'new_string': 'Hi universe', 'replace_all': False},
            {'old_string': 'world, this', 'new_string': 'planet, that', 'replace_all': False}
        ]
        
        result = multiedit_file(str(test_file), edits, validate_conflicts=True)
        
        assert result['metadata']['success'] is False
        assert "Edit conflicts detected" in result['output']
        
        # File should remain unchanged
        content = test_file.read_text()
        assert content == "Hello world, this is a test"
    
    def test_conflict_detection_disabled(self, tmp_path):
        """Test that conflicts can be ignored when validation is disabled."""
        test_file = tmp_path / "test.txt"
        content = "Hello world"
        test_file.write_text(content)
        
        # These edits would conflict but we disable validation
        edits = [
            {'old_string': 'Hello', 'new_string': 'Hi', 'replace_all': False},
            {'old_string': 'Hello world', 'new_string': 'Hi universe', 'replace_all': False}  # Won't find this after first edit
        ]
        
        result = multiedit_file(str(test_file), edits, validate_conflicts=False)
        
        # First edit succeeds, second fails because string not found
        assert result['metadata']['success'] is False
        assert result['metadata']['successful_edits'] == 1
    
    def test_multiline_edits(self, tmp_path):
        """Test edits with multiline strings."""
        test_file = tmp_path / "test.py"
        content = """def function1():
    print("Hello")
    return True

def function2():
    print("World")
    return False
"""
        test_file.write_text(content)
        
        edits = [
            {
                'old_string': 'def function1():\n    print("Hello")\n    return True',
                'new_string': 'def function1():\n    print("Hi there")\n    return "success"',
                'replace_all': False
            },
            {
                'old_string': 'def function2():\n    print("World")\n    return False',
                'new_string': 'def function2():\n    print("Universe")\n    return "failure"',
                'replace_all': False
            }
        ]
        
        result = multiedit_file(str(test_file), edits)
        
        assert result['metadata']['success'] is True
        assert result['metadata']['total_edits'] == 2
        assert result['metadata']['successful_edits'] == 2
        
        new_content = test_file.read_text()
        assert 'print("Hi there")' in new_content
        assert 'return "success"' in new_content
        assert 'print("Universe")' in new_content
        assert 'return "failure"' in new_content
    
    def test_empty_edits_list(self, tmp_path):
        """Test error with empty edits list."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        result = multiedit_file(str(test_file), [])
        
        assert result['metadata']['success'] is False
        assert "At least one edit operation is required" in result['output']
    
    def test_invalid_edit_format(self, tmp_path):
        """Test error with invalid edit format."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        # Missing required fields
        edits = [
            {'old_string': 'test'},  # Missing new_string
        ]
        
        result = multiedit_file(str(test_file), edits)
        
        assert result['metadata']['success'] is False
        assert "missing required 'new_string' field" in result['output']
    
    def test_same_old_and_new_string(self, tmp_path):
        """Test error when old_string and new_string are the same."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        edits = [
            {'old_string': 'same', 'new_string': 'same', 'replace_all': False}
        ]
        
        result = multiedit_file(str(test_file), edits)
        
        assert result['metadata']['success'] is False
        assert "must be different" in result['output']
    
    def test_file_not_found_error(self, tmp_path):
        """Test error when file doesn't exist and first edit isn't file creation."""
        nonexistent_file = tmp_path / "nonexistent.txt"
        
        edits = [
            {'old_string': 'test', 'new_string': 'modified', 'replace_all': False}
        ]
        
        result = multiedit_file(str(nonexistent_file), edits)
        
        assert result['metadata']['success'] is False
        assert "File not found" in result['output']
    
    def test_directory_path_error(self, tmp_path):
        """Test error when path is a directory."""
        edits = [
            {'old_string': 'test', 'new_string': 'modified', 'replace_all': False}
        ]
        
        result = multiedit_file(str(tmp_path), edits)
        
        assert result['metadata']['success'] is False
        assert "Path is a directory" in result['output']
    
    def test_sequential_edit_dependencies(self, tmp_path):
        """Test that edits are applied sequentially and can depend on each other."""
        test_file = tmp_path / "test.txt"
        content = "step1 step2 step3"
        test_file.write_text(content)
        
        # Each edit depends on the result of the previous one
        edits = [
            {'old_string': 'step1', 'new_string': 'phase1', 'replace_all': False},
            {'old_string': 'phase1 step2', 'new_string': 'phase1 phase2', 'replace_all': False},
            {'old_string': 'phase2 step3', 'new_string': 'phase2 phase3', 'replace_all': False}
        ]
        
        result = multiedit_file(str(test_file), edits)
        
        assert result['metadata']['success'] is True
        assert result['metadata']['total_edits'] == 3
        assert result['metadata']['successful_edits'] == 3
        
        new_content = test_file.read_text()
        assert new_content == "phase1 phase2 phase3"
    
    def test_diff_generation(self, tmp_path):
        """Test that diff is generated correctly for multiple edits."""
        test_file = tmp_path / "test.txt"
        content = "line1\nline2\nline3"
        test_file.write_text(content)
        
        edits = [
            {'old_string': 'line1', 'new_string': 'modified1', 'replace_all': False},
            {'old_string': 'line3', 'new_string': 'modified3', 'replace_all': False}
        ]
        
        result = multiedit_file(str(test_file), edits)
        
        assert result['metadata']['success'] is True
        assert result['metadata']['diff'] is not None
        
        diff = result['metadata']['diff']
        assert '-line1' in diff
        assert '+modified1' in diff
        assert '-line3' in diff
        assert '+modified3' in diff
    
    def test_no_changes_needed(self, tmp_path):
        """Test when edits result in no actual changes."""
        test_file = tmp_path / "test.txt"
        content = "Hello world"
        test_file.write_text(content)
        
        # Edit that replaces with identical content
        edits = [
            {'old_string': 'Hello', 'new_string': 'Hello', 'replace_all': False}
        ]
        
        # This should fail due to validation
        result = multiedit_file(str(test_file), edits)
        assert result['metadata']['success'] is False
        assert "must be different" in result['output']


class TestEditOperations:
    """Test EditOperation and related functionality."""
    
    def test_validate_edit_operations_success(self):
        """Test successful validation of edit operations."""
        edits = [
            EditOperation("old1", "new1", False),
            EditOperation("old2", "new2", True),
            EditOperation("", "new3", False)  # File creation
        ]
        
        # Should not raise exception
        validate_edit_operations(edits)
    
    def test_validate_edit_operations_empty_list(self):
        """Test validation failure with empty list."""
        with pytest.raises(MultiEditToolError) as exc_info:
            validate_edit_operations([])
        
        assert "At least one edit operation is required" in str(exc_info.value)
    
    def test_validate_edit_operations_same_strings(self):
        """Test validation failure with same old and new strings."""
        edits = [
            EditOperation("same", "same", False)
        ]
        
        with pytest.raises(MultiEditToolError) as exc_info:
            validate_edit_operations(edits)
        
        assert "must be different" in str(exc_info.value)
    
    def test_detect_edit_conflicts_no_conflicts(self):
        """Test conflict detection with non-overlapping edits."""
        content = "Hello world, this is a test"
        edits = [
            EditOperation("Hello", "Hi", False),
            EditOperation("test", "example", False)
        ]
        
        conflicts = detect_edit_conflicts(content, edits)
        assert conflicts == []
    
    def test_detect_edit_conflicts_with_conflicts(self):
        """Test conflict detection with overlapping edits."""
        content = "Hello world, this is a test"
        edits = [
            EditOperation("Hello world", "Hi universe", False),
            EditOperation("world, this", "planet, that", False)
        ]
        
        conflicts = detect_edit_conflicts(content, edits)
        assert len(conflicts) > 0
        assert "overlapping target ranges" in conflicts[0]
    
    def test_detect_edit_conflicts_empty_old_string(self):
        """Test conflict detection with empty old_string (file creation)."""
        content = ""
        edits = [
            EditOperation("", "new content", False),
            EditOperation("new", "modified", False)
        ]
        
        conflicts = detect_edit_conflicts(content, edits)
        assert conflicts == []  # Empty old_string should not cause conflicts


class TestApplyEditsSequentially:
    """Test the apply_edits_sequentially function."""
    
    def test_apply_edits_success(self, tmp_path):
        """Test successful application of multiple edits."""
        test_file = tmp_path / "test.txt"
        content = "line1\nline2\nline3"
        test_file.write_text(content)
        
        edits = [
            EditOperation("line1", "modified1", False),
            EditOperation("line2", "modified2", False)
        ]
        
        result = apply_edits_sequentially(str(test_file), edits)
        
        assert result.success is True
        assert result.total_edits == 2
        assert result.successful_edits == 2
        assert len(result.edit_results) == 2
        assert all(edit.success for edit in result.edit_results)
        assert result.final_diff is not None
        
        # Check file was modified
        new_content = test_file.read_text()
        assert "modified1" in new_content
        assert "modified2" in new_content
    
    def test_apply_edits_failure(self, tmp_path):
        """Test failure during edit application."""
        test_file = tmp_path / "test.txt"
        content = "line1\nline2\nline3"
        test_file.write_text(content)
        
        edits = [
            EditOperation("line1", "modified1", False),
            EditOperation("nonexistent", "modified2", False),  # This will fail
            EditOperation("line3", "modified3", False)
        ]
        
        result = apply_edits_sequentially(str(test_file), edits)
        
        assert result.success is False
        assert result.total_edits == 3
        assert result.successful_edits == 1
        assert len(result.edit_results) == 2  # Only first two edits attempted
        assert result.edit_results[0].success is True
        assert result.edit_results[1].success is False
        assert result.error_message is not None
        
        # File should remain unchanged due to atomicity
        original_content = test_file.read_text()
        assert original_content == content
    
    def test_apply_edits_file_creation(self, tmp_path):
        """Test file creation with apply_edits_sequentially."""
        test_file = tmp_path / "new_file.txt"
        
        edits = [
            EditOperation("", "Initial content\nLine 2", False),
            EditOperation("Line 2", "Modified Line 2", False)
        ]
        
        result = apply_edits_sequentially(str(test_file), edits)
        
        assert result.success is True
        assert result.total_edits == 2
        assert result.successful_edits == 2
        assert test_file.exists()
        
        content = test_file.read_text()
        assert content == "Initial content\nModified Line 2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
