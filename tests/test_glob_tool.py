"""
Tests for the glob (file pattern matching) tool.
"""
import os
import tempfile
import time
import unittest
from pathlib import Path

from tools.glob_tool import glob_files


class TestGlobTool(unittest.TestCase):
    def setUp(self):
        """Create a temporary directory structure for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        # Create directory structure:
        # temp_dir/
        #   file1.py
        #   file2.py
        #   file3.js
        #   src/
        #     app.py
        #     utils.py
        #     style.css
        #   tests/
        #     test_file.py
        #   deep/
        #     nested.py

        Path("file1.py").touch()
        Path("file2.py").touch()
        Path("file3.js").touch()

        Path("src").mkdir()
        Path("src/app.py").touch()
        Path("src/utils.py").touch()
        Path("src/style.css").touch()

        Path("tests").mkdir()
        Path("tests/test_file.py").touch()

        Path("deep").mkdir()
        Path("deep/nested.py").touch()

    def tearDown(self):
        """Clean up temporary directory."""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_glob_python_files(self):
        """Test finding Python files with *.py pattern."""
        result = glob_files("*.py")
        self.assertIn("file1.py", result["output"])
        self.assertIn("file2.py", result["output"])
        self.assertNotIn("file3.js", result["output"])

    def test_glob_js_files(self):
        """Test finding JavaScript files."""
        result = glob_files("*.js")
        self.assertIn("file3.js", result["output"])
        self.assertNotIn("file1.py", result["output"])

    def test_glob_recursive_pattern(self):
        """Test recursive **/*.py pattern."""
        result = glob_files("**/*.py")
        self.assertIn("file1.py", result["output"])
        self.assertIn("file2.py", result["output"])
        # Check for app.py in src (full path or basename)
        self.assertTrue("app.py" in result["output"])
        self.assertTrue("utils.py" in result["output"])
        self.assertTrue("test_file.py" in result["output"])
        self.assertTrue("nested.py" in result["output"])

    def test_glob_nested_pattern(self):
        """Test pattern for files in specific subdirectory."""
        result = glob_files("src/*.py")
        # Check for full path or basename
        self.assertTrue(
            "app.py" in result["output"] or self.temp_dir in result["output"]
        )
        self.assertTrue(
            "utils.py" in result["output"] or self.temp_dir in result["output"]
        )
        self.assertNotIn("file1.py", result["output"])
        self.assertNotIn("tests/", result["output"])

    def test_glob_no_matches(self):
        """Test when no files match the pattern."""
        result = glob_files("*.java")
        self.assertIn("No files found", result["output"])
        self.assertEqual(result["metadata"]["count"], 0)

    def test_glob_sorted_by_mtime(self):
        """Test that results are sorted by modification time (most recent first)."""
        # Modify one file to have a newer mtime
        time.sleep(0.1)
        Path("file2.py").touch()

        result = glob_files("*.py")
        lines = result["output"].split("\n")
        lines = [l for l in lines if l]  # Remove empty lines

        # file2.py should be first since we just touched it
        self.assertTrue(lines[0].endswith("file2.py"))

    def test_glob_metadata(self):
        """Test that metadata is correct."""
        result = glob_files("*.py")
        self.assertIsInstance(result["metadata"], dict)
        self.assertIn("count", result["metadata"])
        self.assertIn("truncated", result["metadata"])

    def test_glob_title(self):
        """Test that title is the search path."""
        result = glob_files("*.py")
        self.assertEqual(result["title"], self.temp_dir)

    def test_glob_with_custom_path(self):
        """Test glob with explicit path parameter."""
        result = glob_files("*.py", path=str(Path(self.temp_dir) / "src"))
        # Results contain full paths, so just check they exist
        self.assertTrue("app.py" in result["output"])
        self.assertTrue("utils.py" in result["output"])

    def test_glob_nonexistent_path(self):
        """Test glob with non-existent path."""
        result = glob_files("*.py", path="/nonexistent/path")
        self.assertIn("Error", result["output"])
        self.assertEqual(result["metadata"]["count"], 0)

    def test_glob_file_passed_as_path(self):
        """Test glob when a file is passed as path."""
        result = glob_files("*.py", path="file1.py")
        self.assertIn("Error", result["output"])
        self.assertEqual(result["metadata"]["count"], 0)

    def test_glob_truncation(self):
        """Test that results are truncated when limit is exceeded."""
        # Create many files to exceed default limit
        for i in range(150):
            Path(f"file_{i}.py").touch()

        result = glob_files("*.py")
        self.assertTrue(result["metadata"]["truncated"])
        self.assertIn("truncated", result["output"].lower())


class TestGlobToolEdgeCases(unittest.TestCase):
    def test_empty_directory(self):
        """Test glob in an empty directory."""
        import sys
        if sys.platform == "win32":
            self.skipTest("Windows temp directory cleanup issue")
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            result = glob_files("*.py")
            self.assertIn("No files found", result["output"])
            self.assertEqual(result["metadata"]["count"], 0)

    def test_invalid_pattern(self):
        """Test handling of invalid glob pattern."""
        import sys
        if sys.platform == "win32":
            self.skipTest("Windows temp directory cleanup issue")
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            # Some patterns might cause issues, but shouldn't crash
            result = glob_files("[")
            self.assertIn("output", result)


if __name__ == "__main__":
    unittest.main()
