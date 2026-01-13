"""
Bash Tool for j4ne

Executes shell commands with proper security, timeout handling, and output management.
Based on OpenCode's bash tool implementation.
"""

import os
import subprocess
import signal
import threading
import time
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import shlex
import platform


class BashToolError(Exception):
    """Exception raised by the bash tool."""
    pass


class BashTool:
    """
    Tool for executing shell commands with security and timeout handling.
    
    Features:
    - Command execution with configurable timeout
    - Working directory support
    - Output truncation for large outputs
    - Cross-platform process termination
    - Security validation for dangerous commands
    """
    
    # Constants
    DEFAULT_TIMEOUT = 120  # 2 minutes in seconds
    MAX_OUTPUT_LENGTH = 30_000  # Maximum characters in output
    MAX_LINES = 2000  # Maximum lines in output
    MAX_BYTES = 1_000_000  # Maximum bytes in output
    
    # Dangerous commands that require extra caution
    DANGEROUS_COMMANDS = {
        'rm', 'rmdir', 'del', 'format', 'fdisk', 'mkfs', 'dd',
        'shutdown', 'reboot', 'halt', 'poweroff', 'init',
        'kill', 'killall', 'pkill', 'taskkill',
        'chmod', 'chown', 'chgrp', 'passwd', 'su', 'sudo',
        'mv', 'move', 'ren', 'rename'
    }
    
    def __init__(self, working_directory: Optional[str] = None):
        """
        Initialize the bash tool.
        
        Args:
            working_directory: Default working directory for commands
        """
        self.working_directory = working_directory or os.getcwd()
        self.shell = self._get_shell()
    
    def _get_shell(self) -> str:
        """Get the appropriate shell for the current platform."""
        if platform.system() == "Windows":
            # Try PowerShell first, fall back to cmd
            if shutil.which("powershell"):
                return "powershell"
            return "cmd"
        else:
            # Unix-like systems
            return os.environ.get("SHELL", "/bin/bash")
    
    def _validate_command(self, command: str) -> None:
        """
        Validate command for basic security.
        
        Args:
            command: The command to validate
            
        Raises:
            BashToolError: If command is deemed unsafe
        """
        # Basic validation - check for dangerous patterns
        command_lower = command.lower().strip()
        
        # Check for dangerous command patterns
        first_word = command_lower.split()[0] if command_lower.split() else ""
        
        if first_word in self.DANGEROUS_COMMANDS:
            # Allow some safe patterns
            if first_word == "rm" and ("-h" in command_lower or "--help" in command_lower):
                return
            if first_word == "chmod" and ("-h" in command_lower or "--help" in command_lower):
                return
                
            # For now, just warn but don't block - in production you might want stricter validation
            pass
        
        # Check for command injection patterns
        dangerous_patterns = [
            "; rm -rf",
            "&& rm -rf", 
            "| rm -rf",
            "; del /",
            "&& del /",
            "| del /",
            "$(rm",
            "`rm",
            "format c:",
            "shutdown -",
            "reboot -",
        ]
        
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                raise BashToolError(f"Command contains potentially dangerous pattern: {pattern}")
    
    def _kill_process_tree(self, process: subprocess.Popen) -> None:
        """
        Kill a process and all its children.
        
        Args:
            process: The process to kill
        """
        try:
            if platform.system() == "Windows":
                # Windows process termination
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                    capture_output=True,
                    timeout=5
                )
            else:
                # Unix process termination
                try:
                    # Try to terminate gracefully first
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    time.sleep(0.5)
                    
                    # If still running, force kill
                    if process.poll() is None:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except (OSError, ProcessLookupError):
                    # Process might already be dead
                    pass
        except Exception:
            # Last resort - try to kill the process directly
            try:
                process.kill()
            except:
                pass
    
    def _truncate_output(self, output: str) -> Tuple[str, bool]:
        """
        Truncate output if it's too long.
        
        Args:
            output: The output to potentially truncate
            
        Returns:
            Tuple of (truncated_output, was_truncated)
        """
        was_truncated = False
        
        # Check length limits
        if len(output) > self.MAX_OUTPUT_LENGTH:
            output = output[:self.MAX_OUTPUT_LENGTH] + "\n\n[Output truncated - exceeded character limit]"
            was_truncated = True
        
        # Check line limits
        lines = output.split('\n')
        if len(lines) > self.MAX_LINES:
            output = '\n'.join(lines[:self.MAX_LINES]) + "\n\n[Output truncated - exceeded line limit]"
            was_truncated = True
        
        # Check byte limits
        if len(output.encode('utf-8')) > self.MAX_BYTES:
            # Binary search to find the right truncation point
            while len(output.encode('utf-8')) > self.MAX_BYTES and output:
                output = output[:len(output)//2]
            output += "\n\n[Output truncated - exceeded byte limit]"
            was_truncated = True
        
        return output, was_truncated
    
    def execute(
        self,
        command: str,
        timeout: Optional[float] = None,
        workdir: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a shell command.
        
        Args:
            command: The command to execute
            timeout: Timeout in seconds (default: 120)
            workdir: Working directory (default: self.working_directory)
            description: Human-readable description of what the command does
            
        Returns:
            Dictionary with execution results:
            - success: bool - Whether command succeeded
            - exit_code: int - Process exit code
            - stdout: str - Standard output
            - stderr: str - Standard error
            - output: str - Combined stdout and stderr
            - timeout_exceeded: bool - Whether timeout was exceeded
            - truncated: bool - Whether output was truncated
            - description: str - Command description
            - command: str - The executed command
            - working_directory: str - Directory where command was executed
        """
        # Set defaults
        timeout = timeout or self.DEFAULT_TIMEOUT
        workdir = workdir or self.working_directory
        description = description or f"Execute: {command[:50]}{'...' if len(command) > 50 else ''}"
        
        # Validate inputs
        if timeout <= 0:
            raise BashToolError(f"Invalid timeout: {timeout}. Must be positive.")
        
        if not os.path.exists(workdir):
            raise BashToolError(f"Working directory does not exist: {workdir}")
        
        # Validate command
        self._validate_command(command)
        
        # Prepare execution environment
        env = os.environ.copy()
        
        # Set up process creation parameters
        if platform.system() == "Windows":
            # Windows-specific setup
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
            shell = True
        else:
            # Unix-specific setup
            creation_flags = 0
            shell = True
        
        stdout_data = ""
        stderr_data = ""
        combined_output = ""
        timeout_exceeded = False
        
        try:
            # Start the process
            process = subprocess.Popen(
                command,
                shell=shell,
                cwd=workdir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                creationflags=creation_flags if platform.system() == "Windows" else 0,
                preexec_fn=os.setsid if platform.system() != "Windows" else None
            )
            
            # Wait for completion with timeout
            try:
                stdout_data, stderr_data = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                timeout_exceeded = True
                # Kill the process tree
                self._kill_process_tree(process)
                
                # Try to get partial output
                try:
                    stdout_data, stderr_data = process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    stdout_data = ""
                    stderr_data = ""
            
            exit_code = process.returncode
            
        except Exception as e:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Failed to execute command: {str(e)}",
                "output": f"Failed to execute command: {str(e)}",
                "timeout_exceeded": False,
                "truncated": False,
                "description": description,
                "command": command,
                "working_directory": workdir
            }
        
        # Combine output
        combined_output = ""
        if stdout_data:
            combined_output += stdout_data
        if stderr_data:
            if combined_output:
                combined_output += "\n" + stderr_data
            else:
                combined_output = stderr_data
        
        # Add timeout information if needed
        if timeout_exceeded:
            timeout_msg = f"\n\n<bash_metadata>\nCommand terminated after exceeding timeout of {timeout} seconds\n</bash_metadata>"
            combined_output += timeout_msg
            stderr_data += timeout_msg
        
        # Truncate output if necessary
        combined_output, truncated = self._truncate_output(combined_output)
        
        # Determine success
        success = exit_code == 0 and not timeout_exceeded
        
        return {
            "success": success,
            "exit_code": exit_code,
            "stdout": stdout_data,
            "stderr": stderr_data,
            "output": combined_output,
            "timeout_exceeded": timeout_exceeded,
            "truncated": truncated,
            "description": description,
            "command": command,
            "working_directory": workdir
        }


# Convenience function for direct usage
def execute_bash_command(
    command: str,
    timeout: Optional[float] = None,
    workdir: Optional[str] = None,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute a bash command using the BashTool.
    
    Args:
        command: The command to execute
        timeout: Timeout in seconds
        workdir: Working directory
        description: Human-readable description
        
    Returns:
        Dictionary with execution results
    """
    tool = BashTool()
    return tool.execute(command, timeout, workdir, description)


if __name__ == "__main__":
    # Example usage
    tool = BashTool()
    
    # Test basic command
    result = tool.execute("echo 'Hello, World!'", description="Test echo command")
    print("Echo test:")
    print(f"Success: {result['success']}")
    print(f"Output: {result['output']}")
    print()
    
    # Test directory listing
    result = tool.execute("ls -la", description="List current directory")
    print("Directory listing:")
    print(f"Success: {result['success']}")
    print(f"Output: {result['output'][:200]}...")
    print()
    
    # Test timeout
    result = tool.execute("sleep 5", timeout=2, description="Test timeout")
    print("Timeout test:")
    print(f"Success: {result['success']}")
    print(f"Timeout exceeded: {result['timeout_exceeded']}")
    print(f"Output: {result['output']}")
