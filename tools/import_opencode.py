"""
Import OpenCode sessions into j4ne's memory system.

This script reads OpenCode session data from its storage directory and imports
conversations, messages, and generates embeddings for semantic search.

Usage:
    python -m tools.import_opencode [--opencode-path PATH]

The script will:
1. Find OpenCode storage (or use provided path)
2. Import all sessions as Conversations
3. Import all messages with role/content
4. Generate embeddings for semantic search
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import memory
from memory import Embedder


# Global to store opencode path for message lookup
opencode_base_path = None


def find_opencode_storage() -> Optional[Path]:
    """Find OpenCode storage directory in common locations."""
    
    # Common locations for OpenCode data
    candidates = [
        # Windows
        Path(os.environ.get('APPDATA', '')) / 'opencode' / 'storage',
        Path(os.environ.get('LOCALAPPDATA', '')) / 'opencode' / 'storage',
        # Linux/Mac
        Path.home() / '.opencode' / 'storage',
        Path.home() / '.opencode',
        # Try current directory (dev mode)
        Path('.opencode') / 'storage',
        Path('.opencode'),
    ]
    
    for path in candidates:
        if path.exists():
            # Check for session or message directory structure
            if (path / 'session').exists() or (path / 'message').exists() or (path / 'storage' / 'session').exists():
                print(f"Found OpenCode storage at: {path}")
                return path
    
    return None


def read_json_file(path: Path) -> dict:
    """Read and parse a JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_session_files(storage_path: Path) -> List[Path]:
    """Find all session JSON files in the storage."""
    session_files = []
    
    # Check different possible structures
    search_paths = [
        storage_path / 'session',
        storage_path / 'storage' / 'session',
        storage_path / 'storage',
    ]
    
    for search_path in search_paths:
        if search_path.exists():
            # Recursively find all JSON files
            for json_file in search_path.rglob('*.json'):
                # Skip part files
                if 'part' in json_file.parts:
                    continue
                session_files.append(json_file)
    
    return session_files


def is_session_file(path: Path, data: dict) -> bool:
    """Check if a JSON file is a session file."""
    # Sessions have these fields
    return 'id' in data and ('title' in data or 'projectID' in data)


def find_message_files(storage_path: Path, session_id: str) -> List[Path]:
    """Find all message files for a session."""
    message_files = []
    
    # Check different possible paths
    search_paths = [
        storage_path / 'message' / session_id,
        storage_path / 'storage' / 'message' / session_id,
        storage_path / 'session' / session_id,  # Might be nested under session
    ]
    
    # Also check in storage/session/<projectID>/message/<session_id>
    storage_session = storage_path / 'storage' / 'session'
    if storage_session.exists():
        for project_dir in storage_session.iterdir():
            if project_dir.is_dir():
                alt_path = project_dir / 'message' / session_id
                if alt_path.exists():
                    search_paths.append(alt_path)
    
    for search_path in search_paths:
        if search_path.exists() and search_path.is_dir():
            for msg_file in search_path.glob('*.json'):
                message_files.append(msg_file)
    
    return message_files


def get_message_content(storage_path: Path, msg_data: dict) -> str:
    """Get the full content of a message, including parts."""
    content_parts = []
    
    msg_id = msg_data.get('id')
    session_id = msg_data.get('sessionID')
    
    # First check if content is directly in the message
    if 'content' in msg_data:
        if isinstance(msg_data['content'], str):
            content_parts.append(msg_data['content'])
        elif isinstance(msg_data['content'], list):
            # Array of parts - extract text
            for part in msg_data['content']:
                if isinstance(part, dict):
                    if part.get('type') == 'text':
                        content_parts.append(part.get('text', ''))
                    elif part.get('type') == 'reasoning':
                        content_parts.append(f"[Reasoning] {part.get('text', '')}")
    
    # Also check for separate parts files
    if msg_id and session_id:
        part_paths = [
            storage_path / 'part' / msg_id,
            storage_path / 'storage' / 'part' / msg_id,
        ]
        
        for part_path in part_paths:
            if part_path.exists() and part_path.is_dir():
                for part_file in sorted(part_path.glob('*.json')):
                    try:
                        part_data = read_json_file(part_file)
                        part_type = part_data.get('type', 'text')
                        part_text = part_data.get('text', '')
                        
                        if part_type == 'text':
                            content_parts.append(part_text)
                        elif part_type == 'reasoning':
                            content_parts.append(f"[Reasoning] {part_text}")
                        elif part_type == 'tool':
                            tool_name = part_data.get('tool', 'unknown')
                            state = part_data.get('state', {})
                            tool_input = state.get('input', '')
                            tool_output = state.get('output', '')
                            content_parts.append(f"[Tool: {tool_name}]\nInput: {tool_input}\nOutput: {tool_output}")
                    except Exception:
                        pass
    
    return '\n\n'.join(content_parts)


def import_sessions(opencode_path: Path) -> dict:
    """Import all sessions from OpenCode storage.
    
    Returns statistics about the import.
    """
    stats = {
        'sessions_imported': 0,
        'messages_imported': 0,
        'embeddings_created': 0,
        'errors': []
    }
    
    print(f"Scanning for session files in: {opencode_path}")
    
    session_files = find_session_files(opencode_path)
    print(f"Found {len(session_files)} potential session files")
    
    # Track seen sessions
    sessions_seen = {}
    
    for session_file in session_files:
        try:
            session_data = read_json_file(session_file)
            
            # Check if this is a session file
            if not is_session_file(session_file, session_data):
                continue
            
            session_id = session_data.get('id')
            if not session_id:
                continue
            
            if session_id in sessions_seen:
                continue
            
            sessions_seen[session_id] = session_data
            
        except Exception as e:
            stats['errors'].append(f"Error reading {session_file}: {e}")
    
    print(f"Found {len(sessions_seen)} unique sessions")
    
    # Import each session
    for session_id, session_data in sessions_seen.items():
        try:
            # Import session
            conv = import_session(session_data)
            
            if conv:
                stats['sessions_imported'] += 1
                
                # Import messages for this session
                msg_count = import_messages(opencode_path, session_id, conv.id)
                stats['messages_imported'] += msg_count
                
                title = session_data.get('title', 'Untitled')
                print(f"  Imported: {title} ({msg_count} messages)")
        
        except Exception as e:
            stats['errors'].append(f"Error importing session {session_id}: {e}")
            print(f"  Error: {e}")
    
    # Generate embeddings for all imported messages
    print("\nGenerating embeddings...")
    stats['embeddings_created'] = generate_embeddings_for_imported_messages()
    
    return stats


def import_session(session_data: dict) -> Optional[memory.Conversation]:
    """Import a single session as a Conversation."""
    
    # Parse timestamps
    time_data = session_data.get('time', {})
    created_at = datetime.now()
    updated_at = datetime.now()
    
    if time_data:
        created_ts = time_data.get('created')
        if created_ts:
            created_at = datetime.fromtimestamp(created_ts / 1000)
        
        updated_ts = time_data.get('updated')
        if updated_ts:
            updated_at = datetime.fromtimestamp(updated_ts / 1000)
    
    # Create conversation
    conv = memory.Conversation.create(
        user='imported',  # OpenCode doesn't track users in local storage
        platform='opencode',
        started_at=created_at,
        ended_at=updated_at,
        context_window=json.dumps({
            'title': session_data.get('title', 'Untitled'),
            'original_id': session_data.get('id'),
            'project_id': session_data.get('projectID'),
        })
    )
    
    return conv


def import_messages(storage_path: Path, session_id: str, conversation_id: int) -> int:
    """Import all messages for a session."""
    
    message_files = find_message_files(storage_path, session_id)
    message_count = 0
    
    for msg_file in message_files:
        try:
            msg_data = read_json_file(msg_file)
            
            # Skip if not a message (no role field)
            if 'role' not in msg_data:
                continue
            
            import_message(storage_path, msg_data, conversation_id)
            message_count += 1
            
        except Exception as e:
            print(f"    Error importing message {msg_file}: {e}")
    
    return message_count


def import_message(storage_path: Path, msg_data: dict, conversation_id: int):
    """Import a single message."""
    
    role = msg_data.get('role', 'assistant')
    
    # Get content from the message or parts
    content = get_message_content(storage_path, msg_data)
    
    if not content:
        # Fallback to any content field
        content = str(msg_data.get('content', ''))
    
    # Get timestamps
    time_data = msg_data.get('time', {})
    created_at = datetime.now()
    
    if time_data:
        created_ts = time_data.get('created')
        if created_ts:
            created_at = datetime.fromtimestamp(created_ts / 1000)
    
    # Store metadata (model, agent, etc)
    metadata = {
        'agent': msg_data.get('agent'),
        'model_id': msg_data.get('modelID') or msg_data.get('model', {}).get('modelID'),
        'provider_id': msg_data.get('providerID'),
    }
    
    # Store message
    memory.Message.create(
        conversation_id=conversation_id,
        role=role,
        content=content[:50000],  # Limit content length
        timestamp=created_at,
        metadata=json.dumps(metadata) if any(v for v in metadata.values()) else None
    )


def generate_embeddings_for_imported_messages() -> int:
    """Generate embeddings for all imported messages."""
    
    # Get all messages
    messages = list(memory.Message.select())
    
    count = 0
    for msg in messages:
        # Check if embedding already exists
        existing = memory.Embedding.get_or_none(
            (memory.Embedding.chunk_type == 'message') & 
            (memory.Embedding.source_id == msg.id)
        )
        
        if not existing and msg.content:
            try:
                # Generate embedding (limit content length for efficiency)
                content_for_embedding = msg.content[:5000]
                vector = Embedder.encode(content_for_embedding)
                
                memory.Embedding.create(
                    chunk=msg.content[:1000],  # Store truncated chunk
                    chunk_type='message',
                    source_id=msg.id,
                    vector=json.dumps(vector)
                )
                count += 1
            except Exception as e:
                print(f"    Error creating embedding for message {msg.id}: {e}")
    
    return count


def main():
    parser = argparse.ArgumentParser(description='Import OpenCode sessions into j4ne')
    parser.add_argument(
        '--opencode-path', 
        type=str, 
        help='Path to OpenCode storage directory'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be imported without importing'
    )
    
    args = parser.parse_args()
    
    # Initialize memory database
    print("Initializing memory database...")
    memory.init_db()
    
    # Find OpenCode storage
    if args.opencode_path:
        opencode_path = Path(args.opencode_path)
        if not opencode_path.exists():
            print(f"Error: Path does not exist: {opencode_path}")
            sys.exit(1)
    else:
        opencode_path = find_opencode_storage()
        if not opencode_path:
            print("Error: Could not find OpenCode storage directory.")
            print("Please provide --opencode-path or ensure OpenCode is installed.")
            sys.exit(1)
    
    # Set global for message lookup
    global opencode_base_path
    opencode_base_path = opencode_path
    
    print(f"\nOpenCode storage: {opencode_path}")
    
    if args.dry_run:
        # Just count files
        session_files = find_session_files(opencode_path)
        sessions = [f for f in session_files if is_session_file(f, {})]
        print(f"Would import {len(sessions)} sessions")
        
        # Count messages
        total_messages = 0
        for sess_file in sessions[:5]:  # Sample first 5
            try:
                data = read_json_file(sess_file)
                msgs = find_message_files(opencode_path, data.get('id', ''))
                total_messages += len(msgs)
            except:
                pass
        print(f"Sample: ~{total_messages} messages found")
        return
    
    # Import
    print("\nImporting sessions...")
    stats = import_sessions(opencode_path)
    
    # Print summary
    print("\n" + "="*50)
    print("Import complete!")
    print(f"  Sessions imported: {stats['sessions_imported']}")
    print(f"  Messages imported: {stats['messages_imported']}")
    print(f"  Embeddings created: {stats['embeddings_created']}")
    
    if stats['errors']:
        print(f"\nErrors ({len(stats['errors'])}):")
        for err in stats['errors'][:5]:
            print(f"  - {err}")


if __name__ == '__main__':
    main()
