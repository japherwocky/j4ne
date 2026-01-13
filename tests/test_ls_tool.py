"""
Tests for the ls (list) tool.
"""
import os
import tempfile
import unittest
from pathlib import Path

from tools.ls_tool import list_directory, DEFAULT_IGNORE_PATTERNS, should_ignore


class TestListTool(unittest.TestCase):
    def setUp(self):
        """Create a temporary directory structure for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        # Create directory structure:
        # temp_dir/
        #   file1.txt
        #   file2.py
        #   src/
        #     app.js
        #     utils.ts
        #   node_modules/
        #     ignored.js
        #   __pycache__/
        #     cache.pyc
        #   .git/
        #     config
        #   deep/
        #     nested/
        #       file.txt

        Path("file1.txt").touch()
        Path("file2.py").touch()

        Path("src").mkdir()
        Path("src/app.js").touch()
        Path("src/utils.ts").touch()

        Path("node_modules").mkdir()
        Path("node_modules/ignored.js").touch()

        Path("__pycache__").mkdir()
        Path("__pycache__/cache.pyc").touch()

        Path(".git").mkdir()
        Path(".git/config").touch()

        Path("deep").mkdir()
        Path("deep/nested").mkdir()
        Path("deep/nested/file.txt").touch()

    def tearDown(self):
        """Clean up temporary directory."""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_list_directory_basic(self):
        """Test basic directory listing."""
        result = list_directory(".")
        self.assertIn("file1.txt", result["output"])
        self.assertIn("file2.py", result["output"])
        self.assertIn("src/", result["output"])
        self.assertNotIn("node_modules", result["output"])
        self.assertNotIn("__pycache__", result["output"])
        self.assertNotIn(".git", result["output"])

    def test_list_directory_shows_tree_structure(self):
        """Test that output shows hierarchical structure."""
        result = list_directory(".")
        self.assertIn("src/", result["output"])
        self.assertIn("app.js", result["output"])
        self.assertIn("deep/", result["output"])
        self.assertIn("nested/", result["output"])

    def test_list_directory_nonexistent(self):
        """Test handling of non-existent directory."""
        result = list_directory("/nonexistent/path")
        self.assertIn("Error", result["output"])
        self.assertEqual(result["metadata"]["count"], 0)

    def test_list_directory_file_passed(self):
        """Test handling when a file is passed instead of directory."""
        result = list_directory("file1.txt")
        self.assertIn("Error", result["output"])
        self.assertEqual(result["metadata"]["count"], 0)

    def test_list_directory_custom_ignore(self):
        """Test custom ignore patterns."""
        result = list_directory(".", ignore=["src"])
        self.assertNotIn("src/", result["output"])
        self.assertNotIn("app.js", result["output"])

    def test_should_ignore(self):
        """Test the should_ignore function."""
        self.assertTrue(should_ignore("node_modules", DEFAULT_IGNORE_PATTERNS))
        self.assertTrue(should_ignore("__pycache__", DEFAULT_IGNORE_PATTERNS))
        self.assertTrue(should_ignore(".git", DEFAULT_IGNORE_PATTERNS))
        self.assertTrue(should_ignore("dist", DEFAULT_IGNORE_PATTERNS))
        self.assertFalse(should_ignore("src", DEFAULT_IGNORE_PATTERNS))
        self.assertFalse(should_ignore("file.py", DEFAULT_IGNORE_PATTERNS))

    def test_list_directory_metadata(self):
        """Test that metadata is correct."""
        result = list_directory(".")
        self.assertIsInstance(result["metadata"], dict)
        self.assertIn("count", result["metadata"])
        self.assertIn("truncated", result["metadata"])
        self.assertIsInstance(result["metadata"]["truncated"], bool)

    def test_list_directory_title(self):
        """Test that title is the directory path."""
        result = list_directory(".")
        self.assertEqual(result["title"], self.temp_dir)


class TestListToolEdgeCases(unittest.TestCase):
    def test_empty_directory(self):
        """Test listing an empty directory."""
        import sys
        if sys.platform == "win32":
            self.skipTest("Windows temp directory cleanup issue")
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            result = list_directory(".")
            self.assertIn("output", result)
            self.assertIn("metadata", result)

    def test_permission_denied(self):
        """Test handling of permission errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a directory we can't read
            protected = Path(temp_dir) / "protected"
            protected.mkdir()
            protected.chmod(0o000)

            try:
                result = list_directory(str(protected))
                # Should handle gracefully without crashing
                self.assertIn("output", result)
            finally:
                protected.chmod(0o755)


if __name__ == "__main__":
    unittest.main()
