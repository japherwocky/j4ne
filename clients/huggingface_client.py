"""
Hugging Face Client Implementation

This module provides a HuggingFaceClient that mimics the OpenAI client interface
but uses Hugging Face models for inference instead of Azure OpenAI.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
    from huggingface_hub import InferenceClient
    import torch
except ImportError as e:
    raise ImportError(f"Missing required dependencies: {e}. Please install with: pip install transformers torch huggingface_hub")

from .tool_calling import ToolCallHandler

logger = logging.getLogger(__name__)

@dataclass
class ChatCompletionChoice:
    """Mimics OpenAI's ChatCompletionChoice structure"""
    message: Dict[str, Any]
    finish_reason: str
    index: int = 0

@dataclass
class ChatCompletion:
    """Mimics OpenAI's ChatCompletion structure"""
    choices: List[ChatCompletionChoice]
    model: str
    id: str = "hf-completion"
    object: str = "chat.completion"

class ChatCompletions:
    """Mimics OpenAI's chat.completions interface"""
    
    def __init__(self, client):
        self.client = client
    
    def create(self, model: str, messages: List[Dict[str, str]], 
               max_tokens: int = 1000, tools: Optional[List[Dict]] = None, **kwargs) -> ChatCompletion:
        """Create a chat completion using Hugging Face models"""
        return self.client._create_completion(model, messages, max_tokens, tools, **kwargs)

class HuggingFaceClient:
    """
    Hugging Face client that mimics the OpenAI client interface.
    
    Supports both local inference and Hugging Face Inference API.
    """
    
    def __init__(self, model_name: Optional[str] = None, api_token: Optional[str] = None, 
                 use_local: bool = False, device: Optional[str] = None):
        """
        Initialize the Hugging Face client.
        
        Args:
            model_name: Name of the Hugging Face model to use
            api_token: Hugging Face API token (for Inference API)
            use_local: Whether to use local inference instead of API
            device: Device to use for local inference ('cuda', 'cpu', 'auto')
        """
        self.model_name = model_name or os.getenv('HF_MODEL_NAME', 'microsoft/DialoGPT-medium')
        self.api_token = api_token or os.getenv('HF_API_TOKEN')
        self.use_local = use_local or os.getenv('HF_USE_LOCAL', 'false').lower() == 'true'
        self.device = device or os.getenv('HF_DEVICE', 'auto')
        
        # Initialize the chat completions interface
        self.chat = ChatCompletions(self)
        
        # Initialize tool calling handler
        self.tool_handler = ToolCallHandler()
        
        # Initialize the appropriate inference method
        if self.use_local:
            self._init_local_model()
        else:
            self._init_api_client()
        
        logger.info(f"HuggingFace client initialized with model: {self.model_name}, local: {self.use_local}")
    
    def _init_local_model(self):
        """Initialize local model for inference"""
        try:
            logger.info(f"Loading local model: {self.model_name}")
            
            # Determine device
            if self.device == 'auto':
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
            else:
                device = self.device
            
            # Load tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if device == 'cuda' else torch.float32,
                device_map='auto' if device == 'cuda' else None
            )
            
            # Create pipeline
            self.pipeline = pipeline(
                'text-generation',
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if device == 'cuda' else -1,
                torch_dtype=torch.float16 if device == 'cuda' else torch.float32
            )
            
            logger.info(f"Local model loaded successfully on {device}")
            
        except Exception as e:
            logger.error(f"Failed to load local model: {e}")
            raise
    
    def _init_api_client(self):
        """Initialize Hugging Face Inference API client"""
        try:
            if not self.api_token:
                logger.warning("No HF_API_TOKEN provided, using public inference API (may have rate limits)")
            
            self.inference_client = InferenceClient(
                model=self.model_name,
                token=self.api_token
            )
            
            logger.info("Hugging Face Inference API client initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Inference API client: {e}")
            raise
    
    def _create_completion(self, model: str, messages: List[Dict[str, str]], 
                          max_tokens: int = 1000, tools: Optional[List[Dict]] = None, **kwargs) -> ChatCompletion:
        """Create a chat completion"""
        try:
            # Convert messages to prompt
            prompt = self._messages_to_prompt(messages, tools)
            
            # Generate response
            if self.use_local:
                response_text = self._generate_local(prompt, max_tokens)
            else:
                response_text = self._generate_api(prompt, max_tokens)
            
            # Handle tool calls if tools are provided
            if tools:
                return self._handle_tool_response(response_text, tools)
            else:
                return self._create_simple_response(response_text)
                
        except Exception as e:
            logger.error(f"Error creating completion: {e}")
            # Return error response in OpenAI format
            return ChatCompletion(
                choices=[ChatCompletionChoice(
                    message={"role": "assistant", "content": f"Error: {str(e)}"},
                    finish_reason="stop"
                )],
                model=model
            )
    
    def _messages_to_prompt(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> str:
        """Convert OpenAI-style messages to a prompt string"""
        prompt_parts = []
        
        # Add system message if present
        system_msg = next((msg for msg in messages if msg['role'] == 'system'), None)
        if system_msg:
            prompt_parts.append(f"System: {system_msg['content']}")
        
        # Add conversation history
        for msg in messages:
            if msg['role'] == 'user':
                prompt_parts.append(f"Human: {msg['content']}")
            elif msg['role'] == 'assistant':
                prompt_parts.append(f"Assistant: {msg['content']}")
        
        # Add tool information if tools are provided
        if tools:
            tool_prompt = self.tool_handler.create_tool_prompt(tools)
            prompt_parts.append(tool_prompt)
        
        prompt_parts.append("Assistant:")
        return "\n\n".join(prompt_parts)
    
    def _generate_local(self, prompt: str, max_tokens: int) -> str:
        """Generate response using local model"""
        try:
            # Generate response
            outputs = self.pipeline(
                prompt,
                max_new_tokens=max_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            # Extract generated text (remove the input prompt)
            generated_text = outputs[0]['generated_text']
            response = generated_text[len(prompt):].strip()
            
            return response
            
        except Exception as e:
            logger.error(f"Error in local generation: {e}")
            raise
    
    def _generate_api(self, prompt: str, max_tokens: int) -> str:
        """Generate response using Hugging Face Inference API"""
        try:
            # Use text generation
            response = self.inference_client.text_generation(
                prompt,
                max_new_tokens=max_tokens,
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
                return_full_text=False
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error in API generation: {e}")
            raise
    
    def _handle_tool_response(self, response_text: str, tools: List[Dict]) -> ChatCompletion:
        """Handle response that might contain tool calls"""
        try:
            # Check if the response contains a tool call
            tool_call = self.tool_handler.parse_tool_call(response_text)
            
            if tool_call:
                # Create tool call response
                message = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tool_call]
                }
                finish_reason = "tool_calls"
            else:
                # Regular response
                message = {
                    "role": "assistant",
                    "content": response_text
                }
                finish_reason = "stop"
            
            return ChatCompletion(
                choices=[ChatCompletionChoice(
                    message=message,
                    finish_reason=finish_reason
                )],
                model=self.model_name
            )
            
        except Exception as e:
            logger.error(f"Error handling tool response: {e}")
            # Fallback to simple response
            return self._create_simple_response(response_text)
    
    def _create_simple_response(self, response_text: str) -> ChatCompletion:
        """Create a simple chat completion response"""
        return ChatCompletion(
            choices=[ChatCompletionChoice(
                message={
                    "role": "assistant",
                    "content": response_text
                },
                finish_reason="stop"
            )],
            model=self.model_name
        )
