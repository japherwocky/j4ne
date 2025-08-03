"""
LLM Provider Registry.

This module manages the registration, discovery, and instantiation of LLM providers.
"""

import os
import logging
from typing import Dict, List, Optional, Type, Any
from llm_providers.base import LLMProvider

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry for managing LLM providers."""
    
    def __init__(self):
        """Initialize the provider registry."""
        self._providers: Dict[str, Type[LLMProvider]] = {}
        self._instances: Dict[str, LLMProvider] = {}
        self._current_provider: Optional[str] = None
        logger.info("Provider registry initialized")
    
    def register_provider(self, name: str, provider_class: Type[LLMProvider]) -> None:
        """
        Register a provider class.
        
        Args:
            name: The name of the provider
            provider_class: The provider class to register
        """
        if not issubclass(provider_class, LLMProvider):
            raise ValueError(f"Provider class must inherit from LLMProvider")
        
        self._providers[name] = provider_class
        logger.info(f"Registered provider: {name}")
    
    def get_available_providers(self) -> List[str]:
        """
        Get a list of available provider names.
        
        Returns:
            List of provider names
        """
        return list(self._providers.keys())
    
    def create_provider(self, name: str, config: Dict[str, Any]) -> Optional[LLMProvider]:
        """
        Create and initialize a provider instance.
        
        Args:
            name: The name of the provider
            config: Configuration dictionary for the provider
            
        Returns:
            Initialized provider instance or None if creation failed
        """
        if name not in self._providers:
            logger.error(f"Unknown provider: {name}")
            return None
        
        try:
            provider_class = self._providers[name]
            provider = provider_class(name, config)
            
            if provider.initialize():
                self._instances[name] = provider
                logger.info(f"Successfully created provider: {name}")
                return provider
            else:
                logger.error(f"Failed to initialize provider: {name}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating provider {name}: {str(e)}")
            return None
    
    def get_provider(self, name: str) -> Optional[LLMProvider]:
        """
        Get a provider instance by name.
        
        Args:
            name: The name of the provider
            
        Returns:
            Provider instance or None if not found
        """
        return self._instances.get(name)
    
    def set_current_provider(self, name: str) -> bool:
        """
        Set the current active provider.
        
        Args:
            name: The name of the provider to set as current
            
        Returns:
            True if successful, False otherwise
        """
        if name not in self._instances:
            logger.error(f"Provider {name} not found in instances")
            return False
        
        self._current_provider = name
        logger.info(f"Set current provider to: {name}")
        return True
    
    def get_current_provider(self) -> Optional[LLMProvider]:
        """
        Get the current active provider.
        
        Returns:
            Current provider instance or None if none set
        """
        if self._current_provider:
            return self._instances.get(self._current_provider)
        return None
    
    def get_current_provider_name(self) -> Optional[str]:
        """
        Get the name of the current active provider.
        
        Returns:
            Current provider name or None if none set
        """
        return self._current_provider
    
    def auto_detect_provider(self) -> Optional[str]:
        """
        Auto-detect the best provider based on available environment variables.
        
        Returns:
            Name of the detected provider or None if none found
        """
        # Check for Azure OpenAI (legacy compatibility)
        if all(os.getenv(var) for var in ['AZURE_OPENAI_ENDPOINT', 'AZURE_OPENAI_API_MODEL', 'AZURE_OPENAI_API_VERSION']):
            logger.info("Auto-detected Azure OpenAI configuration")
            return 'azure_openai'
        
        # Check for OpenAI
        if os.getenv('OPENAI_API_KEY'):
            logger.info("Auto-detected OpenAI configuration")
            return 'openai'
        
        # Check for Anthropic
        if os.getenv('ANTHROPIC_API_KEY'):
            logger.info("Auto-detected Anthropic configuration")
            return 'anthropic'
        
        logger.warning("No provider configuration auto-detected")
        return None
    
    def initialize_auto_provider(self) -> Optional[LLMProvider]:
        """
        Auto-detect and initialize a provider based on environment variables.
        
        Returns:
            Initialized provider instance or None if none could be created
        """
        provider_name = self.auto_detect_provider()
        if not provider_name:
            return None
        
        # Import and register providers if not already done
        self._ensure_providers_registered()
        
        # Create configuration based on detected provider
        config = self._create_auto_config(provider_name)
        if not config:
            return None
        
        provider = self.create_provider(provider_name, config)
        if provider:
            self.set_current_provider(provider_name)
        
        return provider
    
    def _ensure_providers_registered(self) -> None:
        """Ensure all built-in providers are registered."""
        if 'azure_openai' not in self._providers:
            try:
                from llm_providers.azure_openai import AzureOpenAIProvider
                self.register_provider('azure_openai', AzureOpenAIProvider)
            except ImportError:
                logger.warning("Azure OpenAI provider not available")
        
        if 'openai' not in self._providers:
            try:
                from llm_providers.openai import OpenAIProvider
                self.register_provider('openai', OpenAIProvider)
            except ImportError:
                logger.warning("OpenAI provider not available")
        
        if 'anthropic' not in self._providers:
            try:
                from llm_providers.anthropic import AnthropicProvider
                self.register_provider('anthropic', AnthropicProvider)
            except ImportError:
                logger.warning("Anthropic provider not available")
    
    def _create_auto_config(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """
        Create configuration for auto-detected provider.
        
        Args:
            provider_name: Name of the provider to create config for
            
        Returns:
            Configuration dictionary or None if unable to create
        """
        if provider_name == 'azure_openai':
            return {
                'endpoint': os.getenv('AZURE_OPENAI_ENDPOINT'),
                'api_model': os.getenv('AZURE_OPENAI_API_MODEL'),
                'api_version': os.getenv('AZURE_OPENAI_API_VERSION'),
                'model': os.getenv('OPENAI_MODEL', 'gpt-4'),
                'followup_model': os.getenv('OPENAI_FOLLOWUP_MODEL', 'gpt-4.1-mini')
            }
        elif provider_name == 'openai':
            return {
                'api_key': os.getenv('OPENAI_API_KEY'),
                'model': os.getenv('OPENAI_MODEL', 'gpt-4'),
                'followup_model': os.getenv('OPENAI_FOLLOWUP_MODEL', 'gpt-4-turbo')
            }
        elif provider_name == 'anthropic':
            return {
                'api_key': os.getenv('ANTHROPIC_API_KEY'),
                'model': os.getenv('ANTHROPIC_MODEL', 'claude-3-sonnet-20240229'),
                'followup_model': os.getenv('ANTHROPIC_FOLLOWUP_MODEL', 'claude-3-haiku-20240307')
            }
        
        return None
    
    def get_provider_status(self) -> Dict[str, Any]:
        """
        Get status information for all providers.
        
        Returns:
            Dictionary with provider status information
        """
        status = {
            'current_provider': self._current_provider,
            'available_providers': list(self._providers.keys()),
            'initialized_providers': list(self._instances.keys()),
            'provider_health': {}
        }
        
        # Get health status for all initialized providers
        for name, provider in self._instances.items():
            status['provider_health'][name] = provider.health_check()
        
        return status

