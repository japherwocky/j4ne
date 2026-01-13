"""
File pattern matching tool using glob patterns.

Fast file discovery for any codebase size.
Supports patterns like "**/*.js" or "src/**/*.ts".
Returns files sorted by modification time (most recent first).
"""
import os
from pathlib import Path
from typing import Optional

LIMIT = 100


def glob_files(
    pattern: str,
    path: Optional[str] = None,
    max_results: int = LIMIT,
) -> dict:
    """
    Find files matching a glob pattern.

    Args:
        pattern: The glob pattern (e.g., "**/*.py", "src/**/*.ts")
        path: The directory to search in. Uses current directory if None.
        max_results: Maximum number of results to return.

    Returns:
        dict with output, title, and metadata
    """
    if path is None:
        search_path = Path.cwd()
    else:
        search_path = Path(path).resolve()

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

    files: list[tuple[float, str]] = []
    truncated = False

    try:
        # Handle different pattern types
        if "**" in pattern:
            # Recursive pattern - use rglob with the part after **
            # e.g., "**/*.py" -> "*.py"
            glob_part = pattern.split("**", 1)[1].lstrip("/\\")
            if glob_part.startswith("/") or glob_part.startswith("\\"):
                glob_part = glob_part[1:]
            # Use rglob for recursive matching
            for p in search_path.rglob(glob_part):
                if p.is_file():
                    try:
                        mtime = p.stat().st_mtime
                    except OSError:
                        mtime = 0
                    files.append((mtime, str(p.resolve())))
                    if len(files) >= max_results:
                        truncated = True
                        break
        else:
            # Non-recursive pattern
            for p in search_path.glob(pattern):
                if p.is_file():
                    try:
                        mtime = p.stat().st_mtime
                    except OSError:
                        mtime = 0
                    files.append((mtime, str(p.resolve())))
                    if len(files) >= max_results:
                        truncated = True
                        break
    except Exception as e:
        return {
            "output": f"Error: {str(e)}",
            "title": str(search_path),
            "metadata": {"count": 0, "truncated": False},
        }

    # Sort by modification time (most recent first)
    files.sort(key=lambda x: -x[0])

    output_lines: list[str] = []
    if not files:
        output_lines.append("No files found")
    else:
        for _, filepath in files:
            output_lines.append(filepath)

    output = "\n".join(output_lines)

    if truncated:
        output += "\n\n(Results are truncated. Consider using a more specific path or pattern.)"

    return {
        "title": str(search_path),
        "metadata": {"count": len(files), "truncated": truncated},
        "output": output,
    }


if __name__ == "__main__":
    # Demo usage
    import sys
    pattern = sys.argv[1] if len(sys.argv) > 1 else "**/*.py"
    path_arg = sys.argv[2] if len(sys.argv) > 2 else None

    result = glob_files(pattern, path_arg)
    print(f"Pattern: {pattern}")
    if path_arg:
        print(f"Path: {path_arg}")
    print()
    print(result["output"])
    print(f"\n({result['metadata']['count']} files found)")
