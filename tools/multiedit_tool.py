"""
Multi-edit tool for making multiple changes to a single file in one atomic operation.

This tool is built on top of the Edit tool and allows performing multiple
find-and-replace operations efficiently. Either all edits succeed or none are applied.

Usage:
    Use this tool when you need to make several changes to different parts of the same file.

Before using:
    1. Use the Read tool to understand the file's contents and context
    2. Verify the directory path is correct

Key features:
    - All edits are applied in sequence, in the order provided
    - Each edit operates on the result of the previous edit
    - Atomic operation: if any edit fails, none will be applied
    - Shows combined diff of all changes
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from .edit_tool import edit_file, EditToolError


class MultiEditToolError(Exception):
    """Custom exception for multiedit tool errors."""
    pass


def multiedit_file(
    file_path: str,
    edits: List[Dict[str, Any]],
    working_directory: Optional[str] = None,
    show_diff: bool = True
) -> Dict[str, Any]:
    """
    Apply multiple edits to a single file in one atomic operation.

    Args:
        file_path: Path to the file to modify (absolute or relative)
        edits: List of edit operations, each containing:
            - old_string: The text to replace
            - new_string: The text to replace it with
            - replace_all: (optional) Replace all occurrences
        working_directory: Working directory for relative paths
        show_diff: Whether to show diff in output

    Returns:
        Dictionary containing:
            - title: Relative path to file
            - output: Success message and combined diff
            - metadata: Diff, edit count, and file change info

    Raises:
        MultiEditToolError: If any edit fails or inputs are invalid
    """
    # Validate inputs
    if not file_path:
        raise MultiEditToolError("filePath is required")

    if not edits:
        raise MultiEditToolError("At least one edit is required")

    if not isinstance(edits, list):
        raise MultiEditToolError("edits must be a list of edit operations")

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
        raise MultiEditToolError(f"File not found: {filepath}")

    if filepath.is_dir():
        raise MultiEditToolError(f"Path is a directory, not a file: {filepath}")

    # Validate each edit
    for i, edit in enumerate(edits):
        if 'old_string' not in edit:
            raise MultiEditToolError(f"Edit {i}: old_string is required")
        if 'new_string' not in edit:
            raise MultiEditToolError(f"Edit {i}: new_string is required")
        if edit['old_string'] == edit.get('new_string', ''):
            raise MultiEditToolError(
                f"Edit {i}: oldString and newString must be different"
            )

    # Read original content
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except UnicodeDecodeError:
        raise MultiEditToolError(f"Cannot read file (encoding error): {filepath}")
    except Exception as e:
        raise MultiEditToolError(f"Failed to read file: {e}")

    # Create a backup path for rollback
    backup_fd, backup_path = tempfile.mkstemp()
    try:
        # Create backup for potential rollback
        with open(backup_fd, 'w', encoding='utf-8') as f:
            f.write(original_content)

        # Apply edits sequentially, building up the new content
        current_content = original_content
        all_results = []
        all_diffs = []

        for i, edit in enumerate(edits):
            old_string = edit['old_string']
            new_string = edit['new_string']
            # Support both 'replace_all' and 'replaceAll' for compatibility
            replace_all = edit.get('replace_all', edit.get('replaceAll', False))

            # Create a temporary file to apply this single edit
            temp_fd, temp_path = tempfile.mkstemp()
            try:
                with open(temp_fd, 'w', encoding='utf-8') as f:
                    f.write(current_content)

                # Apply the edit
                result = edit_file(
                    temp_path,
                    old_string,
                    new_string,
                    replace_all=replace_all,
                    working_directory=str(filepath.parent),
                    show_diff=False
                )

                # Read back the modified content
                with open(temp_path, 'r', encoding='utf-8') as f:
                    current_content = f.read()

                all_results.append({
                    'edit_index': i,
                    'success': True,
                    'metadata': result.get('metadata', {})
                })

            except EditToolError as e:
                raise MultiEditToolError(f"Edit {i} failed: {e}")
            finally:
                try:
                    os.close(temp_fd)
                except OSError:
                    pass
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

        # All edits succeeded - write the final content
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(current_content)
        except Exception as e:
            raise MultiEditToolError(f"Failed to write file: {e}")

        # Generate combined diff
        diff = _create_combined_diff(title, original_content, current_content)

        # Count total changes
        additions = 0
        deletions = 0
        for line in diff.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                additions += 1
            elif line.startswith('-') and not line.startswith('---'):
                deletions += 1

        # Build output
        edit_count = len(edits)
        output = f"Applied {edit_count} edit{'' if edit_count == 1 else 's'} successfully"

        if show_diff and diff:
            output += f"\n\n{diff}"

        return {
            'title': title,
            'output': output,
            'metadata': {
                'diff': diff,
                'edit_count': edit_count,
                'additions': additions,
                'deletions': deletions,
                'results': all_results
            }
        }

    except MultiEditToolError:
        # Rollback: restore from backup
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_content = f.read()
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(backup_content)
        except Exception as rollback_error:
            raise MultiEditToolError(
                f"Edit failed and rollback also failed: {rollback_error}"
            )
        raise
    finally:
        # Clean up backup file
        try:
            os.close(backup_fd)
        except OSError:
            pass
        try:
            os.unlink(backup_path)
        except OSError:
            pass


def _create_combined_diff(filepath: str, old_content: str, new_content: str) -> str:
    """Create a unified diff showing all changes combined."""
    import difflib

    old_lines = old_content.replace('\r\n', '\n').splitlines(keepends=True)
    new_lines = new_content.replace('\r\n', '\n').splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{filepath}",
        tofile=f"b/{filepath}",
        lineterm=''
    )

    return ''.join(diff)


def multiedit_tool_description() -> str:
    """Get the tool description for LLM consumption."""
    return """This is a tool for making multiple edits to a single file in one operation. It is built on top of the Edit tool and allows you to perform multiple find-and-replace operations efficiently. Prefer this tool over the Edit tool when you need to make multiple edits to the same file.

Before using this tool:
    1. Use the Read tool to understand the file's contents and context
    2. Verify the directory path is correct

To make multiple file edits, provide the following:
    1. filePath: The absolute path to the file to modify (must be absolute, not relative)
    2. edits: An array of edit operations to perform, where each edit contains:
        - oldString: The text to replace (must match the file contents exactly, including all whitespace and indentation)
        - newString: The edited text to replace the oldString
        - replaceAll: Replace all occurrences of oldString (default false)

IMPORTANT:
    - All edits are applied in sequence, in the order they are provided
    - Each edit operates on the result of the previous edit
    - All edits must be valid for the operation to succeed - if any edit fails, none will be applied
    - This tool is ideal when you need to make several changes to different parts of the same file

CRITICAL REQUIREMENTS:
    1. All edits follow the same requirements as the single Edit tool
    2. The edits are atomic - either all succeed or none are applied
    3. Plan your edits carefully to avoid conflicts between sequential operations

WARNING:
    - The tool will fail if edits.oldString doesn't match the file contents exactly (including whitespace)
    - The tool will fail if edits.oldString and edits.newString are the same
    - Since edits are applied in sequence, ensure that earlier edits don't affect the text that later edits are trying to find

When making edits:
    - Ensure all edits result in idiomatic, correct code
    - Do not leave the code in a broken state
    - Always use absolute file paths (starting with /)
    - Only use emojis if the user explicitly requests it. Avoid adding emojis to files unless asked.
    - Use replaceAll for replacing and renaming strings across the file. This parameter is useful if you want to rename a variable for instance."""


# Example usage
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 3:
        print("Usage: python multiedit_tool.py <file_path> <edits_json>")
        print("  edits_json: JSON array of edit objects with old_string, new_string, and optional replaceAll")
        sys.exit(1)

    file_path = sys.argv[1]
    try:
        edits = json.loads(sys.argv[2])
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        result = multiedit_file(file_path, edits)
        print(result['output'])
    except MultiEditToolError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
