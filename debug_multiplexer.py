#!/usr/bin/env python3
import os
import sys
import platform
import asyncio
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Load environment variables
load_dotenv()

async def main():
    """
    Debug script to test the multiplexer directly.
    """
    # Determine the Python executable path based on the platform
    if platform.system() == "Windows":
        python_executable = os.path.join(".venv", "Scripts", "python.exe")
    else:
        python_executable = os.path.join(".venv", "bin", "python")
    
    logging.info(f"Using Python executable: {python_executable}")
    logging.info(f"Current working directory: {os.getcwd()}")
    
    # Start the multiplexer process
    logging.info("Starting multiplexer process...")
    
    try:
        proc = await asyncio.create_subprocess_exec(
            python_executable, 
            "./servers/multiplexer_fixed.py",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        logging.info(f"Multiplexer process started with PID {proc.pid}")
        
        # Create a task to read stderr continuously
        async def read_stderr():
            while True:
                line = await proc.stderr.readline()
                if not line:
                    break
                logging.info(f"MULTIPLEXER STDERR: {line.decode().strip()}")
        
        stderr_task = asyncio.create_task(read_stderr())
        
        # Send initialize message
        logging.info("Sending initialize message...")
        init_msg = '{"type": "initialize"}\n'
        proc.stdin.write(init_msg.encode())
        await proc.stdin.drain()
        
        # Read response
        response = await proc.stdout.readline()
        logging.info(f"Initialize response: {response.decode().strip()}")
        
        # Send list_tools message
        logging.info("Sending list_tools message...")
        tools_msg = '{"type": "list_tools"}\n'
        proc.stdin.write(tools_msg.encode())
        await proc.stdin.drain()
        
        # Read response
        response = await proc.stdout.readline()
        logging.info(f"List tools response: {response.decode().strip()}")
        
        # Wait for a moment to see all stderr output
        await asyncio.sleep(5)
        
        # Clean up
        stderr_task.cancel()
        proc.terminate()
        await proc.wait()
        
    except Exception as e:
        logging.error(f"Error: {e}")
        import traceback
        logging.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())

