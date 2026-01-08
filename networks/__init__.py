"""
Network integrations for j4ne chat bot.

This package provides network-specific implementations for various chat platforms
including IRC, Slack, Discord, Twitch, and Twitter.
"""

from .base import NetworkClient, NetworkMessage
from .irc import IRCClient
from .slack import SlackClient

__all__ = ['NetworkClient', 'NetworkMessage', 'IRCClient', 'SlackClient']
