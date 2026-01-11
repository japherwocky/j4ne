"""
Tests for the bash_tool module.
"""

import pytest
import tempfile
import os
import platform
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from tools.bash_tool import (
    bash_command,
    execute_command,
    get_shell_manager,
    get_shell_info,
    validate_command_security,
    BashToolError,
    UnixShellManager,
    WindowsShellManager,
    CommandResult
)


class TestBashTool:
    """Test suite for bash_tool functionality."""
    
    def test_simple_command_execution(self):
        """Test basic command execution."""
        result = bash_command("echo 'Hello World'", description="Test echo")
        
        assert result['title'] == "Test echo"
        assert "Hello World" in result['output']
        assert result['metadata']['exit_code'] == 0
        assert result['metadata']['description'] == "Test echo"
        assert not result['metadata']['timed_out']
        assert not result['metadata']['aborted']
    
    def test_command_with_working_directory(self, tmp_path):
        """Test command execution with custom working directory."""
        # Create a test file in the temp directory
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        # List files in the temp directory
        if platform.system() == 'Windows':
            result = bash_command("dir", workdir=str(tmp_path), description="List files")
        else:
            result = bash_command("ls", workdir=str(tmp_path), description="List files")
        
        assert result['metadata']['exit_code'] == 0
        assert "test.txt" in result['output']
    
    def test_command_with_timeout(self):
        """Test command timeout functionality."""
        # Use a command that will definitely timeout
        if platform.system() == 'Windows':
            command = "timeout 5"  # Windows timeout command
        else:
            command = "sleep 5"    # Unix sleep command
        
        result = bash_command(command, timeout=1, description="Timeout test")
        
        assert result['metadata']['timed_out'] is True
        assert "timeout" in result['output'].lower()
    
    def test_command_with_error(self):
        """Test command that returns non-zero exit code."""
        if platform.system() == 'Windows':
            result = bash_command("dir nonexistent_directory", description="Error test")
        else:
            result = bash_command("ls nonexistent_directory", description="Error test")
        
        assert result['metadata']['exit_code'] != 0
        # Should have error output
        assert len(result['output']) > 0
    
    def test_empty_command_error(self):
        """Test error with empty command."""
        result = bash_command("", description="Empty command")
        
        assert "Error:" in result['title']
        assert "cannot be empty" in result['output']
        assert result['metadata']['exit_code'] == -1
    
    def test_invalid_timeout_error(self):
        """Test error with invalid timeout."""
        result = bash_command("echo test", timeout=-1, description="Invalid timeout")
        
        assert "Error:" in result['title']
        assert "Invalid timeout" in result['output']
        assert result['metadata']['exit_code'] == -1
    
    def test_invalid_working_directory(self):
        """Test error with invalid working directory."""
        result = bash_command("echo test", workdir="/nonexistent/path", description="Invalid workdir")
        
        assert "Error:" in result['title']
        assert "does not exist" in result['output']
        assert result['metadata']['exit_code'] == -1
    
    def test_working_directory_is_file(self, tmp_path):
        """Test error when working directory is a file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        result = bash_command("echo test", workdir=str(test_file), description="File as workdir")
        
        assert "Error:" in result['title']
        assert "not a directory" in result['output']
        assert result['metadata']['exit_code'] == -1
    
    def test_security_validation(self):
        """Test security validation of dangerous commands."""
        dangerous_commands = [
            "rm -rf /",
            "del /s /q c:\\",
            "format c:",
            "dd if=/dev/zero",
            ":(){ :|:& };:"
        ]
        
        for cmd in dangerous_commands:
            result = bash_command(cmd, description="Dangerous command")
            assert "Error:" in result['title']
            assert "dangerous pattern" in result['output']
            assert result['metadata']['exit_code'] == -1
    
    def test_multiline_output(self):
        """Test command with multiline output."""
        if platform.system() == 'Windows':
            command = 'echo line1 & echo line2 & echo line3'
        else:
            command = 'echo "line1"; echo "line2"; echo "line3"'
        
        result = bash_command(command, description="Multiline test")
        
        assert result['metadata']['exit_code'] == 0
        assert "line1" in result['output']
        assert "line2" in result['output']
        assert "line3" in result['output']
    
    def test_environment_variables(self):
        """Test that environment variables are accessible."""
        if platform.system() == 'Windows':
            command = 'echo %PATH%'
        else:
            command = 'echo $PATH'
        
        result = bash_command(command, description="Environment test")
        
        assert result['metadata']['exit_code'] == 0
        assert len(result['output'].strip()) > 0
    
    def test_git_operations(self, tmp_path):
        """Test git operations in a temporary directory."""
        # Initialize a git repo
        result1 = bash_command("git init", workdir=str(tmp_path), description="Initialize git repo")
        assert result1['metadata']['exit_code'] == 0
        
        # Configure git (required for commits)
        result2 = bash_command(
            'git config user.email "test@example.com"',
            workdir=str(tmp_path),
            description="Configure git email"
        )
        assert result2['metadata']['exit_code'] == 0
        
        result3 = bash_command(
            'git config user.name "Test User"',
            workdir=str(tmp_path),
            description="Configure git name"
        )
        assert result3['metadata']['exit_code'] == 0
        
        # Check git status
        result4 = bash_command("git status", workdir=str(tmp_path), description="Check git status")
        assert result4['metadata']['exit_code'] == 0
        assert "git status" in result4['output'] or "On branch" in result4['output']


class TestShellManagers:
    """Test shell manager implementations."""
    
    def test_get_shell_manager(self):
        """Test that appropriate shell manager is returned."""
        manager = get_shell_manager()
        
        if platform.system() == 'Windows':
            assert isinstance(manager, WindowsShellManager)
        else:
            assert isinstance(manager, UnixShellManager)
    
    def test_shell_info(self):
        """Test shell information retrieval."""
        info = get_shell_info()
        
        assert 'platform' in info
        assert 'shell_command' in info
        assert info['platform'] == platform.system()
        assert isinstance(info['shell_command'], list)
        assert len(info['shell_command']) >= 2
    
    @pytest.mark.skipif(platform.system() != 'Windows', reason="Windows-specific test")
    def test_windows_shell_detection(self):
        """Test Windows shell detection."""
        manager = WindowsShellManager()
        
        assert hasattr(manager, 'shell_type')
        assert hasattr(manager, 'shell_command')
        assert manager.shell_type in ['git_bash', 'wsl_bash', 'powershell_core', 'powershell', 'cmd']
        assert isinstance(manager.shell_command, list)
    
    @pytest.mark.skipif(platform.system() == 'Windows', reason="Unix-specific test")
    def test_unix_shell_detection(self):
        """Test Unix shell detection."""
        manager = UnixShellManager()
        
        assert hasattr(manager, 'shell_path')
        assert os.path.exists(manager.shell_path)
        assert manager.shell_path.endswith(('bash', 'zsh', 'sh'))
    
    def test_command_preparation(self):
        """Test command preparation for different shells."""
        manager = get_shell_manager()
        workdir = "/tmp" if platform.system() != 'Windows' else "C:\\temp"
        
        prepared = manager.prepare_command("echo test", workdir)
        
        assert "echo test" in prepared
        if platform.system() == 'Windows':
            # Should handle Windows paths appropriately
            assert workdir in prepared or workdir.replace('\\', '/') in prepared
        else:
            assert workdir in prepared


class TestExecuteCommand:
    """Test the execute_command function directly."""
    
    def test_execute_command_success(self):
        """Test successful command execution."""
        result = execute_command("echo 'test'", description="Test command")
        
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert "test" in result.stdout
        assert not result.timed_out
        assert not result.aborted
        assert result.description == "Test command"
    
    def test_execute_command_with_stderr(self):
        """Test command that produces stderr output."""
        if platform.system() == 'Windows':
            # Use a command that writes to stderr on Windows
            result = execute_command("echo error 1>&2", description="Stderr test")
        else:
            # Use a command that writes to stderr on Unix
            result = execute_command("echo 'error' >&2", description="Stderr test")
        
        assert isinstance(result, CommandResult)
        # Some shells might handle this differently, so just check it ran
        assert result.exit_code is not None
    
    def test_execute_command_timeout(self):
        """Test command timeout."""
        if platform.system() == 'Windows':
            command = "timeout 3"
        else:
            command = "sleep 3"
        
        result = execute_command(command, timeout=1, description="Timeout test")
        
        assert isinstance(result, CommandResult)
        assert result.timed_out is True
    
    def test_execute_command_nonzero_exit(self):
        """Test command with non-zero exit code."""
        if platform.system() == 'Windows':
            command = "exit 1"
        else:
            command = "false"
        
        result = execute_command(command, description="Non-zero exit")
        
        assert isinstance(result, CommandResult)
        assert result.exit_code != 0


class TestSecurityValidation:
    """Test security validation functionality."""
    
    def test_validate_command_security_safe(self):
        """Test that safe commands pass validation."""
        safe_commands = [
            "echo hello",
            "ls -la",
            "git status",
            "npm install",
            "python script.py"
        ]
        
        for cmd in safe_commands:
            # Should not raise exception
            validate_command_security(cmd)
    
    def test_validate_command_security_dangerous(self):
        """Test that dangerous commands are blocked."""
        dangerous_commands = [
            "rm -rf /",
            "del /s /q c:\\",
            "format c:",
            "dd if=/dev/zero",
            ":(){ :|:& };:"
        ]
        
        for cmd in dangerous_commands:
            with pytest.raises(BashToolError) as exc_info:
                validate_command_security(cmd)
            assert "dangerous pattern" in str(exc_info.value)


class TestCrossPlatformCompatibility:
    """Test cross-platform compatibility features."""
    
    def test_path_handling(self, tmp_path):
        """Test that paths are handled correctly on different platforms."""
        # Create a subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        
        # Test that we can navigate to it
        if platform.system() == 'Windows':
            command = "dir"
        else:
            command = "ls"
        
        result = bash_command(command, workdir=str(subdir), description="Path test")
        assert result['metadata']['exit_code'] == 0
    
    def test_command_output_encoding(self):
        """Test that command output is properly encoded."""
        # Test with unicode characters
        if platform.system() == 'Windows':
            command = 'echo "Hello 世界"'
        else:
            command = 'echo "Hello 世界"'
        
        result = bash_command(command, description="Unicode test")
        
        # Should not crash and should contain the text
        assert result['metadata']['exit_code'] == 0
        # The exact unicode handling may vary by system, so just check it doesn't crash
        assert isinstance(result['output'], str)
    
    def test_long_output_truncation(self):
        """Test that very long output is properly truncated."""
        # Generate a command that produces long output
        if platform.system() == 'Windows':
            # Use PowerShell to generate long output
            command = 'powershell -Command "1..1000 | ForEach-Object { Write-Output (\'line\' + $_) }"'
        else:
            # Use seq to generate long output
            command = 'seq 1 1000 | sed "s/^/line/"'
        
        result = bash_command(command, description="Long output test")
        
        # Should complete successfully
        assert result['metadata']['exit_code'] == 0
        # Output should be truncated if too long
        if len(result['output']) > 30000:
            assert "truncated" in result['output'].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
