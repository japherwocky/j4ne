"""
Azure OpenAI Provider implementation.

This provider maintains backward compatibility with the existing Azure OpenAI setup.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from openai import AzureOpenAI
from llm_providers.base import LLMProvider

logger = logging.getLogger(__name__)


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI provider implementation."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize the Azure OpenAI provider."""
        super().__init__(name, config)
        self.client: Optional[AzureOpenAI] = None
        self.endpoint = config.get('endpoint')
        self.api_model = config.get('api_model')
        self.api_version = config.get('api_version')
        self.model = config.get('model', 'gpt-4')
        self.followup_model = config.get('followup_model', 'gpt-4.1-mini')
    
    def initialize(self) -> bool:
        """Initialize the Azure OpenAI client."""
        try:
            if not self.validate_config():
                return False
            
            # Construct the API path like the original implementation
            api_path = self.endpoint + self.api_model
            
            self.client = AzureOpenAI(
                api_version=self.api_version,
                base_url=api_path
            )
            
            logger.info("Azure OpenAI client initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI client: {str(e)}")
            return False
    
    def validate_config(self) -> bool:
        """Validate the Azure OpenAI configuration."""
        required_fields = ['endpoint', 'api_model', 'api_version']
        
        for field in required_fields:
            if not self.config.get(field):
                logger.error(f"Missing required Azure OpenAI config field: {field}")
                return False
        
        return True
    
    def chat_completion(self, messages: List[Dict[str, str]], model: str = None, 
                       max_tokens: int = 3000, tools: List[Dict] = None) -> Dict[str, Any]:
        """Generate a chat completion using Azure OpenAI."""
        if not self.client:
            raise RuntimeError("Azure OpenAI client not initialized")
        
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
            
            # Convert response to dictionary format similar to original implementation
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
            logger.error(f"Azure OpenAI chat completion failed: {str(e)}")
            raise
    
    def get_available_models(self) -> List[str]:
        """Get available models for Azure OpenAI."""
        # Azure OpenAI models are deployment-specific, so we return the configured models
        models = []
        
        if self.model:
            models.append(self.model)
        
        if self.followup_model and self.followup_model != self.model:
            models.append(self.followup_model)
        
        # Add some common Azure OpenAI model names
        common_models = ['gpt-4', 'gpt-4-turbo', 'gpt-4.1-mini', 'gpt-35-turbo']
        for model in common_models:
            if model not in models:
                models.append(model)
        
        return models
    
    def get_default_model(self) -> str:
        """Get the default model for Azure OpenAI."""
        return self.model
    
    def get_followup_model(self) -> str:
        """Get the followup model for Azure OpenAI."""
        return self.followup_model
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the Azure OpenAI provider."""
        base_health = super().health_check()
        
        if base_health['status'] == 'healthy':
            # Add Azure-specific health information
            base_health.update({
                'endpoint': self.endpoint,
                'api_version': self.api_version,
                'default_model': self.model,
                'followup_model': self.followup_model
            })
        
        return base_health
    
    @classmethod
    def from_environment(cls) -> 'AzureOpenAIProvider':
        """
        Create an Azure OpenAI provider from environment variables.
        
        This method provides backward compatibility with the existing setup.
        """
        config = {
            'endpoint': os.getenv('AZURE_OPENAI_ENDPOINT'),
            'api_model': os.getenv('AZURE_OPENAI_API_MODEL'),
            'api_version': os.getenv('AZURE_OPENAI_API_VERSION'),
            'model': os.getenv('OPENAI_MODEL', 'gpt-4'),
            'followup_model': os.getenv('OPENAI_FOLLOWUP_MODEL', 'gpt-4.1-mini')
        }
        
        return cls('azure_openai', config)

