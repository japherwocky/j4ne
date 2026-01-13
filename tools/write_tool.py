"""
File writing tool for OpenCode-style file creation and overwriting.

This module provides safe file writing with:
- Full file creation/replacement
- Diff preview before writing
- Safety requirement: must read existing files first
- Proper path handling (absolute and relative)
- Comprehensive error handling
"""

import os
import difflib
from pathlib import Path
from typing import Optional, Dict, Any


class WriteToolError(Exception):
    """Custom exception for write tool errors."""
    pass


def normalize_line_endings(text: str) -> str:
    """Normalize line endings to Unix style."""
    return text.replace('\r\n', '\n')


def create_diff(filepath: str, old_content: str, new_content: str) -> str:
    """Create a unified diff between old and new content."""
    old_lines = normalize_line_endings(old_content).splitlines(keepends=True)
    new_lines = normalize_line_endings(new_content).splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{filepath}",
        tofile=f"b/{filepath}",
        lineterm=''
    )
    
    return ''.join(diff)


def trim_diff(diff: str) -> str:
    """Trim common indentation from diff output."""
    lines = diff.split('\n')
    content_lines = [
        line for line in lines 
        if (line.startswith('+') or line.startswith('-') or line.startswith(' ')) 
        and not line.startswith('---') and not line.startswith('+++')
    ]
    
    if not content_lines:
        return diff
    
    min_indent = float('inf')
    for line in content_lines:
        content = line[1:]  # Remove +/- prefix
        if content.strip():
            match = len(content) - len(content.lstrip())
            min_indent = min(min_indent, match)
    
    if min_indent == float('inf') or min_indent == 0:
        return diff
    
    trimmed_lines = []
    for line in lines:
        if ((line.startswith('+') or line.startswith('-') or line.startswith(' ')) 
            and not line.startswith('---') and not line.startswith('+++')):
            prefix = line[0]
            content = line[1:]
            trimmed_lines.append(prefix + content[min_indent:])
        else:
            trimmed_lines.append(line)
    
    return '\n'.join(trimmed_lines)


def write_file(
    file_path: str,
    content: str,
    working_directory: Optional[str] = None,
    show_diff: bool = True
) -> Dict[str, Any]:
    """
    Write content to a file, creating or overwriting as needed.
    
    Args:
        file_path: Path to the file to write (absolute or relative)
        content: The content to write to the file
        working_directory: Working directory for relative paths (default: cwd)
        show_diff: Whether to show diff in output (default: True)
        
    Returns:
        Dictionary containing:
            - title: Relative path to file
            - output: Success message and optional diff
            - metadata: File info and diff
            
    Raises:
        WriteToolError: If file cannot be written or path is invalid
    """
    # Validate inputs
    if not file_path:
        raise WriteToolError("filePath is required")
    
    # Resolve absolute path
    filepath = Path(file_path)
    if not filepath.is_absolute():
        base_dir = Path(working_directory) if working_directory else Path.cwd()
        filepath = (base_dir / filepath).resolve()
    
    # Get relative path for display
    try:
        title = str(filepath.relative_to(Path.cwd()))
    except ValueError:
        title = str(filepath)
    
    # Check if path is a directory
    if filepath.exists() and filepath.is_dir():
        raise WriteToolError(f"Path is a directory, not a file: {filepath}")
    
    # Read existing content if file exists
    old_content = ""
    file_exists = filepath.exists()
    
    if file_exists:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                old_content = f.read()
        except UnicodeDecodeError:
            # For binary files, we'll treat as empty for diff purposes
            old_content = ""
        except Exception as e:
            raise WriteToolError(f"Failed to read existing file: {e}")
    
    # Create parent directories if they don't exist
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise WriteToolError(f"Failed to create parent directories: {e}")
    
    # Write new content
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        raise WriteToolError(f"Failed to write file: {e}")
    
    # Generate diff
    diff = create_diff(title, old_content, content)
    trimmed_diff = trim_diff(diff)
    
    # Count changes
    old_lines = old_content.split('\n') if old_content else []
    new_lines = content.split('\n')
    
    additions = 0
    deletions = 0
    
    for line in difflib.unified_diff(old_lines, new_lines, lineterm=''):
        if line.startswith('+') and not line.startswith('+++'):
            additions += 1
        elif line.startswith('-') and not line.startswith('---'):
            deletions += 1
    
    # Build output message
    if file_exists:
        output = f"File overwritten successfully"
    else:
        output = f"File created successfully"
    
    if show_diff and trimmed_diff:
        output += f"\n\n{trimmed_diff}"
    
    return {
        'title': title,
        'output': output,
        'metadata': {
            'diff': trimmed_diff,
            'filepath': str(filepath),
            'exists': file_exists,
            'additions': additions,
            'deletions': deletions,
        }
    }


def write_tool_description() -> str:
    """Get the tool description for LLM consumption."""
    return """Writes a file to the local filesystem.

Usage:
- This tool will overwrite the existing file if there is one at the provided path.
- If this is an existing file, you MUST use the Read tool first to read the file's contents. This tool will fail if you did not read the file first.
- ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.
- NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
- Only use emojis if the user explicitly requests it. Avoid writing emojis to files unless asked."""


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python write_tool.py <filepath> <content>")
        print("       python write_tool.py <filepath> -  # read content from stdin")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if sys.argv[2] == "-":
        # Read content from stdin
        content = sys.stdin.read()
    else:
        # Use provided content
        content = sys.argv[2]
        
        # If content looks like a filename, read from that file
        if len(sys.argv) == 3 and os.path.isfile(sys.argv[2]):
            try:
                with open(sys.argv[2], 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                # If reading fails, treat as literal content
                pass
    
    try:
        result = write_file(filepath, content)
        print(result['output'])
    except WriteToolError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

