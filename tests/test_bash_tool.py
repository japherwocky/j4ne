"""
Tests for the bash tool.
"""

import os
import tempfile
import time
import platform
from pathlib import Path

from tools.bash_tool import BashTool, BashToolError, execute_bash_command

# Simple pytest replacement for basic testing
class pytest:
    @staticmethod
    def raises(exception_type, match=None):
        class RaisesContext:
            def __init__(self, exception_type, match=None):
                self.exception_type = exception_type
                self.match = match
            
            def __enter__(self):
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type is None:
                    raise AssertionError(f"Expected {self.exception_type.__name__} but no exception was raised")
                if not issubclass(exc_type, self.exception_type):
                    return False  # Let the exception propagate
                if self.match and self.match not in str(exc_val):
                    raise AssertionError(f"Expected exception message to contain '{self.match}', got '{exc_val}'")
                return True  # Suppress the exception
        
        return RaisesContext(exception_type, match)


class TestBashTool:
    """Test cases for the BashTool class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = BashTool()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up temp directory
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass
    
    def test_basic_command_execution(self):
        """Test basic command execution."""
        if platform.system() == "Windows":
            result = self.tool.execute("echo Hello World", description="Test echo")
        else:
            result = self.tool.execute("echo 'Hello World'", description="Test echo")
        
        assert result["success"] is True
        assert result["exit_code"] == 0
        assert "Hello World" in result["output"]
        assert result["timeout_exceeded"] is False
        assert result["truncated"] is False
        assert result["description"] == "Test echo"
    
    def test_command_with_working_directory(self):
        """Test command execution with custom working directory."""
        # Create a test file in temp directory
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("test content")
        
        if platform.system() == "Windows":
            result = self.tool.execute("dir", workdir=self.temp_dir, description="List directory")
            assert "test.txt" in result["output"]
        else:
            result = self.tool.execute("ls", workdir=self.temp_dir, description="List directory")
            assert "test.txt" in result["output"]
        
        assert result["success"] is True
        assert result["working_directory"] == self.temp_dir
    
    def test_command_timeout(self):
        """Test command timeout functionality."""
        if platform.system() == "Windows":
            # Windows sleep command
            result = self.tool.execute("timeout 5", timeout=1, description="Test timeout")
        else:
            # Unix sleep command
            result = self.tool.execute("sleep 5", timeout=1, description="Test timeout")
        
        assert result["success"] is False
        assert result["timeout_exceeded"] is True
        assert "timeout" in result["output"].lower()
    
    def test_command_failure(self):
        """Test handling of failed commands."""
        # Use a command that should fail
        result = self.tool.execute("nonexistent_command_12345", description="Test failure")
        
        assert result["success"] is False
        assert result["exit_code"] != 0
        assert result["timeout_exceeded"] is False
    
    def test_invalid_working_directory(self):
        """Test error handling for invalid working directory."""
        with pytest.raises(BashToolError, match="Working directory does not exist"):
            self.tool.execute("echo test", workdir="/nonexistent/directory")
    
    def test_invalid_timeout(self):
        """Test error handling for invalid timeout."""
        with pytest.raises(BashToolError, match="Invalid timeout"):
            self.tool.execute("echo test", timeout=-1)
    
    def test_dangerous_command_validation(self):
        """Test validation of potentially dangerous commands."""
        # This should raise an error due to dangerous pattern
        with pytest.raises(BashToolError, match="potentially dangerous pattern"):
            self.tool.execute("echo test && rm -rf /", description="Dangerous command")
    
    def test_safe_rm_command(self):
        """Test that safe rm commands (like help) are allowed."""
        # This should not raise an error
        result = self.tool.execute("rm --help", description="Get rm help")
        # The command might fail if rm is not available, but it shouldn't be blocked by validation
        assert "dangerous pattern" not in str(result.get("stderr", ""))
    
    def test_output_truncation(self):
        """Test output truncation for large outputs."""
        # Create a command that produces large output
        if platform.system() == "Windows":
            # Windows command to generate large output
            large_command = "for /L %i in (1,1,1000) do @echo This is line %i with some additional text to make it longer"
        else:
            # Unix command to generate large output
            large_command = "for i in {1..1000}; do echo 'This is line $i with some additional text to make it longer'; done"
        
        result = self.tool.execute(large_command, description="Generate large output")
        
        # Check if output was truncated (either by lines or characters)
        lines = result["output"].split('\n')
        if len(lines) > BashTool.MAX_LINES or len(result["output"]) > BashTool.MAX_OUTPUT_LENGTH:
            assert result["truncated"] is True
            assert "truncated" in result["output"].lower()
    
    def test_stderr_capture(self):
        """Test that stderr is properly captured."""
        if platform.system() == "Windows":
            # Windows command that outputs to stderr
            result = self.tool.execute("echo Error message 1>&2", description="Test stderr")
        else:
            # Unix command that outputs to stderr
            result = self.tool.execute("echo 'Error message' >&2", description="Test stderr")
        
        assert "Error message" in result["output"] or "Error message" in result["stderr"]
    
    def test_environment_variables(self):
        """Test that environment variables are accessible."""
        if platform.system() == "Windows":
            result = self.tool.execute("echo %PATH%", description="Test env var")
        else:
            result = self.tool.execute("echo $PATH", description="Test env var")
        
        assert result["success"] is True
        assert len(result["output"].strip()) > 0
    
    def test_multiline_output(self):
        """Test handling of multiline output."""
        if platform.system() == "Windows":
            command = "echo Line 1 & echo Line 2 & echo Line 3"
        else:
            command = "echo 'Line 1'; echo 'Line 2'; echo 'Line 3'"
        
        result = self.tool.execute(command, description="Test multiline")
        
        assert result["success"] is True
        lines = result["output"].strip().split('\n')
        assert len(lines) >= 3
        assert "Line 1" in result["output"]
        assert "Line 2" in result["output"]
        assert "Line 3" in result["output"]
    
    def test_unicode_handling(self):
        """Test handling of unicode characters in output."""
        if platform.system() == "Windows":
            # Windows might have encoding issues, so use simple test
            result = self.tool.execute("echo Hello", description="Test unicode")
        else:
            # Unix systems generally handle unicode better
            result = self.tool.execute("echo 'Hello 世界 🌍'", description="Test unicode")
        
        assert result["success"] is True
        assert len(result["output"]) > 0
    
    def test_convenience_function(self):
        """Test the convenience function."""
        result = execute_bash_command("echo 'Convenience test'", description="Test convenience")
        
        assert result["success"] is True
        assert "Convenience test" in result["output"]
        assert result["description"] == "Test convenience"
    
    def test_default_description(self):
        """Test that default description is generated when not provided."""
        result = self.tool.execute("echo test")
        
        assert result["description"].startswith("Execute:")
        assert "echo test" in result["description"]
    
    def test_long_command_description_truncation(self):
        """Test that long commands get truncated in default description."""
        long_command = "echo " + "a" * 100
        result = self.tool.execute(long_command)
        
        assert result["description"].startswith("Execute:")
        assert "..." in result["description"]
        assert len(result["description"]) < len(long_command) + 20
    
    def test_shell_detection(self):
        """Test that appropriate shell is detected."""
        tool = BashTool()
        shell = tool._get_shell()
        
        if platform.system() == "Windows":
            assert shell in ["powershell", "cmd"]
        else:
            assert shell.endswith(("bash", "sh", "zsh", "fish"))
    
    def test_working_directory_persistence(self):
        """Test that working directory is properly set and reported."""
        result = self.tool.execute("pwd" if platform.system() != "Windows" else "cd", 
                                 workdir=self.temp_dir, 
                                 description="Check working directory")
        
        assert result["working_directory"] == self.temp_dir
        # The output should contain the temp directory path
        assert self.temp_dir in result["output"] or os.path.basename(self.temp_dir) in result["output"]
    
    def test_exit_code_capture(self):
        """Test that exit codes are properly captured."""
        if platform.system() == "Windows":
            # Windows command that exits with code 1
            result = self.tool.execute("exit 1", description="Test exit code")
        else:
            # Unix command that exits with code 1
            result = self.tool.execute("exit 1", description="Test exit code")
        
        assert result["success"] is False
        assert result["exit_code"] == 1
    
    def test_command_chaining(self):
        """Test command chaining with && operator."""
        if platform.system() == "Windows":
            result = self.tool.execute("echo First && echo Second", description="Test chaining")
        else:
            result = self.tool.execute("echo 'First' && echo 'Second'", description="Test chaining")
        
        assert result["success"] is True
        assert "First" in result["output"]
        assert "Second" in result["output"]
    
    def test_failed_command_chaining(self):
        """Test that command chaining stops on failure."""
        if platform.system() == "Windows":
            result = self.tool.execute("nonexistent_cmd && echo Should not appear", description="Test failed chaining")
        else:
            result = self.tool.execute("false && echo 'Should not appear'", description="Test failed chaining")
        
        assert result["success"] is False
        assert "Should not appear" not in result["output"]


if __name__ == "__main__":
    # Run a simple test if executed directly
    tool = BashTool()
    
    print("Testing basic functionality...")
    
    # Test basic command
    result = tool.execute("echo 'Test successful!'", description="Basic test")
    print(f"Basic test - Success: {result['success']}, Output: {result['output'].strip()}")
    
    # Test timeout
    print("\nTesting timeout...")
    if platform.system() == "Windows":
        result = tool.execute("timeout 3", timeout=1, description="Timeout test")
    else:
        result = tool.execute("sleep 3", timeout=1, description="Timeout test")
    print(f"Timeout test - Timeout exceeded: {result['timeout_exceeded']}")
    
    print("\nAll basic tests completed!")
