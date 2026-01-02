"""
Base classes for network integrations.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Callable, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class NetworkMessage:
    """Represents a message from a network."""
    network: str
    channel: str
    user: str
    content: str
    timestamp: float
    raw_data: Optional[Any] = None


class NetworkClient(ABC):
    """Base class for network clients."""
    
    def __init__(self, network_name: str):
        self.network_name = network_name
        self.connected = False
        self.message_handlers = []
        self.logger = logging.getLogger(f"{__name__}.{network_name}")
    
    def add_message_handler(self, handler: Callable[[NetworkMessage], None]):
        """Add a message handler function."""
        self.message_handlers.append(handler)
    
    def remove_message_handler(self, handler: Callable[[NetworkMessage], None]):
        """Remove a message handler function."""
        if handler in self.message_handlers:
            self.message_handlers.remove(handler)
    
    async def _dispatch_message(self, message: NetworkMessage):
        """Dispatch a message to all registered handlers."""
        for handler in self.message_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                self.logger.error(f"Error in message handler: {e}")
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the network. Returns True if successful."""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Disconnect from the network."""
        pass
    
    @abstractmethod
    async def send_message(self, channel: str, message: str):
        """Send a message to a channel."""
        pass
    
    @abstractmethod
    async def join_channel(self, channel: str):
        """Join a channel."""
        pass
    
    @abstractmethod
    async def leave_channel(self, channel: str):
        """Leave a channel."""
        pass
