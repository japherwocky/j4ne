"""
Memory system for j4ne - conversation history, rolling context, and semantic search.
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Optional
from pathlib import Path

import peewee
from peewee import *

# Load config
CONTEXT_WINDOW_TOKENS = int(os.getenv("CONTEXT_WINDOW_TOKENS", "4000"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# Database setup
DB_PATH = Path(__file__).parent / "memory.db"

# ============== MODELS ==============

class Conversation(peewee.Model):
    """An active or archived conversation session"""
    user = peewee.CharField(index=True)
    platform = peewee.CharField(default='cli')
    started_at = peewee.DateTimeField(default=datetime.now)
    ended_at = peewee.DateTimeField(null=True)
    context_window = peewee.TextField(null=True)
    
    class Meta:
        database = None
        table_name = 'conversations'


class Message(peewee.Model):
    """Individual messages archived from conversations"""
    conversation = peewee.ForeignKeyField(Conversation, backref='messages')
    role = peewee.CharField()
    content = peewee.TextField()
    timestamp = peewee.DateTimeField(default=datetime.now)
    metadata = peewee.TextField(null=True)
    
    class Meta:
        database = None
        table_name = 'messages'
        indexes = ((('conversation', 'timestamp'), False),)


class Memory(peewee.Model):
    """Facts learned about user or from conversations"""
    key = peewee.CharField(unique=True)
    value = peewee.TextField()
    importance = peewee.IntegerField(default=5)
    source_conversation = peewee.ForeignKeyField(Conversation, null=True)
    created_at = peewee.DateTimeField(default=datetime.now)
    updated_at = peewee.DateTimeField(default=datetime.now)
    
    class Meta:
        database = None
        table_name = 'memories'


class Embedding(peewee.Model):
    """Stored embeddings for semantic search"""
    chunk = peewee.TextField()
    chunk_type = peewee.CharField()
    source_id = peewee.IntegerField()
    vector = peewee.TextField()
    created_at = peewee.DateTimeField(default=datetime.now)
    
    class Meta:
        database = None
        table_name = 'embeddings'


# ============== DATABASE ==============

_db = None

def get_db():
    global _db
    if _db is None:
        _db = peewee.SqliteDatabase(str(DB_PATH))
    return _db

def init_db():
    """Initialize database tables (sync)."""
    db = get_db()
    Conversation._meta.database = db
    Message._meta.database = db
    Memory._meta.database = db
    Embedding._meta.database = db
    db.create_tables([Conversation, Message, Memory, Embedding], safe=True)


# ============== EMBEDDING MODEL ==============

class Embedder:
    """Lazy-loaded sentence transformer for embeddings."""
    
    _instance = None
    _model = None
    
    @classmethod
    def get_model(cls):
        if cls._model is None:
            from sentence_transformers import SentenceTransformer
            cls._model = SentenceTransformer(EMBEDDING_MODEL)
        return cls._model
    
    @classmethod
    def encode(cls, text: str) -> list[float]:
        """Encode text to embedding vector."""
        model = cls.get_model()
        result = model.encode(text)
        return result.tolist()
    
    @classmethod
    def encode_batch(cls, texts: list[str]) -> list[list[float]]:
        """Encode multiple texts."""
        model = cls.get_model()
        results = model.encode(texts)
        return [r.tolist() for r in results]


# ============== CONTEXT WINDOW ==============

class ContextWindow:
    """Manages rolling context window for a conversation."""
    
    def __init__(self, conversation_id: int, max_tokens: int = None):
        self.conversation_id = conversation_id
        self.max_tokens = max_tokens or CONTEXT_WINDOW_TOKENS
        self.messages: list[dict] = []
    
    def add_message(self, role: str, content: str, metadata: dict = None):
        """Add a message to the context window and archive it."""
        msg_dict = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        db = get_db()
        Message.create(
            conversation_id=self.conversation_id,
            role=role,
            content=content,
            metadata=json.dumps(metadata) if metadata else None
        )
        
        self.messages.append(msg_dict)
        self._maybe_truncate()
    
    def _maybe_truncate(self):
        """Truncate if over token limit."""
        total_chars = sum(len(m["content"]) for m in self.messages)
        max_chars = self.max_tokens * 4
        
        if total_chars > max_chars:
            keep_count = int(len(self.messages) * 0.8)
            if keep_count > 0:
                self.messages = self.messages[-keep_count:]
    
    def get_context(self) -> list[dict]:
        """Get current context window as message list."""
        return self.messages
    
    def to_prompt(self) -> str:
        """Format context as prompt string for LLM."""
        parts = []
        for msg in self.messages:
            parts.append(f"{msg['role']}: {msg['content']}")
        return "\n".join(parts)


# ============== MEMORY MANAGEMENT ==============

def store_memory(key: str, value: str, importance: int = 5, 
                conversation_id: int = None) -> Memory:
    """Store or update a memory (sync)."""
    existing = Memory.get_or_none(Memory.key == key)
    if existing:
        existing.value = value
        existing.importance = importance
        existing.updated_at = datetime.now()
        existing.save()
        return existing
    
    return Memory.create(
        key=key,
        value=value,
        importance=importance,
        source_conversation_id=conversation_id
    )


def get_memory(key: str) -> Optional[str]:
    """Retrieve a memory by key."""
    memory = Memory.get_or_none(Memory.key == key)
    return memory.value if memory else None


def get_all_memories() -> list[dict]:
    """Get all memories, sorted by importance."""
    memories = Memory.select().order_by(Memory.importance.desc())
    return [{"key": m.key, "value": m.value, "importance": m.importance} 
            for m in memories]


def inject_memories() -> str:
    """Get important memories formatted for prompt injection."""
    memories = Memory.select().order_by(Memory.importance.desc())
    
    if not memories:
        return ""
    
    important = [m for m in memories if m.importance >= 7]
    if len(important) < 10:
        important = list(memories)[:10]
    
    lines = ["## Known information about you:"]
    for m in important:
        lines.append(f"- {m.key}: {m.value}")
    
    return "\n".join(lines)


# ============== SEMANTIC SEARCH ==============

def embed_and_store_message(message_id: int, content: str):
    """Generate and store embedding for a message."""
    vector = Embedder.encode(content)
    Embedding.create(
        chunk=content,
        chunk_type='message',
        source_id=message_id,
        vector=json.dumps(vector)
    )


def embed_and_store_memory(memory_id: int, key: str, value: str):
    """Generate and store embedding for a memory."""
    text = f"{key}: {value}"
    vector = Embedder.encode(text)
    Embedding.create(
        chunk=text,
        chunk_type='memory',
        source_id=memory_id,
        vector=json.dumps(vector)
    )


def semantic_search(query: str, limit: int = 5, 
                   memory_weight: float = 1.5) -> list[dict]:
    """Search embeddings by semantic similarity."""
    query_vector = Embedder.encode(query)
    
    embeddings = Embedding.select()
    
    results = []
    for emb in embeddings:
        emb_vector = json.loads(emb.vector)
        score = cosine_similarity(query_vector, emb_vector)
        
        if emb.chunk_type == 'memory':
            score *= memory_weight
        
        results.append({
            "type": emb.chunk_type,
            "source_id": emb.source_id,
            "chunk": emb.chunk,
            "score": score
        })
    
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot / (norm_a * norm_b)


# ============== CONVERSATION MANAGEMENT ==============

def start_conversation(user: str, platform: str = "cli") -> Conversation:
    """Start a new conversation."""
    return Conversation.create(user=user, platform=platform)


def end_conversation(conversation_id: int):
    """End a conversation and index its messages."""
    conv = Conversation.get_or_none(Conversation.id == conversation_id)
    if conv:
        conv.ended_at = datetime.now()
        conv.save()
        index_conversation(conversation_id)


def index_conversation(conversation_id: int, limit: int = 20):
    """Index recent messages from a conversation."""
    messages = (Message.select()
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.timestamp.desc())
                .limit(limit))
    
    for msg in messages:
        existing = Embedding.get_or_none(
            (Embedding.chunk_type == 'message') & 
            (Embedding.source_id == msg.id)
        )
        if not existing:
            embed_and_store_message(msg.id, msg.content)
    
    memories = Memory.select().where(
        Memory.source_conversation_id == conversation_id
    )
    for mem in memories:
        existing = Embedding.get_or_none(
            (Embedding.chunk_type == 'memory') & 
            (Embedding.source_id == mem.id)
        )
        if not existing:
            embed_and_store_memory(mem.id, mem.key, mem.value)


def get_recent_messages(conversation_id: int, limit: int = 10) -> list[dict]:
    """Get recent messages from a conversation."""
    messages = (Message.select()
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.timestamp.desc())
                .limit(limit))
    
    return [{
        "role": m.role,
        "content": m.content,
        "timestamp": m.timestamp.isoformat()
    } for m in reversed(list(messages))]


def store_message(conversation_id: int, role: str, content: str, metadata: dict = None):
    """Store a message to the database."""
    if conversation_id:
        Message.create(
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata=json.dumps(metadata) if metadata else None
        )
