#!/usr/bin/env python3
"""
Entry point script for running the direct client.
"""

import asyncio
import argparse
import os
from direct_client import DirectClient

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Run the direct client")
    parser.add_argument(
        "--root-path",
        type=str,
        default="./",
        help="Root path for filesystem operations (default: ./)"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="./database.db",
        help="Path to the SQLite database (default: ./database.db)"
    )
    return parser.parse_args()

async def main():
    """Main entry point"""
    args = parse_args()
    
    # Create and run the client
    client = DirectClient(
        root_path=args.root_path,
        db_path=args.db_path
    )
    
    try:
        await client.chat_loop()
    finally:
        client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())

