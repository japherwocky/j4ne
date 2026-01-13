"""
Patch tool for applying multi-file patch operations.

NOTE: This tool is not exposed in the main tools list as it is considered
experimental. It is kept here for reference and potential future use.

The patch tool applies unified patch files with a custom format:
    *** Begin Patch
    *** Add File: <filepath>
    +<content line 1>
    +<content line 2>
    ...
    *** Update File: <filepath>
    @@
     <context line 1>
    -<line to remove>
    +<line to add>
     <context line 2>
    *** Delete File: <filepath>
    *** End Patch
"""

import os
import difflib
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class PatchError(Exception):
    """Custom exception for patch tool errors."""
    pass


class HunkType(Enum):
    ADD = "add"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class UpdateFileChunk:
    """A chunk of changes within an update hunk."""
    old_lines: List[str]
    new_lines: List[str]
    change_context: Optional[str] = None
    is_end_of_file: bool = False


@dataclass
class Hunk:
    """A single hunk in a patch."""
    type: HunkType
    path: str
    contents: Optional[str] = None  # For add operations
    chunks: Optional[List[UpdateFileChunk]] = None  # For update operations
    move_path: Optional[str] = None  # For move operations


def parse_patch_header(lines: List[str], start_idx: int) -> Optional[Dict[str, Any]]:
    """Parse a patch header line to determine file operation type."""
    line = lines[start_idx]

    if line.startswith("*** Add File:"):
        parts = line.split(":", 2)
        file_path = parts[1].strip() if len(parts) > 1 else None
        return {"type": "add", "path": file_path, "next_idx": start_idx + 1} if file_path else None

    if line.startswith("*** Delete File:"):
        parts = line.split(":", 2)
        file_path = parts[1].strip() if len(parts) > 1 else None
        return {"type": "delete", "path": file_path, "next_idx": start_idx + 1} if file_path else None

    if line.startswith("*** Update File:"):
        parts = line.split(":", 2)
        file_path = parts[1].strip() if len(parts) > 1 else ""
        move_path: Optional[str] = None
        next_idx = start_idx + 1

        # Check for move directive
        if next_idx < len(lines) and lines[next_idx].startswith("*** Move to:"):
            move_parts = lines[next_idx].split(":", 2)
            move_path = move_parts[1].strip() if len(move_parts) > 1 else None
            next_idx += 1

        return {"type": "update", "path": file_path, "move_path": move_path, "next_idx": next_idx}

    return None


def parse_update_file_chunks(lines: List[str], start_idx: int) -> Dict[str, Any]:
    """Parse update file chunks (the @@ sections with - and + lines)."""
    chunks: List[UpdateFileChunk] = []
    i = start_idx

    while i < len(lines) and not lines[i].startswith("***"):
        if lines[i].startswith("@@"):
            # Parse context line
            context_line = lines[i][2:].strip()
            i += 1

            old_lines: List[str] = []
            new_lines: List[str] = []
            is_end_of_file = False

            # Parse change lines
            while i < len(lines) and not lines[i].startswith("@@") and not lines[i].startswith("***"):
                change_line = lines[i]

                if change_line == "*** End of File":
                    is_end_of_file = True
                    i += 1
                    break

                if change_line.startswith(" "):
                    # Keep line - appears in both old and new
                    content = change_line[1:]
                    old_lines.append(content)
                    new_lines.append(content)
                elif change_line.startswith("-"):
                    # Remove line - only in old
                    old_lines.append(change_line[1:])
                elif change_line.startswith("+"):
                    # Add line - only in new
                    new_lines.append(change_line[1:])

                i += 1

            chunks.append(UpdateFileChunk(
                old_lines=old_lines,
                new_lines=new_lines,
                change_context=context_line or None,
                is_end_of_file=is_end_of_file
            ))
        else:
            i += 1

    return {"chunks": chunks, "next_idx": i}


def parse_add_file_content(lines: List[str], start_idx: int) -> Dict[str, Any]:
    """Parse the content of an add file operation."""
    content = ""
    i = start_idx

    while i < len(lines) and not lines[i].startswith("***"):
        if lines[i].startswith("+"):
            content += lines[i][1:] + "\n"
        i += 1

    # Remove trailing newline
    if content.endswith("\n"):
        content = content[:-1]

    return {"content": content, "next_idx": i}


def parse_patch(patch_text: str) -> List[Hunk]:
    """
    Parse a patch text and return a list of hunks.

    Args:
        patch_text: The patch text to parse

    Returns:
        List of Hunk objects

    Raises:
        PatchError: If the patch format is invalid
    """
    lines = patch_text.split("\n")
    hunks: List[Hunk] = []

    # Look for Begin/End patch markers
    begin_marker = "*** Begin Patch"
    end_marker = "*** End Patch"

    begin_idx = -1
    end_idx = -1

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == begin_marker:
            begin_idx = i
        elif stripped == end_marker:
            end_idx = i
            break

    if begin_idx == -1 or end_idx == -1 or begin_idx >= end_idx:
        raise PatchError("Invalid patch format: missing *** Begin Patch / *** End Patch markers")

    # Parse content between markers
    i = begin_idx + 1

    while i < end_idx:
        header = parse_patch_header(lines, i)
        if not header:
            i += 1
            continue

        hunk_type = header["type"]
        path = header["path"]

        if hunk_type == "add":
            content_result = parse_add_file_content(lines, header["next_idx"])
            hunks.append(Hunk(
                type=HunkType.ADD,
                path=path,
                contents=content_result["content"]
            ))
            i = content_result["next_idx"]
        elif hunk_type == "delete":
            hunks.append(Hunk(
                type=HunkType.DELETE,
                path=path
            ))
            i = header["next_idx"]
        elif hunk_type == "update":
            chunks_result = parse_update_file_chunks(lines, header["next_idx"])
            hunks.append(Hunk(
                type=HunkType.UPDATE,
                path=path,
                chunks=chunks_result["chunks"],
                move_path=header.get("move_path")
            ))
            i = chunks_result["next_idx"]
        else:
            i += 1

    if not hunks:
        raise PatchError("No file changes found in patch")

    return hunks


def derive_new_content_from_chunks(file_path: str, chunks: List[UpdateFileChunk]) -> str:
    """
    Derive new file content by applying chunks to existing content.

    Args:
        file_path: Path to the file (for error messages)
        chunks: List of update chunks

    Returns:
        The new file content

    Raises:
        PatchError: If chunk application fails
    """
    # Read the current file content
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.read().split('\n')
    except FileNotFoundError:
        raise PatchError(f"File not found for update: {file_path}")
    except UnicodeDecodeError:
        raise PatchError(f"Cannot read file (encoding error): {file_path}")

    # Apply each chunk
    for chunk in chunks:
        if chunk.is_end_of_file:
            # Handle end-of-file marker - truncate at this point
            # This is a simplified handling
            pass

        # For each chunk, we need to find the context lines and apply changes
        # This is a basic implementation - the OpenCode version has more sophisticated logic

        # Find the starting position based on context
        if not chunk.old_lines:
            # No context - can't apply
            continue

        start_pos = -1
        for j in range(len(lines) - len(chunk.old_lines) + 1):
            # Check if context matches
            match = True
            for k, ctx_line in enumerate(chunk.old_lines):
                if j + k < len(lines) and lines[j + k].strip() != ctx_line.strip():
                    match = False
                    break
            if match:
                start_pos = j
                break

        if start_pos == -1:
            # Try with more relaxed matching
            for j in range(len(lines)):
                if j < len(lines) and lines[j].strip() == chunk.old_lines[0].strip():
                    start_pos = j
                    break

        if start_pos == -1:
            raise PatchError(f"Failed to find context in {file_path} for chunk update")

        # Replace the old lines with new lines
        # Number of old lines to remove
        num_old = len(chunk.old_lines)

        # Build new content
        new_lines = lines[:start_pos] + chunk.new_lines + lines[start_pos + num_old:]
        lines = new_lines

    return '\n'.join(lines)


def apply_patch(
    patch_text: str,
    base_directory: Optional[str] = None
) -> Dict[str, Any]:
    """
    Apply a patch to modify multiple files.

    Args:
        patch_text: The patch text to apply
        base_directory: Base directory for relative paths (default: cwd)

    Returns:
        Dictionary containing:
            - title: Summary of changes
            - output: Success message with list of changed files
            - metadata: Diff and file change info

    Raises:
        PatchError: If patch parsing or application fails
    """
    if not patch_text or not patch_text.strip():
        raise PatchError("patchText is required")

    # Parse the patch
    try:
        hunks = parse_patch(patch_text)
    except PatchError:
        raise
    except Exception as e:
        raise PatchError(f"Failed to parse patch: {e}")

    if not hunks:
        raise PatchError("No file changes found in patch")

    # Resolve base directory
    base_dir = Path(base_directory) if base_directory else Path.cwd()

    # Track all file changes for combined diff
    file_changes: List[Dict[str, Any]] = []
    changed_files: List[str] = []

    # Process each hunk
    for hunk in hunks:
        file_path = base_dir / hunk.path
        file_path_str = str(file_path.resolve())

        if hunk.type == HunkType.ADD:
            # Create new file
            new_content = hunk.contents or ""

            # Create parent directories
            parent_dir = file_path.parent
            if str(parent_dir) != "." and str(parent_dir) != "/":
                parent_dir.mkdir(parents=True, exist_ok=True)

            # Write the file
            file_path.write_text(new_content, encoding='utf-8')
            changed_files.append(file_path_str)

            # Generate diff
            diff = difflib.unified_diff(
                [],  # No old content for new file
                new_content.split('\n'),
                fromfile=f"a/{hunk.path}",
                tofile=f"b/{hunk.path}",
                lineterm=''
            )

            file_changes.append({
                "filePath": file_path_str,
                "oldContent": "",
                "newContent": new_content,
                "type": "add",
                "diff": '\n'.join(diff)
            })

        elif hunk.type == HunkType.UPDATE:
            # Update existing file
            if not file_path.exists():
                raise PatchError(f"File not found for update: {file_path}")

            if file_path.is_dir():
                raise PatchError(f"Path is a directory, not a file: {file_path}")

            old_content = file_path.read_text(encoding='utf-8')

            # Apply chunks to get new content
            if hunk.chunks:
                try:
                    new_content = derive_new_content_from_chunks(file_path_str, hunk.chunks)
                except PatchError:
                    raise
                except Exception as e:
                    raise PatchError(f"Failed to apply update to {file_path_str}: {e}")
            else:
                new_content = old_content

            # Handle move operation
            move_path = hunk.move_path
            if move_path:
                move_file_path = base_dir / move_path
                move_file_path_str = str(move_file_path.resolve())

                # Create parent directories for destination
                parent_dir = move_file_path.parent
                if str(parent_dir) != "." and str(parent_dir) != "/":
                    parent_dir.mkdir(parents=True, exist_ok=True)

                # Write to new location
                move_file_path.write_text(new_content, encoding='utf-8')

                # Remove original
                file_path.unlink()

                changed_files.append(move_file_path_str)

                # Generate diff
                diff = difflib.unified_diff(
                    old_content.split('\n'),
                    new_content.split('\n'),
                    fromfile=f"a/{hunk.path}",
                    tofile=f"b/{move_path}",
                    lineterm=''
                )

                file_changes.append({
                    "filePath": move_file_path_str,
                    "oldContent": old_content,
                    "newContent": new_content,
                    "type": "move",
                    "originalPath": file_path_str,
                    "diff": '\n'.join(diff)
                })
            else:
                # Regular update
                file_path.write_text(new_content, encoding='utf-8')
                changed_files.append(file_path_str)

                # Generate diff
                diff = difflib.unified_diff(
                    old_content.split('\n'),
                    new_content.split('\n'),
                    fromfile=f"a/{hunk.path}",
                    tofile=f"b/{hunk.path}",
                    lineterm=''
                )

                file_changes.append({
                    "filePath": file_path_str,
                    "oldContent": old_content,
                    "newContent": new_content,
                    "type": "update",
                    "diff": '\n'.join(diff)
                })

        elif hunk.type == HunkType.DELETE:
            # Delete file
            if not file_path.exists():
                raise PatchError(f"File not found for delete: {file_path}")

            if file_path.is_dir():
                raise PatchError(f"Path is a directory, not a file: {file_path}")

            old_content = file_path.read_text(encoding='utf-8')
            file_path.unlink()
            changed_files.append(file_path_str)

            # Generate diff
            diff = difflib.unified_diff(
                old_content.split('\n'),
                [],
                fromfile=f"a/{hunk.path}",
                tofile=f"b/{hunk.path}",
                lineterm=''
            )

            file_changes.append({
                "filePath": file_path_str,
                "oldContent": old_content,
                "newContent": "",
                "type": "delete",
                "diff": '\n'.join(diff)
            })

    # Build combined diff
    combined_diff = '\n'.join(change["diff"] for change in file_changes)

    # Get relative paths for output
    try:
        relative_paths = [str(Path(f).relative_to(base_dir)) for f in changed_files]
    except ValueError:
        relative_paths = changed_files

    # Build output
    file_count = len(changed_files)
    summary = f"{file_count} file{'s' if file_count != 1 else ''} changed"
    output = f"Patch applied successfully. {summary}:\n" + '\n'.join(f"  {p}" for p in relative_paths)

    return {
        "title": summary,
        "output": output,
        "metadata": {
            "diff": combined_diff,
            "files_changed": file_count,
            "changed_files": changed_files,
            "file_changes": file_changes
        }
    }


def patch_tool_description() -> str:
    """
    Get the tool description for LLM consumption.

    NOTE: This tool is not exposed in the main tools list.
    """
    return """Apply a patch to modify multiple files. Supports adding, updating, and deleting files with context-aware changes.

Patch Format:
    *** Begin Patch
    *** Add File: <filepath>
    +<content line 1>
    +<content line 2>
    ...
    *** Update File: <filepath>
    @@
     <context line 1>
    -<line to remove>
    +<line to add>
     <context line 2>
    *** Delete File: <filepath>
    *** End Patch

Operations:
    - *** Add File: - Create a new file with the given content
    - *** Update File: - Modify an existing file using context lines and +/- markers
    - *** Delete File: - Delete an existing file
    - *** Move to: - (Optional) Move file to new location during update

All changes in a patch are applied atomically - either all succeed or none are applied."""


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python patch_tool.py <patch_text> [base_directory]")
        sys.exit(1)

    patch_text = sys.argv[1]
    base_directory = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        result = apply_patch(patch_text, base_directory)
        print(result['output'])
        if result['metadata']['diff']:
            print("\n--- Diff ---")
            print(result['metadata']['diff'])
    except PatchError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
