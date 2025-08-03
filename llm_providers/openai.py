"""
OpenAI Provider implementation.

This provider supports the standard OpenAI API (non-Azure).
"""

import logging
from typing import Dict, List, Any, Optional
from openai import OpenAI
from llm_providers.base import LLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize the OpenAI provider."""
        super().__init__(name, config)
        self.client: Optional[OpenAI] = None
        self.api_key = config.get('api_key')
        self.model = config.get('model', 'gpt-4')
        self.followup_model = config.get('followup_model', 'gpt-4-turbo')
        self.base_url = config.get('base_url')  # Optional custom base URL
    
    def initialize(self) -> bool:
        """Initialize the OpenAI client."""
        try:
            if not self.validate_config():
                return False
            
            # Initialize client with optional base URL
            client_params = {'api_key': self.api_key}
            if self.base_url:
                client_params['base_url'] = self.base_url
            
            self.client = OpenAI(**client_params)
            
            logger.info("OpenAI client initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            return False
    
    def validate_config(self) -> bool:
        """Validate the OpenAI configuration."""
        if not self.api_key:
            logger.error("Missing required OpenAI API key")
            return False
        
        return True
    
    def chat_completion(self, messages: List[Dict[str, str]], model: str = None, 
                       max_tokens: int = 3000, tools: List[Dict] = None) -> Dict[str, Any]:
        """Generate a chat completion using OpenAI."""
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")
        
        # Use provided model or default
        model_to_use = model or self.model
        
        # Prepare the request parameters
        params = {
            'model': model_to_use,
            'messages': messages,
            'max_tokens': max_tokens
        }
        
        # Add tools if provided
        if tools:
            params['tools'] = tools
        
        try:
            response = self.client.chat.completions.create(**params)
            
            # Convert response to dictionary format
            return {
                'choices': [{
                    'message': {
                        'content': response.choices[0].message.content,
                        'role': response.choices[0].message.role,
                        'tool_calls': getattr(response.choices[0].message, 'tool_calls', None)
                    },
                    'finish_reason': response.choices[0].finish_reason
                }],
                'usage': response.usage.model_dump() if response.usage else None,
                'model': response.model
            }
            
        except Exception as e:
            logger.error(f"OpenAI chat completion failed: {str(e)}")
            raise
    
    def get_available_models(self) -> List[str]:
        """Get available models from OpenAI."""
        if not self.client:
            # Return common models if client not initialized
            return ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo', 'gpt-4o', 'gpt-4o-mini']
        
        try:
            # Get models from API
            models_response = self.client.models.list()
            models = [model.id for model in models_response.data if 'gpt' in model.id.lower()]
            
            # Sort by preference (GPT-4 models first)
            gpt4_models = [m for m in models if 'gpt-4' in m]
            other_models = [m for m in models if 'gpt-4' not in m]
            
            return sorted(gpt4_models) + sorted(other_models)
            
        except Exception as e:
            logger.warning(f"Failed to fetch OpenAI models: {str(e)}")
            # Return fallback list
            return ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo', 'gpt-4o', 'gpt-4o-mini']
    
    def get_default_model(self) -> str:
        """Get the default model for OpenAI."""
        return self.model
    
    def get_followup_model(self) -> str:
        """Get the followup model for OpenAI."""
        return self.followup_model
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the OpenAI provider."""
        base_health = super().health_check()
        
        if base_health['status'] == 'healthy':
            # Add OpenAI-specific health information
            base_health.update({
                'default_model': self.model,
                'followup_model': self.followup_model,
                'base_url': self.base_url or 'https://api.openai.com/v1'
            })
        
        return base_health

