"""
Smart directory listing tool.

Lists files and directories with a tree-like structure.
Ignores common build/cache directories by default.
"""
import os
from pathlib import Path
from typing import Optional

# Default ignore patterns (similar to OpenCode)
DEFAULT_IGNORE_PATTERNS = [
    "node_modules/",
    "__pycache__/",
    ".git/",
    "dist/",
    "build/",
    "target/",
    "vendor/",
    "bin/",
    "obj/",
    ".idea/",
    ".vscode/",
    ".zig-cache/",
    "zig-out",
    ".coverage",
    "coverage/",
    "tmp/",
    "temp/",
    ".cache/",
    "cache/",
    "logs/",
    ".venv/",
    "venv/",
    "env/",
]

LIMIT = 100


def should_ignore(entry_name: str, ignore_patterns: list[str]) -> bool:
    """Check if an entry should be ignored based on patterns."""
    for pattern in ignore_patterns:
        # Handle trailing slash patterns for directories
        if pattern.endswith("/"):
            if entry_name + "/" == pattern or entry_name.startswith(pattern.rstrip("/") + "/"):
                return True
        elif entry_name == pattern or entry_name.startswith(pattern + "/"):
            return True
    return False


def scan_directory(
    dir_path: Path,
    ignore_patterns: list[str],
    max_files: int = LIMIT,
) -> tuple[dict[str, list[str]], int, bool]:
    """
    Scan a directory and return its structure.

    Returns:
        tuple of (directory_structure, total_files, truncated)
        directory_structure: dict mapping dir path to list of entries (files and dirs)
    """
    entries_by_dir: dict[str, list[str]] = {}
    total_files = 0
    truncated = False

    def add_entry(parent: str, name: str, is_dir: bool):
        """Add an entry to the structure."""
        if parent not in entries_by_dir:
            entries_by_dir[parent] = []
        prefix = "/" if is_dir else ""
        entries_by_dir[parent].append(f"{name}{prefix}")

    def scan_dir(current_dir: Path, parent_key: str) -> tuple[int, bool]:
        """Recursively scan a directory."""
        nonlocal total_files, truncated

        local_count = 0
        local_truncated = False

        try:
            for entry in sorted(current_dir.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
                entry_name = entry.name

                if should_ignore(entry_name, ignore_patterns):
                    continue

                if entry.is_dir():
                    add_entry(parent_key, entry_name, True)
                    child_count, child_truncated = scan_dir(entry, entry_name)
                    local_count += child_count
                    local_truncated = local_truncated or child_truncated
                elif entry.is_file():
                    local_count += 1
                    if local_count > max_files:
                        local_truncated = True
                        break
                    add_entry(parent_key, entry_name, False)

            total_files += local_count
            truncated = truncated or local_truncated
            return local_count, local_truncated
        except PermissionError:
            return 0, False

    # Add root level entries
    entries_by_dir["."] = []

    try:
        for entry in sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
            entry_name = entry.name

            if should_ignore(entry_name, ignore_patterns):
                continue

            if entry.is_dir():
                add_entry(".", entry_name, True)
                scan_dir(entry, entry_name)
            elif entry.is_file():
                add_entry(".", entry_name, False)
                total_files += 1
                if total_files > max_files:
                    truncated = True
                    break
    except PermissionError:
        pass

    return (entries_by_dir, total_files, truncated)


def render_tree(
    entries_by_dir: dict[str, list[str]],
    root_path: str = ".",
    depth: int = 0,
) -> str:
    """Render directory structure as a tree."""
    indent = "  " * depth
    output = ""

    entries = entries_by_dir.get(root_path, [])
    child_dirs = sorted([e.rstrip("/") for e in entries if e.endswith("/")])
    files = sorted([e for e in entries if not e.endswith("/")])

    # Render directories first
    for child_dir in child_dirs:
        output += f"{indent}{child_dir}/\n"
        output += render_tree(entries_by_dir, child_dir, depth + 1)

    # Render files
    for file_name in files:
        output += f"{indent}{file_name}\n"

    return output


def list_directory(
    dir_path: Optional[str] = None,
    ignore: Optional[list[str]] = None,
) -> dict:
    """
    List directory contents with tree structure.

    Args:
        dir_path: Absolute path to directory. Uses current directory if None.
        ignore: Additional glob patterns to ignore.

    Returns:
        dict with output, title, and metadata
    """
    if dir_path is None:
        dir_path = os.getcwd()

    search_path = Path(dir_path).resolve()

    if not search_path.exists():
        return {
            "output": f"Error: Directory does not exist: {search_path}",
            "title": str(search_path),
            "metadata": {"count": 0, "truncated": False},
        }

    if not search_path.is_dir():
        return {
            "output": f"Error: Not a directory: {search_path}",
            "title": str(search_path),
            "metadata": {"count": 0, "truncated": False},
        }

    # Combine default ignore patterns with custom ones
    ignore_patterns = DEFAULT_IGNORE_PATTERNS.copy()
    if ignore:
        ignore_patterns.extend(ignore)

    entries_by_dir, count, truncated = scan_directory(search_path, ignore_patterns)

    # Build the tree output
    output = f"{search_path}/\n"
    output += render_tree(entries_by_dir)

    return {
        "title": str(search_path),
        "metadata": {"count": count, "truncated": truncated},
        "output": output,
    }


if __name__ == "__main__":
    # Demo usage
    result = list_directory(".")
    print(result["output"])
    if result["metadata"]["truncated"]:
        print(f"\n(Results truncated to {LIMIT} files)")
