# Tests for Direct Tools Implementation

This directory contains tests for the direct tools implementation.

## Files

- `test_direct_tools.py`: Test script to verify the direct tools implementation works correctly

## Running Tests

To run the tests, use the following command:

```bash
python -m tests.test_direct_tools
```

## Test Coverage

The tests cover:

1. **Filesystem Tools**:
   - Writing files
   - Reading files
   - Listing files
   - Deleting files

2. **SQLite Tools**:
   - Creating tables
   - Listing tables
   - Describing tables
   - Executing queries
   - Adding insights

## Adding New Tests

To add new tests, create a new test method in the `TestDirectTools` class or create a new test class that inherits from `unittest.TestCase`.

Example:

```python
def test_my_new_feature(self):
    """Test my new feature"""
    # Setup
    # ...
    
    # Execute
    result = self.multiplexer.execute_tool(
        "my-provider.my-tool",
        {"param1": "value1", "param2": "value2"}
    )
    
    # Assert
    self.assertTrue(result.get("success", False))
    self.assertEqual(result.get("some_value"), "expected_value")
```

