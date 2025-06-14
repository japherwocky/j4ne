#!/usr/bin/env python3
import asyncio
import sys
import json
import os
import platform
from typing import Dict, Any, List

# ---- Configuration ---- #
# Determine the Python executable path based on the platform
if platform.system() == "Windows":
    PYTHON_EXECUTABLE = os.path.join(".venv", "Scripts", "python.exe")
else:
    PYTHON_EXECUTABLE = os.path.join(".venv", "bin", "python")

# Server paths and arguments
FILESYSTEM_SERVER = './servers/filesystem.py'
FILESYSTEM_ARG = '.'  # Root directory argument
FS_PREFIX = 'fs_'

SQLITE_SERVER = './servers/localsqlite.py'
SQLITE_ARG = './database.db'
DB_PREFIX = 'db_'

# ---- Helper Functions ---- #
async def start_child(path: str, arg: str):
    """Start a child process with the given path and argument."""
    try:
        proc = await asyncio.create_subprocess_exec(
            PYTHON_EXECUTABLE, path, arg,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        print(f"Started child process for {path} with PID {proc.pid}", file=sys.stderr, flush=True)
        return proc
    except Exception as e:
        print(f"Error starting child process {path}: {e}", file=sys.stderr, flush=True)
        raise

async def send_recv(proc, msg: Dict[str, Any]):
    """Send a message to a child process and receive a response."""
    try:
        data = (json.dumps(msg) + '\n').encode()
        proc.stdin.write(data)
        await proc.stdin.drain()
        line = await proc.stdout.readline()
        if not line:
            stderr = await proc.stderr.read()
            print(f"Child process error: {stderr.decode()}", file=sys.stderr, flush=True)
            return {"type": "error", "error": "No response from child process"}
        return json.loads(line.decode())
    except Exception as e:
        print(f"Error in send_recv: {e}", file=sys.stderr, flush=True)
        return {"type": "error", "error": str(e)}

# ---- Multiplexer core ---- #
class MCPMultiplexer:
    def __init__(self):
        self.children = {}
        self.tool_map = {}  # tool_name -> child_key

    async def start(self):
        """Start all child processes and register their tools."""
        try:
            self.children['fs'] = await start_child(FILESYSTEM_SERVER, FILESYSTEM_ARG)
            self.children['db'] = await start_child(SQLITE_SERVER, SQLITE_ARG)
            # On start, get tool lists and map them.
            await self._register_tools()
        except Exception as e:
            print(f"Error in start: {e}", file=sys.stderr, flush=True)
            raise

    async def _register_tools(self):
        """Register tools from all child processes."""
        # 1. Send "initialize" to both children and wait for confirmation
        for key, child in self.children.items():
            try:
                resp = await send_recv(child, {"type": "initialize"})
                print(f"Child {key} initialized: {resp}", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"Failed to initialize child {key}: {e}", file=sys.stderr, flush=True)
                                                                                                                                                                
        # 2. Proceed to list tools
        list_tools_msg = {"type": "list_tools"}
        
        # Get tools from each child process
        db_tools = []
        fs_tools = []
        
        try:
            db_resp = await send_recv(self.children['db'], list_tools_msg)
            db_tools = db_resp.get("tools", [])
        except Exception as e:
            print(f"Error getting DB tools: {e}", file=sys.stderr, flush=True)
            
        try:
            fs_resp = await send_recv(self.children['fs'], list_tools_msg)
            fs_tools = fs_resp.get("tools", [])
        except Exception as e:
            print(f"Error getting FS tools: {e}", file=sys.stderr, flush=True)
                                                                                                                                                                
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
                
                try:
                    fs_resp = await send_recv(self.children['fs'], msg)
                    fs_tools = fs_resp.get('tools', [])
                except Exception as e:
                    print(f"Error listing FS tools: {e}", file=sys.stderr, flush=True)
                    
                try:
                    db_resp = await send_recv(self.children['db'], msg)
                    db_tools = db_resp.get('tools', [])
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
                    real_tool = tool[len(FS_PREFIX):]
                    msg2 = dict(msg)
                    msg2['tool'] = real_tool
                    return await send_recv(self.children['fs'], msg2)
                elif tool.startswith(DB_PREFIX):
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
            return {"type": "error", "error": str(e)}

async def amain():
    """Main async function."""
    try:
        mux = MCPMultiplexer()
        await mux.start()
        
        print("Multiplexer started successfully", file=sys.stderr, flush=True)
        
        while True:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                print("End of input, exiting", file=sys.stderr, flush=True)
                break
                
            try:
                msg = json.loads(line)
                resp = await mux.handle_message(msg)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}", file=sys.stderr, flush=True)
                resp = {"type": "error", "error": f"Invalid JSON: {str(e)}"}
            except Exception as e:
                print(f"Error processing message: {e}", file=sys.stderr, flush=True)
                resp = {"type": "error", "error": str(e)}
                
            print(json.dumps(resp), flush=True)
    except Exception as e:
        print(f"Fatal error in amain: {e}", file=sys.stderr, flush=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(amain())

