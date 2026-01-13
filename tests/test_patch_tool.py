"""
Tests for the patch_tool module.
"""

import pytest
import tempfile
import os
from pathlib import Path
from tools.patch_tool import (
    apply_patch,
    parse_patch,
    PatchError,
    patch_tool_description,
    Hunk,
    HunkType,
    UpdateFileChunk
)


class TestPatchParsing:
    """Test suite for patch parsing functionality."""

    def test_missing_begin_end_markers(self):
        """Test error on missing begin/end markers."""
        with pytest.raises(PatchError) as exc_info:
            parse_patch("invalid patch")
        assert "missing *** Begin Patch / *** End Patch markers" in str(exc_info.value)

    def test_empty_patch(self):
        """Test error on empty patch (no file changes)."""
        patch = """*** Begin Patch
*** End Patch"""
        with pytest.raises(PatchError) as exc_info:
            parse_patch(patch)
        assert "No file changes found in patch" in str(exc_info.value)

    def test_parse_add_file(self):
        """Test parsing add file operation."""
        patch = """*** Begin Patch
*** Add File: new-file.txt
+Hello World
+This is a new file
*** End Patch"""

        hunks = parse_patch(patch)

        assert len(hunks) == 1
        assert hunks[0].type == HunkType.ADD
        assert hunks[0].path == "new-file.txt"
        assert hunks[0].contents == "Hello World\nThis is a new file"

    def test_parse_delete_file(self):
        """Test parsing delete file operation."""
        patch = """*** Begin Patch
*** Delete File: file-to-delete.txt
*** End Patch"""

        hunks = parse_patch(patch)

        assert len(hunks) == 1
        assert hunks[0].type == HunkType.DELETE
        assert hunks[0].path == "file-to-delete.txt"

    def test_parse_update_file(self):
        """Test parsing update file operation."""
        patch = """*** Begin Patch
*** Update File: existing.txt
@@
 line 1
-line 2
+line 2 updated
 line 3
*** End Patch"""

        hunks = parse_patch(patch)

        assert len(hunks) == 1
        assert hunks[0].type == HunkType.UPDATE
        assert hunks[0].path == "existing.txt"
        assert hunks[0].chunks is not None
        assert len(hunks[0].chunks) == 1

    def test_parse_update_with_move(self):
        """Test parsing update file with move operation."""
        patch = """*** Begin Patch
*** Update File: old-file.txt
*** Move to: new-file.txt
@@
 content here
*** End Patch"""

        hunks = parse_patch(patch)

        assert len(hunks) == 1
        assert hunks[0].type == HunkType.UPDATE
        assert hunks[0].path == "old-file.txt"
        assert hunks[0].move_path == "new-file.txt"

    def test_parse_multiple_operations(self):
        """Test parsing patch with multiple file operations."""
        patch = """*** Begin Patch
*** Add File: new1.txt
+New file 1
*** Add File: new2.txt
+New file 2
*** End Patch"""

        hunks = parse_patch(patch)

        assert len(hunks) == 2
        assert hunks[0].type == HunkType.ADD
        assert hunks[1].type == HunkType.ADD

    def test_parse_complex_update(self):
        """Test parsing complex update with multiple chunks."""
        patch = """*** Begin Patch
*** Update File: config.js
@@
 const API_KEY = "old-key"
-const DEBUG = false
+const DEBUG = true
+const LOG_LEVEL = "debug"
@@
-const LEGACY_FEATURE = true
+const LEGACY_FEATURE = false
*** End Patch"""

        hunks = parse_patch(patch)

        assert len(hunks) == 1
        assert hunks[0].chunks is not None
        assert len(hunks[0].chunks) == 2


class TestPatchApplication:
    """Test suite for patch application functionality."""

    def test_apply_add_file(self, tmp_path):
        """Test applying a patch that adds a new file."""
        patch = """*** Begin Patch
*** Add File: new-file.txt
+Hello World
+This is a new file
*** End Patch"""

        result = apply_patch(patch, str(tmp_path))

        # Check result structure
        assert result['title'] is not None
        assert "1 file changed" in result['output']
        assert result['metadata']['files_changed'] == 1

        # Verify file was created
        new_file = tmp_path / "new-file.txt"
        assert new_file.exists()
        content = new_file.read_text()
        assert content == "Hello World\nThis is a new file"

    def test_apply_add_nested_file(self, tmp_path):
        """Test applying a patch that creates nested directories."""
        patch = """*** Begin Patch
*** Add File: deep/nested/file.txt
+Deep nested content
*** End Patch"""

        result = apply_patch(patch, str(tmp_path))

        # Verify nested file was created
        nested_file = tmp_path / "deep" / "nested" / "file.txt"
        assert nested_file.exists()
        assert nested_file.read_text() == "Deep nested content"

    def test_apply_update_file(self, tmp_path):
        """Test applying a patch that updates an existing file."""
        # Create initial file
        test_file = tmp_path / "test.txt"
        test_file.write_text("line 1\nline 2\nline 3")

        patch = """*** Begin Patch
*** Update File: test.txt
@@
 line 1
-line 2
+line 2 updated
 line 3
*** End Patch"""

        result = apply_patch(patch, str(tmp_path))

        # Verify file was updated
        content = test_file.read_text()
        assert content == "line 1\nline 2 updated\nline 3"

    def test_apply_delete_file(self, tmp_path):
        """Test applying a patch that deletes a file."""
        # Create file to delete
        test_file = tmp_path / "delete-me.txt"
        test_file.write_text("This will be deleted")

        patch = """*** Begin Patch
*** Delete File: delete-me.txt
*** End Patch"""

        result = apply_patch(patch, str(tmp_path))

        # Verify file was deleted
        assert not test_file.exists()

    def test_apply_multiple_files(self, tmp_path):
        """Test applying a patch with multiple file operations."""
        patch = """*** Begin Patch
*** Add File: file1.txt
+Content of file 1
*** Add File: file2.txt
+Content of file 2
*** Add File: file3.txt
+Content of file 3
*** End Patch"""

        result = apply_patch(patch, str(tmp_path))

        # Check summary
        assert "3 files changed" in result['output']
        assert result['metadata']['files_changed'] == 3

        # Verify all files were created
        for i in range(1, 4):
            file_path = tmp_path / f"file{i}.txt"
            assert file_path.exists()
            assert file_path.read_text() == f"Content of file {i}"

    def test_apply_mixed_operations(self, tmp_path):
        """Test applying a patch with add, update, and delete operations."""
        # Create files for update and delete
        update_file = tmp_path / "update.txt"
        update_file.write_text("original content")
        delete_file = tmp_path / "delete.txt"
        delete_file.write_text("to be deleted")

        patch = """*** Begin Patch
*** Add File: new.txt
+New file content
*** Update File: update.txt
@@
 original content
+modified content
*** Delete File: delete.txt
*** End Patch"""

        result = apply_patch(patch, str(tmp_path))

        # Verify add
        new_file = tmp_path / "new.txt"
        assert new_file.exists()
        assert new_file.read_text() == "New file content"

        # Verify update
        assert update_file.read_text() == "original content\nmodified content"

        # Verify delete
        assert not delete_file.exists()

    def test_apply_file_move(self, tmp_path):
        """Test applying a patch that moves a file."""
        # Create original file
        old_file = tmp_path / "old-name.txt"
        old_file.write_text("File content")

        patch = """*** Begin Patch
*** Update File: old-name.txt
*** Move to: new-name.txt
@@
 File content
*** End Patch"""

        result = apply_patch(patch, str(tmp_path))

        # Verify file was moved
        assert not old_file.exists()
        new_file = tmp_path / "new-name.txt"
        assert new_file.exists()
        assert new_file.read_text() == "File content"

    def test_apply_empty_patch_text(self):
        """Test error on empty patch text."""
        with pytest.raises(PatchError) as exc_info:
            apply_patch("")
        assert "patchText is required" in str(exc_info.value)

    def test_apply_invalid_patch_format(self):
        """Test error on invalid patch format."""
        with pytest.raises(PatchError):
            apply_patch("not a valid patch")

    def test_update_nonexistent_file(self, tmp_path):
        """Test error when trying to update a non-existent file."""
        patch = """*** Begin Patch
*** Update File: nonexistent.txt
@@
 content
*** End Patch"""

        with pytest.raises(PatchError) as exc_info:
            apply_patch(patch, str(tmp_path))
        assert "File not found for update" in str(exc_info.value)

    def test_delete_nonexistent_file(self, tmp_path):
        """Test error when trying to delete a non-existent file."""
        patch = """*** Begin Patch
*** Delete File: nonexistent.txt
*** End Patch"""

        with pytest.raises(PatchError) as exc_info:
            apply_patch(patch, str(tmp_path))
        assert "File not found for delete" in str(exc_info.value)


class TestPatchToolEdgeCases:
    """Edge case tests for patch tool."""

    def test_patch_with_whitespace_lines(self, tmp_path):
        """Test patch handling lines with leading/trailing whitespace."""
        patch = """*** Begin Patch
*** Add File: whitespace.txt
+  line with leading spaces
+line with no leading space
+   line with mixed spaces
*** End Patch"""

        result = apply_patch(patch, str(tmp_path))

        new_file = tmp_path / "whitespace.txt"
        content = new_file.read_text()
        assert content == "  line with leading spaces\nline with no leading space\n   line with mixed spaces"

    def test_patch_unicode_content(self, tmp_path):
        """Test patch with unicode characters."""
        patch = """*** Begin Patch
*** Add File: unicode.txt
+Hello 世界
+Emoji: 😀 🎉
*** End Patch"""

        result = apply_patch(patch, str(tmp_path))

        new_file = tmp_path / "unicode.txt"
        content = new_file.read_text(encoding='utf-8')
        assert "Hello 世界" in content
        assert "😀" in content

    def test_tool_description(self):
        """Test that tool description is returned."""
        description = patch_tool_description()

        assert "patch" in description.lower()
        assert "*** Begin Patch" in description
        assert "Add File" in description
        assert "Update File" in description
        assert "Delete File" in description

    def test_metadata_structure(self, tmp_path):
        """Test that metadata contains expected fields."""
        patch = """*** Begin Patch
*** Add File: test.txt
+test content
*** End Patch"""

        result = apply_patch(patch, str(tmp_path))

        assert 'metadata' in result
        assert 'diff' in result['metadata']
        assert 'files_changed' in result['metadata']
        assert 'changed_files' in result['metadata']
        assert result['metadata']['files_changed'] == 1

    def test_combined_diff_output(self, tmp_path):
        """Test that combined diff is generated for multi-file patches."""
        patch = """*** Begin Patch
*** Add File: file1.txt
+content 1
*** Add File: file2.txt
+content 2
*** End Patch"""

        result = apply_patch(patch, str(tmp_path))

        # Combined diff should contain changes from both files
        diff = result['metadata']['diff']
        assert 'file1.txt' in diff
        assert 'file2.txt' in diff
