#!/usr/bin/env python3
import sys
import asyncio
import json
                                                                                                                        
# Change these as needed for future extension:
TOOL_CHILDREN = {
    "filesystem": {
        "filename": "./servers/filesystem.py",  # path to the child
        "arg": ".",                             # root directory arg for now
        "prefix": "filesystem",
        "tools": None,                          # to be discovered
        "proc": None                            # will become a subprocess handle
    }
}
                                                                                                                        
async def start_child_server(child):
    proc = await asyncio.create_subprocess_exec(
        sys.executable, child["filename"], child["arg"],
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
    )
    return proc
                                                                                                                        
async def send_recv(proc, msg):
    # MCP usually means newline-delimited JSON
    wire = (json.dumps(msg) + "\n").encode()
    proc.stdin.write(wire)
    await proc.stdin.drain()
    line = await proc.stdout.readline()
    return json.loads(line)
                                                                                                                        
async def main():
    # Start all child servers, handshake them with MCP
    for child in TOOL_CHILDREN.values():
        child["proc"] = await start_child_server(child)
        # MCP handshake
        resp = await send_recv(child["proc"], {"type": "initialize"})
        # Store tools list and prefix them
        child["tools"] = [
            child["prefix"] + "." + t for t in resp.get("tools", [])
        ]
                                                                                                                        
    # MCP handshake for *this* multiplexer itself!
    # Wait for initialize from client:
    while True:
        # This blocks until first client msg
        line = sys.stdin.readline()
        if not line:
            return
        msg = json.loads(line)
                                                                                                                        
        if msg.get("type") == "initialize":
            # Aggregate all available tool specs
            all_tools = []
            for child in TOOL_CHILDREN.values():
                all_tools.extend(child["tools"] or [])
            reply = {"type": "initialize", "id": msg.get("id"), "tools": all_tools}
            print(json.dumps(reply), flush=True)
            break
        else:
            # refuse until we see initialize
            print(json.dumps({"type": "error", "id": msg.get("id"), "error": "expected initialize as first msg"}),      
flush=True)
                                                                                                                        
    # Main MCP loop
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        msg = json.loads(line)
                                                                                                                        
        # Handle list_tools
        if msg.get("type") == "list_tools":
            all_tools = []
            for child in TOOL_CHILDREN.values():
                all_tools.extend(child["tools"] or [])
            reply = {"type": "list_tools", "id": msg.get("id"), "tools": all_tools}
            print(json.dumps(reply), flush=True)
            continue
                                                                                                                        
        # All tool calls look like {type: "call_tool", id, tool, ...}
        if msg.get("type") == "call_tool":
            tool = msg.get("tool")
            if not tool:
                print(json.dumps({"type": "error", "id": msg.get("id"), "error": "no tool given"}), flush=True)
                continue
                                                                                                                        
            matched = None
            for child in TOOL_CHILDREN.values():
                if child['tools'] and tool in child['tools']:
                    matched = child
                    real_tool = tool[len(child["prefix"]) + 1:]  # strip prefix + '.'
                    break
                                                                                                                        
            if not matched:
                print(json.dumps({"type": "error", "id": msg.get("id"), "error": f"unknown tool: {tool}"}), flush=True) 
                continue
                                                                                                                        
            # Forward request (with tool name rewritten):
            forward = dict(msg)
            forward['tool'] = real_tool
            resp = await send_recv(matched["proc"], forward)
            # Must preserve the original 'id'
            resp["id"] = msg["id"]
            print(json.dumps(resp), flush=True)
            continue
                                                                                                                        
        # fallback: error
        print(json.dumps({"type": "error", "id": msg.get("id"), "error": "unknown message type"}), flush=True)
                                                                                                                        
if __name__ == "__main__":
    asyncio.run(main())