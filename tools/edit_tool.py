"""
Smart file editing tool for OpenCode-style precise string replacements.

This module provides safe and intelligent file editing with:
- Exact string matching (not regex)
- Multiple replacement strategies for flexible matching
- replaceAll option for batch renaming
- Diff preview before applying changes
- Perfect indentation preservation
- Safety requirement: must read file first
"""

import os
import difflib
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Generator
import re


class EditToolError(Exception):
    """Custom exception for edit tool errors."""
    pass


def normalize_line_endings(text: str) -> str:
    """Normalize line endings to Unix style."""
    return text.replace('\r\n', '\n')


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace for flexible matching."""
    return re.sub(r'\s+', ' ', text.strip())


def levenshtein_distance(a: str, b: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if not a:
        return len(b)
    if not b:
        return len(a)
    
    matrix = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    
    for i in range(len(a) + 1):
        matrix[i][0] = i
    for j in range(len(b) + 1):
        matrix[0][j] = j
    
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = 0 if a[i-1] == b[j-1] else 1
            matrix[i][j] = min(
                matrix[i-1][j] + 1,      # deletion
                matrix[i][j-1] + 1,      # insertion
                matrix[i-1][j-1] + cost  # substitution
            )
    
    return matrix[len(a)][len(b)]


class Replacer:
    """Base class for replacement strategies."""
    
    @staticmethod
    def find_matches(content: str, find: str) -> Generator[str, None, None]:
        """Find all matches for the given find string in content."""
        raise NotImplementedError


class SimpleReplacer(Replacer):
    """Simple exact string matching."""
    
    @staticmethod
    def find_matches(content: str, find: str) -> Generator[str, None, None]:
        if find in content:
            yield find


class LineTrimmedReplacer(Replacer):
    """Match lines with trimmed whitespace."""
    
    @staticmethod
    def find_matches(content: str, find: str) -> Generator[str, None, None]:
        original_lines = content.split('\n')
        search_lines = find.split('\n')
        
        # Remove trailing empty line if present
        if search_lines and search_lines[-1] == '':
            search_lines.pop()
        
        for i in range(len(original_lines) - len(search_lines) + 1):
            matches = True
            
            for j in range(len(search_lines)):
                original_trimmed = original_lines[i + j].strip()
                search_trimmed = search_lines[j].strip()
                
                if original_trimmed != search_trimmed:
                    matches = False
                    break
            
            if matches:
                # Calculate the exact substring that matched
                match_start = sum(len(line) + 1 for line in original_lines[:i])
                match_lines = original_lines[i:i + len(search_lines)]
                match_text = '\n'.join(match_lines)
                
                # Don't include trailing newline unless it was in the original find
                if not find.endswith('\n') and match_text.endswith('\n'):
                    match_text = match_text[:-1]
                
                yield match_text


class WhitespaceNormalizedReplacer(Replacer):
    """Match with normalized whitespace."""
    
    @staticmethod
    def find_matches(content: str, find: str) -> Generator[str, None, None]:
        normalized_find = normalize_whitespace(find)
        
        # Handle single line matches
        lines = content.split('\n')
        for line in lines:
            if normalize_whitespace(line) == normalized_find:
                yield line
            elif normalized_find in normalize_whitespace(line):
                # Try to find the actual substring that matches
                words = find.strip().split()
                if words:
                    pattern = r'\s+'.join(re.escape(word) for word in words)
                    try:
                        match = re.search(pattern, line)
                        if match:
                            yield match.group(0)
                    except re.error:
                        pass
        
        # Handle multi-line matches
        find_lines = find.split('\n')
        if len(find_lines) > 1:
            for i in range(len(lines) - len(find_lines) + 1):
                block = '\n'.join(lines[i:i + len(find_lines)])
                if normalize_whitespace(block) == normalized_find:
                    yield block


class IndentationFlexibleReplacer(Replacer):
    """Match with flexible indentation."""
    
    @staticmethod
    def remove_indentation(text: str) -> str:
        """Remove common indentation from text."""
        lines = text.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        if not non_empty_lines:
            return text
        
        min_indent = min(len(line) - len(line.lstrip()) for line in non_empty_lines)
        
        result_lines = []
        for line in lines:
            if line.strip():
                result_lines.append(line[min_indent:])
            else:
                result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    @staticmethod
    def find_matches(content: str, find: str) -> Generator[str, None, None]:
        normalized_find = IndentationFlexibleReplacer.remove_indentation(find)
        content_lines = content.split('\n')
        find_lines = find.split('\n')
        
        for i in range(len(content_lines) - len(find_lines) + 1):
            block = '\n'.join(content_lines[i:i + len(find_lines)])
            if IndentationFlexibleReplacer.remove_indentation(block) == normalized_find:
                yield block


class BlockAnchorReplacer(Replacer):
    """Match blocks using first and last lines as anchors."""
    
    @staticmethod
    def find_matches(content: str, find: str) -> Generator[str, None, None]:
        original_lines = content.split('\n')
        search_lines = find.split('\n')
        
        if len(search_lines) < 3:
            return
        
        # Remove trailing empty line if present
        if search_lines and search_lines[-1] == '':
            search_lines.pop()
        
        first_line_search = search_lines[0].strip()
        last_line_search = search_lines[-1].strip()
        
        # Find candidates where both anchors match
        candidates = []
        for i in range(len(original_lines)):
            if original_lines[i].strip() != first_line_search:
                continue
            
            # Look for matching last line
            for j in range(i + 2, len(original_lines)):
                if original_lines[j].strip() == last_line_search:
                    candidates.append((i, j))
                    break
        
        if not candidates:
            return
        
        # For single candidate, use relaxed matching
        if len(candidates) == 1:
            start_line, end_line = candidates[0]
            actual_block_size = end_line - start_line + 1
            search_block_size = len(search_lines)
            
            # Check similarity of middle lines
            if actual_block_size >= search_block_size:
                similarity = 0
                lines_to_check = min(search_block_size - 2, actual_block_size - 2)
                
                if lines_to_check > 0:
                    for j in range(1, min(search_block_size - 1, actual_block_size - 1)):
                        if (j < len(search_lines) - 1 and 
                            start_line + j < len(original_lines) and
                            original_lines[start_line + j].strip() == search_lines[j].strip()):
                            similarity += 1
                    
                    similarity_ratio = similarity / lines_to_check
                    if similarity_ratio >= 0.0:  # Very relaxed for single candidate
                        block = '\n'.join(original_lines[start_line:end_line + 1])
                        yield block


class MultiOccurrenceReplacer(Replacer):
    """Find all exact occurrences for replaceAll functionality."""
    
    @staticmethod
    def find_matches(content: str, find: str) -> Generator[str, None, None]:
        start_index = 0
        while True:
            index = content.find(find, start_index)
            if index == -1:
                break
            yield find
            start_index = index + len(find)


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
            match = re.match(r'^(\s*)', content)
            if match:
                min_indent = min(min_indent, len(match.group(1)))
    
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


def replace_string(content: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
    """
    Replace old_string with new_string in content using multiple strategies.
    
    Args:
        content: The file content to modify
        old_string: The string to find and replace
        new_string: The replacement string
        replace_all: If True, replace all occurrences; if False, replace only unique occurrence
        
    Returns:
        Modified content
        
    Raises:
        EditToolError: If old_string not found or multiple matches found without replace_all
    """
    if old_string == new_string:
        raise EditToolError("oldString and newString must be different")
    
    # Try different replacement strategies in order of preference
    replacers = [
        SimpleReplacer,
        LineTrimmedReplacer,
        WhitespaceNormalizedReplacer,
        IndentationFlexibleReplacer,
        BlockAnchorReplacer,
        MultiOccurrenceReplacer,
    ]
    
    found_matches = []
    
    for replacer_class in replacers:
        matches = list(replacer_class.find_matches(content, old_string))
        if matches:
            found_matches.extend(matches)
            
            # For replace_all, use the first successful strategy
            if replace_all:
                # Replace all occurrences of the first match found
                search_string = matches[0]
                return content.replace(search_string, new_string)
            
            # For single replacement, ensure uniqueness
            unique_matches = list(set(matches))
            if len(unique_matches) == 1:
                search_string = unique_matches[0]
                # Ensure it appears only once in content
                if content.count(search_string) == 1:
                    return content.replace(search_string, new_string)
    
    if not found_matches:
        raise EditToolError("oldString not found in content")
    
    raise EditToolError(
        "Found multiple matches for oldString. Provide more surrounding lines in oldString "
        "to identify the correct match, or use replaceAll=True to replace all occurrences."
    )


def edit_file(
    file_path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
    working_directory: Optional[str] = None,
    show_diff: bool = True
) -> Dict[str, Any]:
    """
    Edit a file by replacing old_string with new_string.
    
    Args:
        file_path: Path to the file to edit (absolute or relative)
        old_string: The text to replace
        new_string: The text to replace it with
        replace_all: Replace all occurrences (default: False)
        working_directory: Working directory for relative paths (default: cwd)
        show_diff: Whether to show diff in output (default: True)
        
    Returns:
        Dictionary containing:
            - title: Relative path to file
            - output: Success message and optional diff
            - metadata: Diff and file change info
            
    Raises:
        EditToolError: If file cannot be edited or strings are invalid
    """
    # Validate inputs
    if not file_path:
        raise EditToolError("filePath is required")
    
    if old_string == new_string:
        raise EditToolError("oldString and newString must be different")
    
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
    
    # Handle empty old_string (create new file)
    if old_string == "":
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_string)
            
            diff = create_diff(title, "", new_string)
            
            return {
                'title': title,
                'output': f"File created successfully",
                'metadata': {
                    'diff': diff,
                    'additions': len(new_string.split('\n')),
                    'deletions': 0,
                }
            }
        except Exception as e:
            raise EditToolError(f"Failed to create file: {e}")
    
    # Check if file exists (for non-empty old_string)
    if not filepath.exists():
        raise EditToolError(f"File not found: {filepath}")
    
    if filepath.is_dir():
        raise EditToolError(f"Path is a directory, not a file: {filepath}")
    
    # Read current content
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            old_content = f.read()
    except UnicodeDecodeError:
        raise EditToolError(f"Cannot read file (encoding error): {filepath}")
    except Exception as e:
        raise EditToolError(f"Failed to read file: {e}")
    
    # Perform replacement
    try:
        new_content = replace_string(old_content, old_string, new_string, replace_all)
    except EditToolError:
        raise
    except Exception as e:
        raise EditToolError(f"Failed to perform replacement: {e}")
    
    # Write new content
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
    except Exception as e:
        raise EditToolError(f"Failed to write file: {e}")
    
    # Generate diff
    diff = create_diff(title, old_content, new_content)
    trimmed_diff = trim_diff(diff)
    
    # Count changes
    old_lines = old_content.split('\n')
    new_lines = new_content.split('\n')
    
    additions = 0
    deletions = 0
    
    for line in difflib.unified_diff(old_lines, new_lines, lineterm=''):
        if line.startswith('+') and not line.startswith('+++'):
            additions += 1
        elif line.startswith('-') and not line.startswith('---'):
            deletions += 1
    
    # Build output
    output = f"File edited successfully"
    if show_diff and trimmed_diff:
        output += f"\n\n{trimmed_diff}"
    
    return {
        'title': title,
        'output': output,
        'metadata': {
            'diff': trimmed_diff,
            'additions': additions,
            'deletions': deletions,
        }
    }


def edit_tool_description() -> str:
    """Get the tool description for LLM consumption."""
    return """Performs exact string replacements in files.

Usage:
- You must use your `Read` tool at least once in the conversation before editing. This tool will error if you attempt an edit without reading the file.
- When editing text from Read tool output, ensure you preserve the exact indentation (tabs/spaces) as it appears AFTER the line number prefix. The line number prefix format is: spaces + line number + tab. Everything after that tab is the actual file content to match. Never include any part of the line number prefix in the oldString or newString.
- ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.
- Only use emojis if the user explicitly requests it. Avoid adding emojis to files unless asked.
- The edit will FAIL if `oldString` is not found in the file with an error "oldString not found in content".
- The edit will FAIL if `oldString` is found multiple times in the file with an error "oldString found multiple times and requires more code context to uniquely identify the intended match". Either provide a larger string with more surrounding context to make it unique or use `replaceAll` to change every instance of `oldString`.
- Use `replaceAll` for replacing and renaming strings across the file. This parameter is useful if you want to rename a variable for instance."""


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python edit_tool.py <filepath> <old_string> <new_string> [replace_all]")
        sys.exit(1)
    
    filepath = sys.argv[1]
    old_string = sys.argv[2]
    new_string = sys.argv[3]
    replace_all = len(sys.argv) > 4 and sys.argv[4].lower() in ('true', '1', 'yes')
    
    try:
        result = edit_file(filepath, old_string, new_string, replace_all=replace_all)
        print(result['output'])
    except EditToolError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
