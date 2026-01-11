"""
Multi-edit tool for performing multiple string replacements in a single file atomically.

This tool extends the edit tool functionality to perform multiple edits in sequence
while ensuring atomicity - either all edits succeed or none are applied.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from tools.edit_tool import (
    edit_file,
    EditToolError,
    replace_string,
    create_diff,
    trim_diff
)


class MultiEditToolError(Exception):
    """Exception raised by multi-edit tool operations."""
    pass


@dataclass
class EditOperation:
    """Represents a single edit operation."""
    old_string: str
    new_string: str
    replace_all: bool = False


@dataclass
class EditResult:
    """Result of a single edit operation."""
    success: bool
    old_string: str
    new_string: str
    replace_all: bool
    error_message: Optional[str] = None
    additions: int = 0
    deletions: int = 0


@dataclass
class MultiEditResult:
    """Result of a multi-edit operation."""
    success: bool
    file_path: str
    total_edits: int
    successful_edits: int
    edit_results: List[EditResult]
    final_diff: Optional[str] = None
    error_message: Optional[str] = None


def validate_edit_operations(edits: List[EditOperation]) -> None:
    """
    Validate edit operations for basic consistency.
    
    Args:
        edits: List of edit operations to validate
        
    Raises:
        MultiEditToolError: If validation fails
    """
    if not edits:
        raise MultiEditToolError("At least one edit operation is required")
    
    for i, edit in enumerate(edits):
        if not edit.old_string and not edit.new_string:
            raise MultiEditToolError(f"Edit {i+1}: Both old_string and new_string cannot be empty")
        
        if edit.old_string == edit.new_string:
            raise MultiEditToolError(f"Edit {i+1}: old_string and new_string must be different")


def detect_edit_conflicts(content: str, edits: List[EditOperation]) -> List[str]:
    """
    Detect potential conflicts between edit operations.
    
    This is a basic conflict detection that looks for overlapping string matches.
    More sophisticated conflict detection could be added in the future.
    
    Args:
        content: File content to analyze
        edits: List of edit operations
        
    Returns:
        List of conflict descriptions (empty if no conflicts)
    """
    conflicts = []
    
    # Find all match positions for each edit
    edit_positions = []
    for i, edit in enumerate(edits):
        if not edit.old_string:  # Skip empty old_string (file creation)
            edit_positions.append([])
            continue
            
        positions = []
        start = 0
        while True:
            pos = content.find(edit.old_string, start)
            if pos == -1:
                break
            positions.append((pos, pos + len(edit.old_string)))
            start = pos + 1
        edit_positions.append(positions)
    
    # Check for overlapping ranges
    for i in range(len(edits)):
        for j in range(i + 1, len(edits)):
            for pos_i in edit_positions[i]:
                for pos_j in edit_positions[j]:
                    # Check if ranges overlap
                    if (pos_i[0] < pos_j[1] and pos_j[0] < pos_i[1]):
                        conflicts.append(
                            f"Edit {i+1} and Edit {j+1} have overlapping target ranges: "
                            f"positions {pos_i} and {pos_j}"
                        )
    
    return conflicts


def apply_edits_sequentially(
    file_path: str,
    edits: List[EditOperation],
    validate_conflicts: bool = True
) -> MultiEditResult:
    """
    Apply multiple edits to a file sequentially with atomicity.
    
    Args:
        file_path: Path to the file to edit
        edits: List of edit operations to apply
        validate_conflicts: Whether to validate for conflicts before applying
        
    Returns:
        MultiEditResult with operation details
    """
    file_path = os.path.abspath(file_path)
    
    try:
        # Validate edit operations
        validate_edit_operations(edits)
        
        # Read original file content (or prepare for new file creation)
        if os.path.exists(file_path):
            if os.path.isdir(file_path):
                raise MultiEditToolError(f"Path is a directory, not a file: {file_path}")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
            except UnicodeDecodeError:
                raise MultiEditToolError(f"File is not valid UTF-8: {file_path}")
        else:
            # File doesn't exist - check if first edit is for file creation
            if edits[0].old_string != "":
                raise MultiEditToolError(f"File not found: {file_path}")
            original_content = ""
        
        # Detect conflicts if requested
        if validate_conflicts and original_content:
            conflicts = detect_edit_conflicts(original_content, edits)
            if conflicts:
                raise MultiEditToolError(f"Edit conflicts detected:\n" + "\n".join(conflicts))
        
        # Apply edits sequentially
        current_content = original_content
        edit_results = []
        
        for i, edit in enumerate(edits):
            try:
                # Apply the edit using the existing edit tool logic
                new_content = replace_string(
                    current_content,
                    edit.old_string,
                    edit.new_string,
                    edit.replace_all
                )
                
                # Calculate changes
                old_lines = current_content.split('\n')
                new_lines = new_content.split('\n')
                additions = len(new_lines) - len(old_lines)
                deletions = max(0, -additions)
                additions = max(0, additions)
                
                edit_results.append(EditResult(
                    success=True,
                    old_string=edit.old_string,
                    new_string=edit.new_string,
                    replace_all=edit.replace_all,
                    additions=additions,
                    deletions=deletions
                ))
                
                current_content = new_content
                
            except EditToolError as e:
                # Edit failed - return failure result
                edit_results.append(EditResult(
                    success=False,
                    old_string=edit.old_string,
                    new_string=edit.new_string,
                    replace_all=edit.replace_all,
                    error_message=str(e)
                ))
                
                return MultiEditResult(
                    success=False,
                    file_path=file_path,
                    total_edits=len(edits),
                    successful_edits=i,
                    edit_results=edit_results,
                    error_message=f"Edit {i+1} failed: {str(e)}"
                )
        
        # All edits succeeded - write the file
        try:
            # Ensure parent directory exists
            parent_dir = os.path.dirname(file_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(current_content)
        except Exception as e:
            raise MultiEditToolError(f"Failed to write file: {str(e)}")
        
        # Generate final diff
        final_diff = None
        if original_content != current_content:
            final_diff = create_diff(
                os.path.basename(file_path),
                original_content,
                current_content
            )
            final_diff = trim_diff(final_diff)
        
        return MultiEditResult(
            success=True,
            file_path=file_path,
            total_edits=len(edits),
            successful_edits=len(edits),
            edit_results=edit_results,
            final_diff=final_diff
        )
        
    except MultiEditToolError:
        raise
    except Exception as e:
        raise MultiEditToolError(f"Unexpected error during multi-edit: {str(e)}")


def multiedit_file(
    file_path: str,
    edits: List[Dict[str, Any]],
    validate_conflicts: bool = True
) -> Dict[str, Any]:
    """
    Perform multiple edits on a file atomically.
    
    This is the main interface function that matches the OpenCode multiedit tool API.
    
    Args:
        file_path: Path to the file to edit
        edits: List of edit dictionaries with keys: old_string, new_string, replace_all
        validate_conflicts: Whether to validate for conflicts before applying
        
    Returns:
        Dictionary with title, output, and metadata
    """
    try:
        # Convert edit dictionaries to EditOperation objects
        edit_operations = []
        for i, edit_dict in enumerate(edits):
            if not isinstance(edit_dict, dict):
                raise MultiEditToolError(f"Edit {i+1} must be a dictionary")
            
            old_string = edit_dict.get('old_string', '')
            new_string = edit_dict.get('new_string', '')
            replace_all = edit_dict.get('replace_all', False)
            
            if 'old_string' not in edit_dict:
                raise MultiEditToolError(f"Edit {i+1} missing required 'old_string' field")
            if 'new_string' not in edit_dict:
                raise MultiEditToolError(f"Edit {i+1} missing required 'new_string' field")
            
            edit_operations.append(EditOperation(
                old_string=old_string,
                new_string=new_string,
                replace_all=replace_all
            ))
        
        # Apply the edits
        result = apply_edits_sequentially(file_path, edit_operations, validate_conflicts)
        
        if result.success:
            # Generate success output
            output_lines = []
            
            if result.final_diff:
                output_lines.append("Applied multiple edits successfully:")
                output_lines.append("")
                output_lines.append(result.final_diff)
            else:
                output_lines.append("No changes were needed (all edits resulted in identical content).")
            
            # Add summary
            total_additions = sum(edit.additions for edit in result.edit_results)
            total_deletions = sum(edit.deletions for edit in result.edit_results)
            
            output_lines.append("")
            output_lines.append(f"Summary: {result.successful_edits} edits applied successfully")
            if total_additions > 0 or total_deletions > 0:
                output_lines.append(f"Changes: +{total_additions} lines, -{total_deletions} lines")
            
            return {
                'title': os.path.basename(file_path),
                'output': '\n'.join(output_lines),
                'metadata': {
                    'success': True,
                    'total_edits': result.total_edits,
                    'successful_edits': result.successful_edits,
                    'additions': total_additions,
                    'deletions': total_deletions,
                    'diff': result.final_diff,
                    'edit_results': [
                        {
                            'success': edit.success,
                            'old_string': edit.old_string[:100] + '...' if len(edit.old_string) > 100 else edit.old_string,
                            'new_string': edit.new_string[:100] + '...' if len(edit.new_string) > 100 else edit.new_string,
                            'replace_all': edit.replace_all,
                            'additions': edit.additions,
                            'deletions': edit.deletions
                        }
                        for edit in result.edit_results
                    ]
                }
            }
        else:
            # Generate failure output
            output_lines = [f"Multi-edit failed: {result.error_message}"]
            
            if result.edit_results:
                output_lines.append("")
                output_lines.append("Edit results:")
                for i, edit in enumerate(result.edit_results):
                    status = "✓" if edit.success else "✗"
                    output_lines.append(f"  {status} Edit {i+1}: {edit.old_string[:50]}... → {edit.new_string[:50]}...")
                    if not edit.success and edit.error_message:
                        output_lines.append(f"    Error: {edit.error_message}")
            
            return {
                'title': f"Error: {os.path.basename(file_path)}",
                'output': '\n'.join(output_lines),
                'metadata': {
                    'success': False,
                    'total_edits': result.total_edits,
                    'successful_edits': result.successful_edits,
                    'error': result.error_message,
                    'edit_results': [
                        {
                            'success': edit.success,
                            'error_message': edit.error_message
                        }
                        for edit in result.edit_results
                    ]
                }
            }
            
    except MultiEditToolError as e:
        return {
            'title': f"Error: {os.path.basename(file_path)}",
            'output': f"Multi-edit error: {str(e)}",
            'metadata': {
                'success': False,
                'error': str(e)
            }
        }


if __name__ == "__main__":
    # Test the multiedit tool
    import tempfile
    
    # Create a test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""def hello():
    print("Hello")
    return "world"

def goodbye():
    print("Goodbye")
    return "universe"
""")
        test_file = f.name
    
    try:
        # Test multiple edits
        edits = [
            {'old_string': 'print("Hello")', 'new_string': 'print("Hi there")', 'replace_all': False},
            {'old_string': 'return "world"', 'new_string': 'return "planet"', 'replace_all': False},
            {'old_string': 'print("Goodbye")', 'new_string': 'print("See you later")', 'replace_all': False}
        ]
        
        result = multiedit_file(test_file, edits)
        print("Test Result:")
        print(f"Title: {result['title']}")
        print(f"Success: {result['metadata']['success']}")
        print(f"Edits: {result['metadata']['successful_edits']}/{result['metadata']['total_edits']}")
        print("\nOutput:")
        print(result['output'])
        
    finally:
        # Clean up
        os.unlink(test_file)
