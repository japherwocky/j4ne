"""
Anthropic Provider implementation.

This provider supports Anthropic's Claude models via their API.
"""

import logging
from typing import Dict, List, Any, Optional
from llm_providers.base import LLMProvider

logger = logging.getLogger(__name__)

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic library not available. Install with: pip install anthropic")


class AnthropicProvider(LLMProvider):
    """Anthropic provider implementation."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize the Anthropic provider."""
        super().__init__(name, config)
        self.client: Optional[Any] = None
        self.api_key = config.get('api_key')
        self.model = config.get('model', 'claude-3-sonnet-20240229')
        self.followup_model = config.get('followup_model', 'claude-3-haiku-20240307')
        self.base_url = config.get('base_url')  # Optional custom base URL
    
    def initialize(self) -> bool:
        """Initialize the Anthropic client."""
        if not ANTHROPIC_AVAILABLE:
            logger.error("Anthropic library not available")
            return False
        
        try:
            if not self.validate_config():
                return False
            
            # Initialize client with optional base URL
            client_params = {'api_key': self.api_key}
            if self.base_url:
                client_params['base_url'] = self.base_url
            
            self.client = anthropic.Anthropic(**client_params)
            
            logger.info("Anthropic client initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {str(e)}")
            return False
    
    def validate_config(self) -> bool:
        """Validate the Anthropic configuration."""
        if not self.api_key:
            logger.error("Missing required Anthropic API key")
            return False
        
        return True
    
    def chat_completion(self, messages: List[Dict[str, str]], model: str = None, 
                       max_tokens: int = 3000, tools: List[Dict] = None) -> Dict[str, Any]:
        """Generate a chat completion using Anthropic."""
        if not self.client:
            raise RuntimeError("Anthropic client not initialized")
        
        # Use provided model or default
        model_to_use = model or self.model
        
        # Convert messages to Anthropic format
        anthropic_messages = self._convert_messages_to_anthropic(messages)
        
        # Prepare the request parameters
        params = {
            'model': model_to_use,
            'messages': anthropic_messages,
            'max_tokens': max_tokens
        }
        
        # Add tools if provided (Anthropic has different tool format)
        if tools:
            params['tools'] = self._convert_tools_to_anthropic(tools)
        
        try:
            response = self.client.messages.create(**params)
            
            # Convert response to OpenAI-compatible format
            return self._convert_anthropic_response(response)
            
        except Exception as e:
            logger.error(f"Anthropic chat completion failed: {str(e)}")
            raise
    
    def _convert_messages_to_anthropic(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Convert OpenAI-style messages to Anthropic format."""
        anthropic_messages = []
        
        for message in messages:
            role = message.get('role', 'user')
            content = message.get('content', '')
            
            # Anthropic uses 'user' and 'assistant' roles
            if role == 'system':
                # System messages need to be handled differently in Anthropic
                # For now, we'll prepend them to the first user message
                if anthropic_messages and anthropic_messages[0]['role'] == 'user':
                    anthropic_messages[0]['content'] = f"{content}\n\n{anthropic_messages[0]['content']}"
                else:
                    anthropic_messages.insert(0, {'role': 'user', 'content': content})
            else:
                anthropic_messages.append({'role': role, 'content': content})
        
        return anthropic_messages
    
    def _convert_tools_to_anthropic(self, tools: List[Dict]) -> List[Dict]:
        """Convert OpenAI-style tools to Anthropic format."""
        # This is a simplified conversion - Anthropic's tool format may differ
        anthropic_tools = []
        
        for tool in tools:
            if tool.get('type') == 'function':
                function = tool.get('function', {})
                anthropic_tool = {
                    'name': function.get('name'),
                    'description': function.get('description', ''),
                    'input_schema': function.get('parameters', {})
                }
                anthropic_tools.append(anthropic_tool)
        
        return anthropic_tools
    
    def _convert_anthropic_response(self, response) -> Dict[str, Any]:
        """Convert Anthropic response to OpenAI-compatible format."""
        # Extract content from Anthropic response
        content = ""
        if hasattr(response, 'content') and response.content:
            if isinstance(response.content, list):
                content = response.content[0].text if response.content else ""
            else:
                content = str(response.content)
        
        return {
            'choices': [{
                'message': {
                    'content': content,
                    'role': 'assistant',
                    'tool_calls': None  # TODO: Handle tool calls if supported
                },
                'finish_reason': getattr(response, 'stop_reason', 'stop')
            }],
            'usage': {
                'prompt_tokens': getattr(response.usage, 'input_tokens', 0) if hasattr(response, 'usage') else 0,
                'completion_tokens': getattr(response.usage, 'output_tokens', 0) if hasattr(response, 'usage') else 0,
                'total_tokens': (getattr(response.usage, 'input_tokens', 0) + 
                               getattr(response.usage, 'output_tokens', 0)) if hasattr(response, 'usage') else 0
            },
            'model': getattr(response, 'model', self.model)
        }
    
    def get_available_models(self) -> List[str]:
        """Get available models from Anthropic."""
        # Anthropic doesn't have a models endpoint, so return known models
        return [
            'claude-3-opus-20240229',
            'claude-3-sonnet-20240229',
            'claude-3-haiku-20240307',
            'claude-2.1',
            'claude-2.0',
            'claude-instant-1.2'
        ]
    
    def get_default_model(self) -> str:
        """Get the default model for Anthropic."""
        return self.model
    
    def get_followup_model(self) -> str:
        """Get the followup model for Anthropic."""
        return self.followup_model
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the Anthropic provider."""
        if not ANTHROPIC_AVAILABLE:
            return {
                'status': 'unhealthy',
                'error': 'Anthropic library not installed',
                'provider': self.name
            }
        
        base_health = super().health_check()
        
        if base_health['status'] == 'healthy':
            # Add Anthropic-specific health information
            base_health.update({
                'default_model': self.model,
                'followup_model': self.followup_model,
                'base_url': self.base_url or 'https://api.anthropic.com'
            })
        
        return base_health

