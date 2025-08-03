"""
Configuration management for LLM providers.

This module handles loading, validation, and persistence of provider configurations.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class ProviderConfig:
    """Manages configuration for LLM providers."""
    
    def __init__(self, config_file: str = "config/llm_providers.json"):
        """
        Initialize the provider configuration manager.
        
        Args:
            config_file: Path to the configuration file
        """
        self.config_file = Path(config_file)
        self.config_data: Dict[str, Any] = {}
        self._ensure_config_dir()
        self.load_config()
    
    def _ensure_config_dir(self) -> None:
        """Ensure the configuration directory exists."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
    
    def load_config(self) -> None:
        """Load configuration from file and environment variables."""
        # Load from file if it exists
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    self.config_data = json.load(f)
                logger.info(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                logger.error(f"Failed to load config file: {str(e)}")
                self.config_data = {}
        else:
            self.config_data = {}
        
        # Merge with environment variables
        self._load_from_environment()
    
    def _load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        # Azure OpenAI configuration (legacy compatibility)
        if all(os.getenv(var) for var in ['AZURE_OPENAI_ENDPOINT', 'AZURE_OPENAI_API_MODEL', 'AZURE_OPENAI_API_VERSION']):
            azure_config = {
                'endpoint': os.getenv('AZURE_OPENAI_ENDPOINT'),
                'api_model': os.getenv('AZURE_OPENAI_API_MODEL'),
                'api_version': os.getenv('AZURE_OPENAI_API_VERSION'),
                'model': os.getenv('OPENAI_MODEL', 'gpt-4'),
                'followup_model': os.getenv('OPENAI_FOLLOWUP_MODEL', 'gpt-4.1-mini')
            }
            
            if 'providers' not in self.config_data:
                self.config_data['providers'] = {}
            
            # Only set if not already configured in file
            if 'azure_openai' not in self.config_data['providers']:
                self.config_data['providers']['azure_openai'] = azure_config
                logger.info("Loaded Azure OpenAI configuration from environment")
        
        # OpenAI configuration
        if os.getenv('OPENAI_API_KEY'):
            openai_config = {
                'api_key': os.getenv('OPENAI_API_KEY'),
                'model': os.getenv('OPENAI_MODEL', 'gpt-4'),
                'followup_model': os.getenv('OPENAI_FOLLOWUP_MODEL', 'gpt-4-turbo'),
                'base_url': os.getenv('OPENAI_BASE_URL')  # Optional
            }
            
            if 'providers' not in self.config_data:
                self.config_data['providers'] = {}
            
            if 'openai' not in self.config_data['providers']:
                self.config_data['providers']['openai'] = openai_config
                logger.info("Loaded OpenAI configuration from environment")
        
        # Anthropic configuration
        if os.getenv('ANTHROPIC_API_KEY'):
            anthropic_config = {
                'api_key': os.getenv('ANTHROPIC_API_KEY'),
                'model': os.getenv('ANTHROPIC_MODEL', 'claude-3-sonnet-20240229'),
                'followup_model': os.getenv('ANTHROPIC_FOLLOWUP_MODEL', 'claude-3-haiku-20240307'),
                'base_url': os.getenv('ANTHROPIC_BASE_URL')  # Optional
            }
            
            if 'providers' not in self.config_data:
                self.config_data['providers'] = {}
            
            if 'anthropic' not in self.config_data['providers']:
                self.config_data['providers']['anthropic'] = anthropic_config
                logger.info("Loaded Anthropic configuration from environment")
        
        # Set default provider if not specified
        if 'default_provider' not in self.config_data:
            providers = self.config_data.get('providers', {})
            if 'azure_openai' in providers:
                self.config_data['default_provider'] = 'azure_openai'
            elif 'openai' in providers:
                self.config_data['default_provider'] = 'openai'
            elif 'anthropic' in providers:
                self.config_data['default_provider'] = 'anthropic'
    
    def save_config(self) -> bool:
        """
        Save configuration to file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config_data, f, indent=2)
            logger.info(f"Saved configuration to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save config file: {str(e)}")
            return False
    
    def get_provider_config(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific provider.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Provider configuration dictionary or None if not found
        """
        providers = self.config_data.get('providers', {})
        return providers.get(provider_name)
    
    def set_provider_config(self, provider_name: str, config: Dict[str, Any]) -> None:
        """
        Set configuration for a specific provider.
        
        Args:
            provider_name: Name of the provider
            config: Configuration dictionary
        """
        if 'providers' not in self.config_data:
            self.config_data['providers'] = {}
        
        self.config_data['providers'][provider_name] = config
        logger.info(f"Set configuration for provider: {provider_name}")
    
    def get_available_providers(self) -> List[str]:
        """
        Get list of configured providers.
        
        Returns:
            List of provider names
        """
        return list(self.config_data.get('providers', {}).keys())
    
    def get_default_provider(self) -> Optional[str]:
        """
        Get the default provider name.
        
        Returns:
            Default provider name or None if not set
        """
        return self.config_data.get('default_provider')
    
    def set_default_provider(self, provider_name: str) -> bool:
        """
        Set the default provider.
        
        Args:
            provider_name: Name of the provider to set as default
            
        Returns:
            True if successful, False if provider not configured
        """
        providers = self.config_data.get('providers', {})
        if provider_name not in providers:
            logger.error(f"Cannot set default provider: {provider_name} not configured")
            return False
        
        self.config_data['default_provider'] = provider_name
        logger.info(f"Set default provider to: {provider_name}")
        return True
    
    def validate_provider_config(self, provider_name: str, config: Dict[str, Any]) -> List[str]:
        """
        Validate a provider configuration.
        
        Args:
            provider_name: Name of the provider
            config: Configuration to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if provider_name == 'azure_openai':
            required_fields = ['endpoint', 'api_model', 'api_version']
            for field in required_fields:
                if not config.get(field):
                    errors.append(f"Missing required field: {field}")
        
        elif provider_name == 'openai':
            if not config.get('api_key'):
                errors.append("Missing required field: api_key")
        
        elif provider_name == 'anthropic':
            if not config.get('api_key'):
                errors.append("Missing required field: api_key")
        
        else:
            errors.append(f"Unknown provider: {provider_name}")
        
        return errors
    
    def remove_provider(self, provider_name: str) -> bool:
        """
        Remove a provider configuration.
        
        Args:
            provider_name: Name of the provider to remove
            
        Returns:
            True if removed, False if not found
        """
        providers = self.config_data.get('providers', {})
        if provider_name not in providers:
            return False
        
        del providers[provider_name]
        
        # Update default provider if it was the removed one
        if self.config_data.get('default_provider') == provider_name:
            remaining_providers = list(providers.keys())
            self.config_data['default_provider'] = remaining_providers[0] if remaining_providers else None
        
        logger.info(f"Removed provider configuration: {provider_name}")
        return True
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current configuration.
        
        Returns:
            Configuration summary
        """
        providers = self.config_data.get('providers', {})
        
        summary = {
            'config_file': str(self.config_file),
            'default_provider': self.config_data.get('default_provider'),
            'configured_providers': list(providers.keys()),
            'provider_details': {}
        }
        
        # Add sanitized provider details (without sensitive info)
        for name, config in providers.items():
            sanitized_config = {}
            for key, value in config.items():
                if 'key' in key.lower() or 'secret' in key.lower():
                    sanitized_config[key] = '***' if value else None
                else:
                    sanitized_config[key] = value
            summary['provider_details'][name] = sanitized_config
        
        return summary

