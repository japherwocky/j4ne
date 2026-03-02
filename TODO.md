# TODO: Implement /thinking and /tools toggle commands

## Overview
Add session-wide toggles to show raw LLM messages and detailed tool execution.

## Files to Modify

### 1. `tools/direct_client.py`
- Add instance variables:
  - `self.show_thinking = False` - toggle for raw LLM messages
  - `self.show_tool_calls = False` - toggle for detailed tool execution
- Modify `_handle_response()` to:
  - Print full LLM message when `show_thinking` is True
  - Print detailed tool info (args, timing, results) when `show_tool_calls` is True
- Add helper methods:
  - `toggle_thinking()` - returns new state
  - `toggle_tools()` - returns new state

### 2. `tools/commands/__init__.py`
- Add new command handler for `/thinking`
  - Calls `client.toggle_thinking()`
  - Returns status message: "Thinking display: ON/OFF"
- Add new command handler for `/tools`
  - Calls `client.toggle_tools()`
  - Returns status message: "Tool visibility: ON/OFF"

### 3. `j4ne.py` (optional)
- Consider adding CLI flags `--thinking` and `--tools` to enable at startup

## Example Usage

```
> /thinking
Thinking display: ON

> /tools
Tool visibility: ON

> list files in chatters
[Raw LLM message content here]

Called tool filesystem.list-files (args: {'directory': 'chatters'})
💭 Tool executed in 0.05s
[Tool result summary]

> /thinking
Thinking display: OFF

> /tools
Tool visibility: OFF
```

## Implementation Order
1. Add state flags and toggle methods to `DirectClient`
2. Update `_handle_response()` to check flags and output verbose info
3. Add command handlers in `commands/__init__.py`
4. Test the toggles work correctly
