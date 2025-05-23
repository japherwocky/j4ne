#!/usr/bin/env python3
import asyncio
import sys
import json
from typing import Dict, Any, List

# ---- Configuration ---- #
FILESYSTEM_SERVER = './servers/filesystem.py'
FILESYSTEM_ARG = '.'  # Root directory argument
FS_PREFIX = 'fs_'

SQLITE_SERVER = './servers/localsqlite.py'
SQLITE_ARG = './db.sqlite3'
DB_PREFIX = 'db_'

# ---- Helper Functions ---- #
async def start_child(path: str, arg: str):
    proc = await asyncio.create_subprocess_exec(
        sys.executable, path, arg,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    return proc

async def send_recv(proc, msg: Dict[str, Any]):
    data = (json.dumps(msg) + '\n').encode()
    proc.stdin.write(data)
    await proc.stdin.drain()
    line = await proc.stdout.readline()
    return json.loads(line.decode()) if line else {}

# ---- Multiplexer core ---- #
class MCPMultiplexer:
    def __init__(self):
        self.children = {}
        self.tool_map = {}  # tool_name -> child_key

    async def start(self):
        self.children['fs'] = await start_child(FILESYSTEM_SERVER, FILESYSTEM_ARG)
        self.children['db'] = await start_child(SQLITE_SERVER, SQLITE_ARG)
        # On start, get tool lists and map them.
        await self._register_tools()

    async def _register_tools(self):
        # 1. Send "initialize" to both children and wait for confirmation
        for key, child in self.children.items():
            try:
                resp = await send_recv(child, {"type": "initialize"})
                print(f"Child {key} initialized: {resp}", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"Failed to initialize child {key}: {e}", file=sys.stderr, flush=True)
                                                                                                                                                                
        # 2. Proceed to list tools as before
        list_tools_msg = {"type": "list_tools"}
        db_tools = (await send_recv(self.children['db'], list_tools_msg)).get("tools", [])
        fs_tools = (await send_recv(self.children['fs'], list_tools_msg)).get("tools", [])
                                                                                                                                                                
        self.tool_map = {}
        for t in fs_tools:
            self.tool_map[FS_PREFIX + t] = 'fs'
        for t in db_tools:
            self.tool_map[DB_PREFIX + t] = 'db'

    async def handle_message(self, msg: Dict[str, Any]):
        if msg['type'] == 'list_tools':
            # Merge tool lists from both
            fs_tools = (await send_recv(self.children['fs'], msg)).get('tools', [])
            db_tools = (await send_recv(self.children['db'], msg)).get('tools', [])
            return {"type": "list_tools", "tools": [FS_PREFIX+t for t in fs_tools] + [DB_PREFIX+t for t in db_tools]}
        elif msg['type'] == 'call_tool':
            tool = msg.get('tool')
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
        # could handle list_resources, etc, similarly
        else:
            return {"type": "error", "error": "Unsupported message type"}

async def amain():
    mux = MCPMultiplexer()
    await mux.start()
    while True:
        line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        try:
            msg = json.loads(line)
            resp = await mux.handle_message(msg)
        except Exception as e:
            resp = {"type": "error", "error": str(e)}
        print(json.dumps(resp), flush=True)

if __name__ == "__main__":
    asyncio.run(amain())
