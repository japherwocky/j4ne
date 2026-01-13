"""
Smart file reading tool for OpenCode-style file operations.

This module provides a safe and intelligent file reading interface with:
- Line-based reading with offset/limit support
- Binary file detection
- File size limits (50KB default)
- Helpful file suggestions when file not found
- Line numbering in cat -n format
"""

import os
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import base64


# Constants matching OpenCode behavior
DEFAULT_READ_LIMIT = 2000
MAX_LINE_LENGTH = 2000
MAX_BYTES = 50 * 1024  # 50KB

# Binary file extensions (common non-text files)
BINARY_EXTENSIONS = {
    '.zip', '.tar', '.gz', '.exe', '.dll', '.so', '.class', '.jar', '.war',
    '.7z', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods',
    '.odp', '.bin', '.dat', '.obj', '.o', '.a', '.lib', '.wasm', '.pyc', '.pyo'
}


class ReadToolError(Exception):
    """Custom exception for read tool errors."""
    pass


def is_binary_file(filepath: Path) -> bool:
    """
    Detect if a file is binary.
    
    Args:
        filepath: Path to the file to check
        
    Returns:
        True if file is binary, False if text
    """
    # Check by extension first
    if filepath.suffix.lower() in BINARY_EXTENSIONS:
        return True
    
    # Check file contents
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(4096)
            
        if len(chunk) == 0:
            return False
            
        # Check for null bytes (strong indicator of binary)
        if b'\x00' in chunk:
            return True
            
        # Count non-printable characters
        non_printable = 0
        for byte in chunk:
            # Skip common whitespace characters
            if byte < 9 or (byte > 13 and byte < 32):
                non_printable += 1
                
        # If >30% non-printable, consider it binary
        return (non_printable / len(chunk)) > 0.3
        
    except Exception:
        return True


def get_file_suggestions(filepath: Path) -> List[str]:
    """
    Get suggested filenames when a file is not found.
    
    Args:
        filepath: The path that was not found
        
    Returns:
        List of up to 3 suggested file paths
    """
    directory = filepath.parent
    filename = filepath.name.lower()
    
    if not directory.exists():
        return []
    
    suggestions = []
    try:
        for entry in directory.iterdir():
            entry_name = entry.name.lower()
            # Suggest if there's a partial match
            if filename in entry_name or entry_name in filename:
                suggestions.append(str(entry))
                if len(suggestions) >= 3:
                    break
    except Exception:
        pass
        
    return suggestions


def is_image_file(filepath: Path) -> bool:
    """Check if file is an image (excluding SVG)."""
    mime_type, _ = mimetypes.guess_type(str(filepath))
    return mime_type and mime_type.startswith('image/') and mime_type != 'image/svg+xml'


def is_pdf_file(filepath: Path) -> bool:
    """Check if file is a PDF."""
    mime_type, _ = mimetypes.guess_type(str(filepath))
    return mime_type == 'application/pdf'


def read_file(
    file_path: str,
    offset: Optional[int] = None,
    limit: Optional[int] = None,
    working_directory: Optional[str] = None
) -> Dict[str, Any]:
    """
    Read a file from the filesystem with smart handling.
    
    Args:
        file_path: Path to the file to read (absolute or relative)
        offset: Starting line number (0-based, optional)
        limit: Number of lines to read (default: 2000)
        working_directory: Working directory for relative paths (default: cwd)
        
    Returns:
        Dictionary containing:
            - title: Relative path to file
            - output: File contents with line numbers
            - metadata: Additional info (preview, truncated status)
            - attachments: For images/PDFs (base64 encoded)
            
    Raises:
        ReadToolError: If file cannot be read or is binary
    """
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
    
    # Check if file exists
    if not filepath.exists():
        suggestions = get_file_suggestions(filepath)
        if suggestions:
            raise ReadToolError(
                f"File not found: {filepath}\n\n"
                f"Did you mean one of these?\n" + "\n".join(suggestions)
            )
        raise ReadToolError(f"File not found: {filepath}")
    
    # Handle images
    if is_image_file(filepath):
        with open(filepath, 'rb') as f:
            data = f.read()
        mime_type, _ = mimetypes.guess_type(str(filepath))
        encoded = base64.b64encode(data).decode('utf-8')
        
        return {
            'title': title,
            'output': 'Image read successfully',
            'metadata': {
                'preview': 'Image read successfully',
                'truncated': False,
            },
            'attachments': [{
                'type': 'file',
                'mime': mime_type,
                'url': f'data:{mime_type};base64,{encoded}',
            }]
        }
    
    # Handle PDFs
    if is_pdf_file(filepath):
        with open(filepath, 'rb') as f:
            data = f.read()
        encoded = base64.b64encode(data).decode('utf-8')
        
        return {
            'title': title,
            'output': 'PDF read successfully',
            'metadata': {
                'preview': 'PDF read successfully',
                'truncated': False,
            },
            'attachments': [{
                'type': 'file',
                'mime': 'application/pdf',
                'url': f'data:application/pdf;base64,{encoded}',
            }]
        }
    
    # Check for binary file
    if is_binary_file(filepath):
        raise ReadToolError(f"Cannot read binary file: {filepath}")
    
    # Read text file
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        raise ReadToolError(f"Cannot read file (encoding error): {filepath}")
    
    lines = content.split('\n')
    
    # Apply offset and limit
    offset = offset or 0
    limit = limit or DEFAULT_READ_LIMIT
    
    # Process lines with size limits
    raw_lines = []
    total_bytes = 0
    truncated_by_bytes = False
    
    for i in range(offset, min(len(lines), offset + limit)):
        line = lines[i]
        
        # Truncate very long lines
        if len(line) > MAX_LINE_LENGTH:
            line = line[:MAX_LINE_LENGTH] + "..."
        
        # Calculate size (including newline for all but first)
        line_size = len(line.encode('utf-8'))
        if raw_lines:
            line_size += 1  # newline character
            
        # Check size limit
        if total_bytes + line_size > MAX_BYTES:
            truncated_by_bytes = True
            break
            
        raw_lines.append(line)
        total_bytes += line_size
    
    # Format with line numbers (1-based, 5-digit padding)
    formatted_lines = []
    for idx, line in enumerate(raw_lines):
        line_num = offset + idx + 1
        formatted_lines.append(f"{line_num:05d}| {line}")
    
    # Build output
    output = "<file>\n"
    output += "\n".join(formatted_lines)
    
    # Add truncation info
    total_lines = len(lines)
    last_read_line = offset + len(raw_lines)
    has_more_lines = total_lines > last_read_line
    truncated = has_more_lines or truncated_by_bytes
    
    if truncated_by_bytes:
        output += f"\n\n(Output truncated at {MAX_BYTES} bytes. Use 'offset' parameter to read beyond line {last_read_line})"
    elif has_more_lines:
        output += f"\n\n(File has more lines. Use 'offset' parameter to read beyond line {last_read_line})"
    else:
        output += f"\n\n(End of file - total {total_lines} lines)"
    
    output += "\n</file>"
    
    # Generate preview (first 20 lines)
    preview = "\n".join(raw_lines[:20])
    
    return {
        'title': title,
        'output': output,
        'metadata': {
            'preview': preview,
            'truncated': truncated,
        }
    }


def read_tool_description() -> str:
    """Get the tool description for LLM consumption."""
    return """Reads a file from the local filesystem. You can access any file directly by using this tool.
Assume this tool is able to read all files on the machine. If the User provides a path to a file assume that path is valid. It is okay to read a file that does not exist; an error will be returned.

Usage:
- The filePath parameter must be an absolute path, not a relative path
- By default, it reads up to 2000 lines starting from the beginning of the file
- You can optionally specify a line offset and limit (especially handy for long files), but it's recommended to read the whole file by not providing these parameters
- Any lines longer than 2000 characters will be truncated
- Results are returned using cat -n format, with line numbers starting at 1
- You have the capability to call multiple tools in a single response. It is always better to speculatively read multiple files as a batch that are potentially useful.
- If you read a file that exists but has empty contents you will receive a system reminder warning in place of file contents.
- You can read image files using this tool."""


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python read_tool.py <filepath> [offset] [limit]")
        sys.exit(1)
    
    filepath = sys.argv[1]
    offset = int(sys.argv[2]) if len(sys.argv) > 2 else None
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    try:
        result = read_file(filepath, offset=offset, limit=limit)
        print(result['output'])
        if result.get('attachments'):
            print("\n[Note: File contains binary/image data]")
    except ReadToolError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

