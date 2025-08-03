"""
LLM Provider System for j4ne.

This module provides a flexible system for working with multiple LLM providers
including Azure OpenAI, OpenAI, Anthropic, and others.
"""

from llm_providers.base import LLMProvider
from llm_providers.registry import ProviderRegistry

# Create a global provider registry instance
provider_registry = ProviderRegistry()

__all__ = ['LLMProvider', 'ProviderRegistry', 'provider_registry']

