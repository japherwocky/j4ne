"""
Network integrations for j4ne chat bot.

This package provides network-specific implementations for various chat platforms
including IRC, Discord, Twitch, and Twitter.
"""

from .base import NetworkClient, NetworkMessage

__all__ = ['NetworkClient', 'NetworkMessage']
