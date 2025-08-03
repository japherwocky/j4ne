"""
Base LLM Provider interface.

This module defines the abstract base class that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize the LLM provider.
        
        Args:
            name: The name of the provider (e.g., 'azure_openai', 'openai', 'anthropic')
            config: Configuration dictionary containing provider-specific settings
        """
        self.name = name
        self.config = config
        self._client = None
        logger.info(f"Initializing {name} provider")
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the provider client and validate configuration.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def chat_completion(self, messages: List[Dict[str, str]], model: str = None, 
                       max_tokens: int = 3000, tools: List[Dict] = None) -> Dict[str, Any]:
        """
        Generate a chat completion using the provider's API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model: Model name to use (provider-specific)
            max_tokens: Maximum tokens in the response
            tools: Optional list of tools/functions available to the model
            
        Returns:
            Dictionary containing the completion response
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """
        Get a list of available models for this provider.
        
        Returns:
            List of model names
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate the provider configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        pass
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the provider.
        
        Returns:
            Dictionary with health status information
        """
        try:
            if not self.validate_config():
                return {
                    'status': 'unhealthy',
                    'error': 'Invalid configuration',
                    'provider': self.name
                }
            
            # Try to get available models as a basic health check
            models = self.get_available_models()
            return {
                'status': 'healthy',
                'provider': self.name,
                'models_available': len(models),
                'models': models[:5]  # Show first 5 models
            }
        except Exception as e:
            logger.error(f"Health check failed for {self.name}: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'provider': self.name
            }
    
    def get_default_model(self) -> str:
        """
        Get the default model for this provider.
        
        Returns:
            Default model name
        """
        models = self.get_available_models()
        return models[0] if models else "unknown"
    
    def get_followup_model(self) -> str:
        """
        Get the default followup model for this provider.
        
        Returns:
            Default followup model name
        """
        # By default, use the same as the main model
        return self.get_default_model()
    
    def __str__(self) -> str:
        """String representation of the provider."""
        return f"{self.name} LLM Provider"
    
    def __repr__(self) -> str:
        """Detailed string representation of the provider."""
        return f"LLMProvider(name='{self.name}', config_keys={list(self.config.keys())})"

