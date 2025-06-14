# Debugging the J4NE Agent System

This document provides guidance on debugging the J4NE agent system, particularly focusing on the multiplexer component which is responsible for connecting the agent to various tool servers.

## Common Issues

### 1. Multiplexer Freezing

The most common issue is the multiplexer freezing after displaying "Launching MCP Server". This typically happens because:

- Child processes (filesystem or database servers) aren't responding to initialization messages
- Communication between processes is getting stuck
- Timeouts aren't being properly handled

### 2. Missing Tools

Sometimes the agent might start but report that certain tools are unavailable. This can happen when:

- One of the child processes failed to start
- Tool registration failed
- The multiplexer couldn't communicate with a child process

## Debugging Steps

### 1. Use the Debug Script

We've created a dedicated debugging script that helps isolate multiplexer issues:

```bash
# On Windows
.\.venv\Scripts\python.exe .\debug_multiplexer.py

# On Unix/Linux/Mac
./.venv/bin/python ./debug_multiplexer.py
```

This script:
- Starts the multiplexer in isolation
- Captures and displays all stderr output
- Sends test messages to verify communication
- Implements timeouts to prevent hanging

### 2. Check Wrapper Scripts

The fixed multiplexer creates wrapper scripts for child processes to ensure they respond to initialization messages. Check if these wrapper scripts are being created correctly:

```bash
# Look for wrapper scripts
ls -la ./servers/*.wrapper.py
```

### 3. Test Individual Servers

You can test the individual servers directly to see if they work on their own:

```bash
# Test filesystem server
.\.venv\Scripts\python.exe .\servers\filesystem.py .

# Test database server
.\.venv\Scripts\python.exe .\servers\localsqlite.py ./db.sqlite3
```

Note: These servers expect to communicate via stdin/stdout, so they may appear to hang when run directly. This is normal.

### 4. Enable Verbose Logging

Run the agent with verbose logging enabled:

```bash
python j4ne.py chat --verbose
```

### 5. Check for Process Orphans

If the multiplexer crashes, it might leave orphaned child processes:

```bash
# On Windows
tasklist | findstr python

# On Unix/Linux/Mac
ps aux | grep python
```

Kill any orphaned processes before trying again.

## Using the Fixed Multiplexer

The repository includes an enhanced version of the multiplexer (`multiplexer_fixed.py`) with the following improvements:

1. **Timeout Handling**: Prevents indefinite hanging when child processes don't respond
2. **Wrapper Scripts**: Creates wrapper scripts that ensure child processes respond to initialization
3. **Error Handling**: Gracefully handles failures in child processes
4. **Detailed Logging**: Provides comprehensive logging to help diagnose issues
5. **Cross-Platform Support**: Works correctly on both Windows and Unix systems

To use the fixed multiplexer:

1. Make sure you're using the latest version from the repository
2. Run the debug script first to verify it works correctly
3. If the debug script works, try running the full agent

## Advanced Debugging

For more advanced debugging:

1. **Modify Timeout Values**: You can adjust the timeout values in `multiplexer_fixed.py`:
   ```python
   PROCESS_START_TIMEOUT = 10  # seconds
   SEND_RECV_TIMEOUT = 5  # seconds
   ```

2. **Check Database Path**: Ensure the database path in `multiplexer_fixed.py` matches your actual database file:
   ```python
   SQLITE_ARG = './db.sqlite3'  # Should match your database path
   ```

3. **Inspect Wrapper Scripts**: Look at the generated wrapper scripts to ensure they're correctly formatted:
   ```bash
   cat ./servers/filesystem.py.wrapper.py
   ```

4. **Monitor Process Communication**: You can use tools like `strace` (Linux) or Process Monitor (Windows) to monitor the communication between processes.

## Reporting Issues

If you continue to experience issues after following these debugging steps, please report them with:

1. The exact command you're running
2. The complete output including any error messages
3. Your operating system and Python version
4. The contents of any generated wrapper scripts
5. The output from the debug script

