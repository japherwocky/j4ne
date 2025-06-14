#!/usr/bin/env python3
import asyncio
import sys
import json
import os
import platform
import traceback
from typing import Dict, Any, List, Optional
import time

# ---- Configuration ---- #
# Determine the Python executable path based on the platform
if platform.system() == "Windows":
    PYTHON_EXECUTABLE = os.path.join(".venv", "Scripts", "python.exe")
else:
    PYTHON_EXECUTABLE = os.path.join(".venv", "bin", "python")

# For debugging, print the executable path
print(f"Using Python executable: {PYTHON_EXECUTABLE}", file=sys.stderr, flush=True)
print(f"Current working directory: {os.getcwd()}", file=sys.stderr, flush=True)

# Server paths and arguments
FILESYSTEM_SERVER = './servers/filesystem.py'
FILESYSTEM_ARG = '.'  # Root directory argument
FS_PREFIX = 'fs_'

SQLITE_SERVER = './servers/localsqlite.py'
SQLITE_ARG = './db.sqlite3'  # Match the database path used in the code
DB_PREFIX = 'db_'

# Timeout settings
PROCESS_START_TIMEOUT = 10  # seconds
SEND_RECV_TIMEOUT = 5  # seconds

# ---- Helper Functions ---- #
async def start_child(path: str, arg: str):
    """Start a child process with the given path and argument."""
    try:
        print(f"Starting child process: {PYTHON_EXECUTABLE} {path} {arg}", file=sys.stderr, flush=True)
        
        # Check if the file exists
        if not os.path.exists(path):
            print(f"ERROR: File {path} does not exist!", file=sys.stderr, flush=True)
            raise FileNotFoundError(f"File {path} does not exist")
            
        # Create a simple wrapper script to handle initialization
        wrapper_content = f"""#!/usr/bin/env python3
import sys
import json

# Send an immediate response to initialize message
print(json.dumps({{"type": "initialize_response", "status": "ok"}}), flush=True)

# Now execute the actual script
import os
import subprocess
os.execv(sys.executable, [sys.executable, "{path}", "{arg}"])
"""
        wrapper_path = f"{path}.wrapper.py"
        with open(wrapper_path, "w") as f:
            f.write(wrapper_content)
        
        print(f"Created wrapper script at {wrapper_path}", file=sys.stderr, flush=True)
            
        proc = await asyncio.create_subprocess_exec(
            PYTHON_EXECUTABLE, wrapper_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        print(f"Started child process for {path} with PID {proc.pid}", file=sys.stderr, flush=True)
        return proc
    except Exception as e:
        print(f"Error starting child process {path}: {e}", file=sys.stderr, flush=True)
        print(f"Traceback: {traceback.format_exc()}", file=sys.stderr, flush=True)
        raise

async def send_recv(proc, msg: Dict[str, Any], timeout: float = SEND_RECV_TIMEOUT):
    """Send a message to a child process and receive a response with timeout."""
    try:
        print(f"Sending message to child: {msg}", file=sys.stderr, flush=True)
        data = (json.dumps(msg) + '\n').encode()
        proc.stdin.write(data)
        await proc.stdin.drain()
        
        print(f"Waiting for response from child (timeout: {timeout}s)...", file=sys.stderr, flush=True)
        
        # Use asyncio.wait_for to implement timeout
        try:
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
            if not line:
                stderr = await proc.stderr.read()
                print(f"Child process error: {stderr.decode()}", file=sys.stderr, flush=True)
                return {"type": "error", "error": "No response from child process"}
            response = json.loads(line.decode())
            print(f"Received response from child: {response}", file=sys.stderr, flush=True)
            return response
        except asyncio.TimeoutError:
            print(f"Timeout waiting for response after {timeout}s", file=sys.stderr, flush=True)
            # Try to read stderr to see if there's any error information
            try:
                stderr = await asyncio.wait_for(proc.stderr.read(), timeout=1.0)
                if stderr:
                    print(f"Child process stderr: {stderr.decode()}", file=sys.stderr, flush=True)
            except asyncio.TimeoutError:
                pass
            
            # Return a timeout error
            return {"type": "error", "error": f"Timeout waiting for response after {timeout}s"}
            
    except Exception as e:
        print(f"Error in send_recv: {e}", file=sys.stderr, flush=True)
        print(f"Traceback: {traceback.format_exc()}", file=sys.stderr, flush=True)
        return {"type": "error", "error": str(e)}

# ---- Multiplexer core ---- #
class MCPMultiplexer:
    def __init__(self):
        self.children = {}
        self.tool_map = {}  # tool_name -> child_key

    async def start(self):
        """Start all child processes and register their tools."""
        try:
            print("Starting filesystem child process...", file=sys.stderr, flush=True)
            try:
                self.children['fs'] = await start_child(FILESYSTEM_SERVER, FILESYSTEM_ARG)
                print("Filesystem child process started successfully", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"Failed to start filesystem child process: {e}", file=sys.stderr, flush=True)
                print("Continuing without filesystem tools...", file=sys.stderr, flush=True)
        
            print("Starting database child process...", file=sys.stderr, flush=True)
            try:
                self.children['db'] = await start_child(SQLITE_SERVER, SQLITE_ARG)
                print("Database child process started successfully", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"Failed to start database child process: {e}", file=sys.stderr, flush=True)
                print("Continuing without database tools...", file=sys.stderr, flush=True)
        
            # Check if we have at least one child process
            if not self.children:
                print("ERROR: No child processes could be started!", file=sys.stderr, flush=True)
                raise RuntimeError("Failed to start any child processes")
        
            # On start, get tool lists and map them.
            print("Registering tools from child processes...", file=sys.stderr, flush=True)
            await self._register_tools()
            print("Multiplexer initialization complete", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"Error in start: {e}", file=sys.stderr, flush=True)
            print(f"Traceback: {traceback.format_exc()}", file=sys.stderr, flush=True)
            raise

    async def _register_tools(self):
        """Register tools from all child processes."""
        # 1. Send "initialize" to both children and wait for confirmation
        for key, child in self.children.items():
            try:
                print(f"Initializing child {key}...", file=sys.stderr, flush=True)
                resp = await send_recv(child, {"type": "initialize"})
                print(f"Child {key} initialized: {resp}", file=sys.stderr, flush=True)
                
                # If initialization failed, log but continue
                if resp.get("type") == "error":
                    print(f"Warning: Child {key} initialization returned error: {resp.get('error')}", 
                          file=sys.stderr, flush=True)
            except Exception as e:
                print(f"Failed to initialize child {key}: {e}", file=sys.stderr, flush=True)
                print(f"Continuing with other child processes...", file=sys.stderr, flush=True)
                                                                                                                                                                
        # 2. Proceed to list tools
        list_tools_msg = {"type": "list_tools"}
        
        # Get tools from each child process
        db_tools = []
        fs_tools = []
        
        # Try to get tools from database child
        if 'db' in self.children:
            try:
                print(f"Getting tools from database child...", file=sys.stderr, flush=True)
                db_resp = await send_recv(self.children['db'], list_tools_msg)
                if db_resp.get("type") != "error":
                    db_tools = db_resp.get("tools", [])
                    print(f"Got {len(db_tools)} tools from database child", file=sys.stderr, flush=True)
                else:
                    print(f"Error getting DB tools: {db_resp.get('error')}", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"Error getting DB tools: {e}", file=sys.stderr, flush=True)
        else:
            print("Database child not available", file=sys.stderr, flush=True)
        
        # Try to get tools from filesystem child
        if 'fs' in self.children:
            try:
                print(f"Getting tools from filesystem child...", file=sys.stderr, flush=True)
                fs_resp = await send_recv(self.children['fs'], list_tools_msg)
                if fs_resp.get("type") != "error":
                    fs_tools = fs_resp.get("tools", [])
                    print(f"Got {len(fs_tools)} tools from filesystem child", file=sys.stderr, flush=True)
                else:
                    print(f"Error getting FS tools: {fs_resp.get('error')}", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"Error getting FS tools: {e}", file=sys.stderr, flush=True)
        else:
            print("Filesystem child not available", file=sys.stderr, flush=True)
                                                                                                                                                                
        # Map tools to their respective child processes
        self.tool_map = {}
        for t in fs_tools:
            self.tool_map[FS_PREFIX + t] = 'fs'
        for t in db_tools:
            self.tool_map[DB_PREFIX + t] = 'db'
            
        print(f"Registered tools: {list(self.tool_map.keys())}", file=sys.stderr, flush=True)

    async def handle_message(self, msg: Dict[str, Any]):
        """Handle a message from the parent process."""
        try:
            if msg['type'] == 'initialize':
                return {"type": "initialize_response", "status": "ok"}
            elif msg['type'] == 'list_tools':
                # Merge tool lists from both children
                fs_tools = []
                db_tools = []
                
                # Only try to get tools from filesystem if it's available
                if 'fs' in self.children:
                    try:
                        fs_resp = await send_recv(self.children['fs'], msg)
                        if fs_resp.get("type") != "error":
                            fs_tools = fs_resp.get('tools', [])
                        else:
                            print(f"Error listing FS tools: {fs_resp.get('error')}", file=sys.stderr, flush=True)
                    except Exception as e:
                        print(f"Error listing FS tools: {e}", file=sys.stderr, flush=True)
            
                # Only try to get tools from database if it's available
                if 'db' in self.children:
                    try:
                        db_resp = await send_recv(self.children['db'], msg)
                        if db_resp.get("type") != "error":
                            db_tools = db_resp.get('tools', [])
                        else:
                            print(f"Error listing DB tools: {db_resp.get('error')}", file=sys.stderr, flush=True)
                    except Exception as e:
                        print(f"Error listing DB tools: {e}", file=sys.stderr, flush=True)
                    
                return {
                    "type": "list_tools", 
                    "tools": [FS_PREFIX+t for t in fs_tools] + [DB_PREFIX+t for t in db_tools]
                }
            elif msg['type'] == 'call_tool':
                tool = msg.get('tool')
                if not tool:
                    return {"type": "error", "error": "No tool specified"}
                    
                if tool.startswith(FS_PREFIX):
                    if 'fs' not in self.children:
                        return {"type": "error", "error": "Filesystem child process not available"}
                    real_tool = tool[len(FS_PREFIX):]
                    msg2 = dict(msg)
                    msg2['tool'] = real_tool
                    return await send_recv(self.children['fs'], msg2)
                elif tool.startswith(DB_PREFIX):
                    if 'db' not in self.children:
                        return {"type": "error", "error": "Database child process not available"}
                    real_tool = tool[len(DB_PREFIX):]
                    msg2 = dict(msg)
                    msg2['tool'] = real_tool
                    return await send_recv(self.children['db'], msg2)
                else:
                    return {"type": "error", "error": f"Unknown tool prefix for tool '{tool}'"}
            # Handle list_resources, etc. similarly
            else:
                return {"type": "error", "error": f"Unsupported message type: {msg['type']}"}
        except Exception as e:
            print(f"Error in handle_message: {e}", file=sys.stderr, flush=True)
            print(f"Traceback: {traceback.format_exc()}", file=sys.stderr, flush=True)
            return {"type": "error", "error": str(e)}

async def amain():
    """Main async function."""
    try:
        print("Starting multiplexer...", file=sys.stderr, flush=True)
        mux = MCPMultiplexer()
        await mux.start()
        
        print("Multiplexer started successfully, entering main loop", file=sys.stderr, flush=True)
        
        while True:
            print("Waiting for input...", file=sys.stderr, flush=True)
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                print("End of input, exiting", file=sys.stderr, flush=True)
                break
                
            try:
                print(f"Received input: {line.strip()}", file=sys.stderr, flush=True)
                msg = json.loads(line)
                resp = await mux.handle_message(msg)
                print(f"Sending response: {resp}", file=sys.stderr, flush=True)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}", file=sys.stderr, flush=True)
                resp = {"type": "error", "error": f"Invalid JSON: {str(e)}"}
            except Exception as e:
                print(f"Error processing message: {e}", file=sys.stderr, flush=True)
                print(f"Traceback: {traceback.format_exc()}", file=sys.stderr, flush=True)
                resp = {"type": "error", "error": str(e)}
                
            print(json.dumps(resp), flush=True)
    except Exception as e:
        print(f"Fatal error in amain: {e}", file=sys.stderr, flush=True)
        print(f"Traceback: {traceback.format_exc()}", file=sys.stderr, flush=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(amain())
