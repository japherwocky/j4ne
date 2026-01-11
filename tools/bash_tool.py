"""
Bash tool for executing shell commands with cross-platform Windows support.

This tool provides a unified interface for shell command execution that works
across Unix-like systems and Windows, with intelligent shell detection and
command translation capabilities.
"""

import os
import sys
import subprocess
import platform
import shutil
import time
import signal
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod


class BashToolError(Exception):
    """Exception raised by bash tool operations."""
    pass


@dataclass
class CommandResult:
    """Result of a command execution."""
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool
    aborted: bool
    description: str


class ShellManager(ABC):
    """Abstract base class for shell managers."""
    
    @abstractmethod
    def get_shell_command(self) -> List[str]:
        """Get the shell command to use for execution."""
        pass
    
    @abstractmethod
    def prepare_command(self, command: str, workdir: str) -> str:
        """Prepare the command for execution in this shell."""
        pass
    
    @abstractmethod
    def kill_process_tree(self, process: subprocess.Popen) -> None:
        """Kill a process and its children."""
        pass


class UnixShellManager(ShellManager):
    """Shell manager for Unix-like systems."""
    
    def __init__(self):
        self.shell_path = self._detect_shell()
    
    def _detect_shell(self) -> str:
        """Detect the best available shell."""
        # Check SHELL environment variable first
        shell_env = os.environ.get('SHELL')
        if shell_env and os.path.exists(shell_env):
            return shell_env
        
        # Try common shells in order of preference
        shells = ['/bin/bash', '/usr/bin/bash', '/bin/zsh', '/usr/bin/zsh', '/bin/sh']
        for shell in shells:
            if os.path.exists(shell):
                return shell
        
        # Fallback to sh
        return '/bin/sh'
    
    def get_shell_command(self) -> List[str]:
        """Get the shell command to use for execution."""
        return [self.shell_path, '-c']
    
    def prepare_command(self, command: str, workdir: str) -> str:
        """Prepare the command for execution in Unix shell."""
        # Change to workdir and execute command
        return f'cd "{workdir}" && {command}'
    
    def kill_process_tree(self, process: subprocess.Popen) -> None:
        """Kill a process and its children on Unix."""
        if process.poll() is None:
            try:
                # Kill the process group
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                time.sleep(0.2)
                if process.poll() is None:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except (OSError, ProcessLookupError):
                # Fallback to killing just the process
                try:
                    process.terminate()
                    time.sleep(0.2)
                    if process.poll() is None:
                        process.kill()
                except (OSError, ProcessLookupError):
                    pass


class WindowsShellManager(ShellManager):
    """Shell manager for Windows systems."""
    
    def __init__(self):
        self.shell_type, self.shell_command = self._detect_shell()
    
    def _detect_shell(self) -> Tuple[str, List[str]]:
        """Detect the best available shell on Windows."""
        # 1. Try Git Bash first (best compatibility)
        git_bash = self._find_git_bash()
        if git_bash:
            return 'git_bash', [git_bash, '-c']
        
        # 2. Try WSL bash
        wsl_bash = shutil.which('bash')
        if wsl_bash and 'wsl' in wsl_bash.lower():
            return 'wsl_bash', [wsl_bash, '-c']
        
        # 3. Try PowerShell Core (pwsh)
        pwsh = shutil.which('pwsh')
        if pwsh:
            return 'powershell_core', [pwsh, '-Command']
        
        # 4. Try Windows PowerShell
        powershell = shutil.which('powershell')
        if powershell:
            return 'powershell', [powershell, '-Command']
        
        # 5. Fallback to cmd.exe
        cmd = os.environ.get('COMSPEC', 'cmd.exe')
        return 'cmd', [cmd, '/c']
    
    def _find_git_bash(self) -> Optional[str]:
        """Find Git Bash executable on Windows."""
        # Check environment variable first
        git_bash_path = os.environ.get('OPENCODE_GIT_BASH_PATH')
        if git_bash_path and os.path.exists(git_bash_path):
            return git_bash_path
        
        # Try to find git and derive bash path
        git_exe = shutil.which('git')
        if git_exe:
            # git.exe is typically at: C:\Program Files\Git\cmd\git.exe
            # bash.exe is at: C:\Program Files\Git\bin\bash.exe
            git_dir = Path(git_exe).parent.parent
            bash_path = git_dir / 'bin' / 'bash.exe'
            if bash_path.exists():
                return str(bash_path)
        
        # Try common installation paths
        common_paths = [
            r'C:\Program Files\Git\bin\bash.exe',
            r'C:\Program Files (x86)\Git\bin\bash.exe',
            r'C:\Git\bin\bash.exe',
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def get_shell_command(self) -> List[str]:
        """Get the shell command to use for execution."""
        return self.shell_command
    
    def prepare_command(self, command: str, workdir: str) -> str:
        """Prepare the command for execution in Windows shell."""
        if self.shell_type in ['git_bash', 'wsl_bash']:
            # Use Unix-style commands for bash
            # Convert Windows paths to Unix-style for Git Bash
            if self.shell_type == 'git_bash':
                workdir = self._windows_to_git_bash_path(workdir)
            return f'cd "{workdir}" && {command}'
        
        elif self.shell_type in ['powershell', 'powershell_core']:
            # Use PowerShell syntax
            return f'Set-Location "{workdir}"; {command}'
        
        else:  # cmd
            # Use cmd syntax
            return f'cd /d "{workdir}" && {command}'
    
    def _windows_to_git_bash_path(self, path: str) -> str:
        """Convert Windows path to Git Bash compatible path."""
        # Convert C:\Users\... to /c/Users/...
        if len(path) >= 3 and path[1] == ':':
            drive = path[0].lower()
            rest = path[2:].replace('\\', '/')
            return f'/{drive}{rest}'
        return path.replace('\\', '/')
    
    def kill_process_tree(self, process: subprocess.Popen) -> None:
        """Kill a process and its children on Windows."""
        if process.poll() is None:
            try:
                # Use taskkill to kill the process tree
                subprocess.run([
                    'taskkill', '/pid', str(process.pid), '/f', '/t'
                ], capture_output=True, timeout=5)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # Fallback to terminate/kill
                try:
                    process.terminate()
                    time.sleep(0.2)
                    if process.poll() is None:
                        process.kill()
                except (OSError, ProcessLookupError):
                    pass


def get_shell_manager() -> ShellManager:
    """Get the appropriate shell manager for the current platform."""
    if platform.system() == 'Windows':
        return WindowsShellManager()
    else:
        return UnixShellManager()


def validate_command_security(command: str) -> None:
    """Basic security validation for commands."""
    # This is a simplified version - in production you'd want tree-sitter parsing
    dangerous_patterns = [
        'rm -rf /',
        'del /s /q c:\\',
        'format c:',
        'dd if=/dev/zero',
        ':(){ :|:& };:',  # Fork bomb
    ]
    
    command_lower = command.lower().strip()
    for pattern in dangerous_patterns:
        if pattern in command_lower:
            raise BashToolError(f"Command contains potentially dangerous pattern: {pattern}")


def execute_command(
    command: str,
    workdir: Optional[str] = None,
    timeout: Optional[int] = None,
    description: str = "",
    max_output_length: int = 30000
) -> CommandResult:
    """
    Execute a shell command with cross-platform support.
    
    Args:
        command: The command to execute
        workdir: Working directory (defaults to current directory)
        timeout: Timeout in seconds (defaults to 120)
        description: Description of what the command does
        max_output_length: Maximum length of output to capture
    
    Returns:
        CommandResult with execution details
    """
    if not command.strip():
        raise BashToolError("Command cannot be empty")
    
    if timeout is not None and timeout <= 0:
        raise BashToolError(f"Invalid timeout value: {timeout}. Timeout must be positive.")
    
    # Default values
    if workdir is None:
        workdir = os.getcwd()
    if timeout is None:
        timeout = 120  # 2 minutes default
    
    # Validate working directory
    workdir = os.path.abspath(workdir)
    if not os.path.exists(workdir):
        raise BashToolError(f"Working directory does not exist: {workdir}")
    if not os.path.isdir(workdir):
        raise BashToolError(f"Working directory is not a directory: {workdir}")
    
    # Basic security validation
    validate_command_security(command)
    
    # Get shell manager
    shell_manager = get_shell_manager()
    
    # Prepare command
    shell_command = shell_manager.get_shell_command()
    prepared_command = shell_manager.prepare_command(command, workdir)
    full_command = shell_command + [prepared_command]
    
    # Execute command
    stdout_data = ""
    stderr_data = ""
    timed_out = False
    aborted = False
    
    try:
        # Start process
        if platform.system() == 'Windows':
            process = subprocess.Popen(
                full_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=workdir,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            process = subprocess.Popen(
                full_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=workdir,
                preexec_fn=os.setsid
            )
        
        # Wait for completion with timeout
        try:
            stdout_data, stderr_data = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            shell_manager.kill_process_tree(process)
            try:
                stdout_data, stderr_data = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                stdout_data, stderr_data = "", ""
        
        exit_code = process.returncode if process.returncode is not None else -1
        
    except Exception as e:
        raise BashToolError(f"Failed to execute command: {e}")
    
    # Truncate output if too long
    if len(stdout_data) > max_output_length:
        stdout_data = stdout_data[:max_output_length] + "\n\n[Output truncated...]"
    if len(stderr_data) > max_output_length:
        stderr_data = stderr_data[:max_output_length] + "\n\n[Error output truncated...]"
    
    return CommandResult(
        stdout=stdout_data,
        stderr=stderr_data,
        exit_code=exit_code,
        timed_out=timed_out,
        aborted=aborted,
        description=description
    )


def bash_command(
    command: str,
    workdir: Optional[str] = None,
    timeout: Optional[int] = None,
    description: str = ""
) -> Dict[str, Any]:
    """
    Execute a bash command and return formatted result.
    
    This is the main interface function that matches the OpenCode bash tool API.
    
    Args:
        command: The command to execute
        workdir: Working directory (optional)
        timeout: Timeout in seconds (optional, defaults to 120)
        description: Description of what the command does
    
    Returns:
        Dictionary with title, output, and metadata
    """
    try:
        result = execute_command(command, workdir, timeout, description)
        
        # Combine stdout and stderr
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            if output:
                output += "\n"
            output += result.stderr
        
        # Add metadata if command was terminated
        metadata_notes = []
        if result.timed_out:
            metadata_notes.append(f"Command terminated after exceeding timeout {timeout}s")
        if result.aborted:
            metadata_notes.append("Command was aborted")
        
        if metadata_notes:
            output += "\n\n<bash_metadata>\n" + "\n".join(metadata_notes) + "\n</bash_metadata>"
        
        return {
            'title': description or command,
            'output': output,
            'metadata': {
                'exit_code': result.exit_code,
                'description': description,
                'timed_out': result.timed_out,
                'aborted': result.aborted,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        }
        
    except BashToolError as e:
        return {
            'title': f"Error: {description or command}",
            'output': f"Error: {str(e)}",
            'metadata': {
                'exit_code': -1,
                'description': description,
                'error': str(e)
            }
        }


def get_shell_info() -> Dict[str, Any]:
    """Get information about the detected shell."""
    shell_manager = get_shell_manager()
    
    info = {
        'platform': platform.system(),
        'shell_command': shell_manager.get_shell_command(),
    }
    
    if isinstance(shell_manager, WindowsShellManager):
        info['shell_type'] = shell_manager.shell_type
    else:
        info['shell_path'] = shell_manager.shell_path
    
    return info


if __name__ == "__main__":
    # Test the bash tool
    print("Shell Info:", get_shell_info())
    
    # Test basic command
    result = bash_command("echo 'Hello, World!'", description="Test echo command")
    print("Test Result:", result)
    
    # Test with working directory
    result = bash_command("pwd", workdir="/tmp", description="Show current directory")
    print("PWD Result:", result)
