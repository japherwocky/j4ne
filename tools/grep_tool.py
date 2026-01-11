"""
Content search tool using ripgrep for OpenCode-style file searching.

This module provides fast content search with:
- Regex pattern search using ripgrep
- File type filtering (*.js, *.{ts,tsx})
- Directory scoping
- Results sorted by modification time
- Line number and content display
"""

import os
import subprocess
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import shutil


class GrepToolError(Exception):
    """Custom exception for grep tool errors."""
    pass


def find_ripgrep() -> str:
    """Find the ripgrep executable."""
    rg_path = shutil.which('rg')
    if not rg_path:
        raise GrepToolError("ripgrep (rg) not found. Please install ripgrep.")
    return rg_path


def grep_search(
    pattern: str,
    search_path: Optional[str] = None,
    include: Optional[str] = None,
    max_results: int = 100,
    max_line_length: int = 2000
) -> Dict[str, Any]:
    """
    Search for a regex pattern in files using ripgrep.
    
    Args:
        pattern: The regex pattern to search for
        search_path: Directory to search in (default: current directory)
        include: File pattern to include (e.g. "*.js", "*.{ts,tsx}")
        max_results: Maximum number of results to return (default: 100)
        max_line_length: Maximum line length before truncation (default: 2000)
        
    Returns:
        Dictionary containing:
            - title: The search pattern
            - output: Formatted search results
            - metadata: Search statistics
            
    Raises:
        GrepToolError: If ripgrep fails or pattern is invalid
    """
    # Validate inputs
    if not pattern:
        raise GrepToolError("pattern is required")
    
    # Find ripgrep executable
    rg_path = find_ripgrep()
    
    # Resolve search path
    if search_path is None:
        search_path = os.getcwd()
    else:
        search_path = os.path.abspath(search_path)
    
    if not os.path.exists(search_path):
        raise GrepToolError(f"Search path does not exist: {search_path}")
    
    if not os.path.isdir(search_path):
        raise GrepToolError(f"Search path is not a directory: {search_path}")
    
    # Build ripgrep command
    args = [
        rg_path,
        "-nH",  # Show line numbers and filenames
        "--hidden",  # Search hidden files
        "--follow",  # Follow symlinks
        "--field-match-separator=|",  # Use | as separator
        "--regexp", pattern  # The regex pattern
    ]
    
    # Add file pattern filter if specified
    if include:
        args.extend(["--glob", include])
    
    # Add search path
    args.append(search_path)
    
    try:
        # Run ripgrep
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        
        # Handle different exit codes
        if result.returncode == 1:
            # No matches found
            return {
                'title': pattern,
                'output': "No files found",
                'metadata': {
                    'matches': 0,
                    'truncated': False,
                    'pattern': pattern,
                    'search_path': search_path,
                    'include': include
                }
            }
        
        if result.returncode != 0:
            # Error occurred
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            raise GrepToolError(f"ripgrep failed: {error_msg}")
        
        # Parse output
        output = result.stdout.strip()
        if not output:
            return {
                'title': pattern,
                'output': "No files found",
                'metadata': {
                    'matches': 0,
                    'truncated': False,
                    'pattern': pattern,
                    'search_path': search_path,
                    'include': include
                }
            }
        
        # Process matches
        matches = parse_ripgrep_output(output, max_line_length)
        
        # Sort by modification time (most recent first)
        matches = sort_matches_by_mtime(matches)
        
        # Apply result limit
        truncated = len(matches) > max_results
        if truncated:
            matches = matches[:max_results]
        
        # Format output
        output_text = format_matches(matches, pattern, truncated)
        
        return {
            'title': pattern,
            'output': output_text,
            'metadata': {
                'matches': len(matches),
                'truncated': truncated,
                'pattern': pattern,
                'search_path': search_path,
                'include': include
            }
        }
        
    except subprocess.TimeoutExpired:
        raise GrepToolError("Search timed out after 30 seconds")
    except Exception as e:
        raise GrepToolError(f"Search failed: {e}")


def parse_ripgrep_output(output: str, max_line_length: int) -> List[Dict[str, Any]]:
    """Parse ripgrep output into structured matches."""
    matches = []
    
    # Handle both Unix (\n) and Windows (\r\n) line endings
    lines = output.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Parse ripgrep output format: filepath|line_number|line_content
        parts = line.split('|', 2)
        if len(parts) < 3:
            continue
        
        file_path, line_num_str, line_text = parts
        
        try:
            line_num = int(line_num_str)
        except ValueError:
            continue
        
        # Truncate long lines
        if len(line_text) > max_line_length:
            line_text = line_text[:max_line_length] + "..."
        
        matches.append({
            'path': file_path,
            'line_num': line_num,
            'line_text': line_text
        })
    
    return matches


def sort_matches_by_mtime(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort matches by file modification time (most recent first)."""
    # Add modification time to each match
    for match in matches:
        try:
            stat = os.stat(match['path'])
            match['mtime'] = stat.st_mtime
        except (OSError, FileNotFoundError):
            # If we can't get mtime, use 0 (will sort to end)
            match['mtime'] = 0
    
    # Sort by modification time (descending)
    return sorted(matches, key=lambda x: x['mtime'], reverse=True)


def format_matches(matches: List[Dict[str, Any]], pattern: str, truncated: bool) -> str:
    """Format matches for display."""
    if not matches:
        return "No files found"
    
    output_lines = [f"Found {len(matches)} matches"]
    
    current_file = ""
    for match in matches:
        if current_file != match['path']:
            if current_file != "":
                output_lines.append("")
            current_file = match['path']
            output_lines.append(f"{match['path']}:")
        
        output_lines.append(f"  Line {match['line_num']}: {match['line_text']}")
    
    if truncated:
        output_lines.append("")
        output_lines.append("(Results are truncated. Consider using a more specific path or pattern.)")
    
    return "\n".join(output_lines)


def grep_tool_description() -> str:
    """Get the tool description for LLM consumption."""
    return """- Fast content search tool that works with any codebase size
- Searches file contents using regular expressions
- Supports full regex syntax (eg. "log.*Error", "function\\s+\\w+", etc.)
- Filter files by pattern with the include parameter (eg. "*.js", "*.{ts,tsx}")
- Returns file paths and line numbers with at least one match sorted by modification time
- Use this tool when you need to find files containing specific patterns
- If you need to identify/count the number of matches within files, use the Bash tool with `rg` (ripgrep) directly. Do NOT use `grep`.
- When you are doing an open-ended search that may require multiple rounds of globbing and grepping, use the Task tool instead"""


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python grep_tool.py <pattern> [path] [include_pattern]")
        print("Examples:")
        print("  python grep_tool.py 'function.*test'")
        print("  python grep_tool.py 'import.*React' src")
        print("  python grep_tool.py 'class.*Error' . '*.py'")
        sys.exit(1)
    
    pattern = sys.argv[1]
    search_path = sys.argv[2] if len(sys.argv) > 2 else None
    include = sys.argv[3] if len(sys.argv) > 3 else None
    
    try:
        result = grep_search(pattern, search_path, include)
        print(result['output'])
        
        # Print metadata if verbose
        if '--verbose' in sys.argv:
            print(f"\nMetadata:")
            print(f"  Matches: {result['metadata']['matches']}")
            print(f"  Truncated: {result['metadata']['truncated']}")
            print(f"  Pattern: {result['metadata']['pattern']}")
            print(f"  Search path: {result['metadata']['search_path']}")
            if result['metadata']['include']:
                print(f"  Include pattern: {result['metadata']['include']}")
                
    except GrepToolError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

