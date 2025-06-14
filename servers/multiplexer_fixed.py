#!/usr/bin/env python3
import asyncio
import sys
import json
import logging
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('multiplexer')

# ---- Configuration ---- #
FILESYSTEM_SERVER = './servers/filesystem.py'
FILESYSTEM_ARG = '.'  # Root directory argument
FS_PREFIX = 'fs_'

SQLITE_SERVER = './servers/localsqlite.py'
SQLITE_ARG = './db.sqlite3'
DB_PREFIX = 'db_'

# ---- Helper Functions ---- #
async def start_child(path: str, arg: str, timeout: int = 10):
    """Start a child process with timeout to prevent hanging"""
    logger.debug(f"Starting child process: {path} {arg}")
    try:
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                sys.executable, path, arg,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            ), 
            timeout
        )
        logger.debug(f"Child process started: {path}")
        return proc
    except asyncio.TimeoutError:
        logger.error(f"Timeout starting child process: {path}")
        return None
    except Exception as e:
        logger.error(f"Error starting child process {path}: {e}")
        return None

async def send_recv(proc, msg: Dict[str, Any], timeout: int = 5):
    """Send a message to a child process and receive a response with timeout"""
    if proc is None:
        return {"type": "error", "error": "Process not available"}
    
    try:
        data = (json.dumps(msg) + '\n').encode()
        proc.stdin.write(data)
        await asyncio.wait_for(proc.stdin.drain(), timeout)
        line = await asyncio.wait_for(proc.stdout.readline(), timeout)
        if not line:
            return {"type": "error", "error": "Empty response from child process"}
        return json.loads(line.decode())
    except asyncio.TimeoutError:
        logger.error(f"Timeout in send_recv: {msg}")
        return {"type": "error", "error": "Timeout waiting for response"}
    except Exception as e:
        logger.error(f"Error in send_recv: {e}")
        return {"type": "error", "error": str(e)}

# ---- Multiplexer core ---- #
class MCPMultiplexer:
    def __init__(self):
        self.children = {}
        self.tool_map = {}  # tool_name -> child_key
        self.initialized = False

    async def start(self):
        """Start the child processes and initialize them"""
        logger.info("Starting multiplexer")
        
        # Start filesystem server
        self.children['fs'] = await start_child(FILESYSTEM_SERVER, FILESYSTEM_ARG)
        if self.children['fs'] is None:
            logger.error("Failed to start filesystem server")
            return False
            
        # Start database server
        self.children['db'] = await start_child(SQLITE_SERVER, SQLITE_ARG)
        if self.children['db'] is None:
            logger.error("Failed to start database server")
            # Cleanup filesystem server
            if 'fs' in self.children and self.children['fs']:
                self.children['fs'].terminate()
            return False
        
        # Initialize the servers
        success = await self._register_tools()
        self.initialized = success
        return success

    async def _register_tools(self):
        """Initialize the child processes and register their tools"""
        # 1. Send "initialize" to both children and wait for confirmation
        for key, child in self.children.items():
            try:
                logger.debug(f"Initializing child: {key}")
                resp = await send_recv(child, {"type": "initialize"})
                logger.info(f"Child {key} initialized: {resp}")
                if "error" in resp:
                    logger.error(f"Error initializing child {key}: {resp['error']}")
                    return False
            except Exception as e:
                logger.error(f"Failed to initialize child {key}: {e}")
                return False
                                                                                                                                                                
        # 2. List tools from each child
        list_tools_msg = {"type": "list_tools"}
        
        logger.debug("Listing tools from database server")
        db_tools_resp = await send_recv(self.children['db'], list_tools_msg)
        if "error" in db_tools_resp:
            logger.error(f"Error listing DB tools: {db_tools_resp['error']}")
            return False
        db_tools = db_tools_resp.get("tools", [])
        
        logger.debug("Listing tools from filesystem server")
        fs_tools_resp = await send_recv(self.children['fs'], list_tools_msg)
        if "error" in fs_tools_resp:
            logger.error(f"Error listing FS tools: {fs_tools_resp['error']}")
            return False
        fs_tools = fs_tools_resp.get("tools", [])
                                                                                                                                                                
        self.tool_map = {}
        for t in fs_tools:
            self.tool_map[FS_PREFIX + t] = 'fs'
        for t in db_tools:
            self.tool_map[DB_PREFIX + t] = 'db'
            
        logger.info(f"Registered tools: {list(self.tool_map.keys())}")
        return True

    async def handle_message(self, msg: Dict[str, Any]):
        """Handle a message from the client"""
        if not self.initialized:
            return {"type": "error", "error": "Multiplexer not initialized"}
            
        try:
            if msg['type'] == 'list_tools':
                logger.debug("Handling list_tools request")
                # Merge tool lists from both
                fs_tools_resp = await send_recv(self.children['fs'], msg)
                if "error" in fs_tools_resp:
                    logger.error(f"Error listing FS tools: {fs_tools_resp['error']}")
                    return fs_tools_resp
                fs_tools = fs_tools_resp.get('tools', [])
                
                db_tools_resp = await send_recv(self.children['db'], msg)
                if "error" in db_tools_resp:
                    logger.error(f"Error listing DB tools: {db_tools_resp['error']}")
                    return db_tools_resp
                db_tools = db_tools_resp.get('tools', [])
                
                return {
                    "type": "list_tools", 
                    "tools": [FS_PREFIX+t for t in fs_tools] + [DB_PREFIX+t for t in db_tools]
                }
            elif msg['type'] == 'call_tool':
                tool = msg.get('tool')
                logger.debug(f"Handling call_tool request for tool: {tool}")
                
                if tool.startswith(FS_PREFIX):
                    real_tool = tool[len(FS_PREFIX):]
                    msg2 = dict(msg)
                    msg2['tool'] = real_tool
                    logger.debug(f"Routing to filesystem server: {real_tool}")
                    return await send_recv(self.children['fs'], msg2)
                elif tool.startswith(DB_PREFIX):
                    real_tool = tool[len(DB_PREFIX):]
                    msg2 = dict(msg)
                    msg2['tool'] = real_tool
                    logger.debug(f"Routing to database server: {real_tool}")
                    return await send_recv(self.children['db'], msg2)
                else:
                    logger.error(f"Unknown tool prefix for tool '{tool}'")
                    return {"type": "error", "error": f"Unknown tool prefix for tool '{tool}'"}
            # could handle list_resources, etc, similarly
            else:
                logger.error(f"Unsupported message type: {msg['type']}")
                return {"type": "error", "error": "Unsupported message type"}
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return {"type": "error", "error": str(e)}
            
    async def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up multiplexer")
        for name, child in self.children.items():
            if child:
                logger.debug(f"Terminating child: {name}")
                try:
                    child.terminate()
                    await child.wait()
                except Exception as e:
                    logger.error(f"Error terminating child {name}: {e}")

async def amain():
    """Main entry point"""
    mux = MCPMultiplexer()
    success = await mux.start()
    if not success:
        logger.error("Failed to start multiplexer")
        await mux.cleanup()
        return
        
    try:
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                    
                msg = json.loads(line)
                resp = await mux.handle_message(msg)
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                resp = {"type": "error", "error": str(e)}
                
            print(json.dumps(resp), flush=True)
    finally:
        await mux.cleanup()

if __name__ == "__main__":
    asyncio.run(amain())

