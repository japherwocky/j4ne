# Direct Files Explanation

This document explains the presence of duplicate files in the root directory and the `tools/` directory.

## Current Status

There are duplicate files in the root directory and the `tools/` directory:
- `direct_client.py` and `tools/direct_client.py`
- `direct_tools.py` and `tools/direct_tools.py`
- `test_direct_tools.py` and `tests/test_direct_tools.py`

## Why We're Keeping Both Versions (Temporarily)

1. **Backward Compatibility**: The files in the root directory are being kept temporarily to maintain backward compatibility with existing code that might still import from these locations.

2. **Gradual Migration**: We're gradually migrating all imports to use the versions in the `tools/` directory, which are more up-to-date and better organized.

3. **Testing**: We need to ensure that all functionality works correctly with the new imports before removing the old files.

## Next Steps

1. Update all imports to use the versions in the `tools/` directory (in progress).
2. Run comprehensive tests to ensure everything works correctly.
3. Once all imports have been updated and tested, remove the duplicate files from the root directory.

## Files to Eventually Remove

Once all imports have been updated and tested, the following files can be removed from the root directory:
- `direct_client.py`
- `direct_tools.py`
- `test_direct_tools.py`

