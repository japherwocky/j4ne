"""
Client Factory for creating inference clients

This module provides a factory function that creates the appropriate client
based on environment variables, supporting both Azure OpenAI and Hugging Face.
"""

import os
import logging
from typing import Optional, Union

logger = logging.getLogger(__name__)

def create_client(prefer_huggingface: bool = True) -> Union['AzureOpenAI', 'HuggingFaceClient']:
    """
    Create an inference client based on available environment variables.
    
    Args:
        prefer_huggingface: If True, prefer Hugging Face when both are available
        
    Returns:
        Either an AzureOpenAI client or HuggingFaceClient
        
    Raises:
        ValueError: If no valid configuration is found
    """
    # Check for Hugging Face configuration
    hf_model = os.getenv('HF_MODEL_NAME')
    hf_token = os.getenv('HF_API_TOKEN')
    hf_use_local = os.getenv('HF_USE_LOCAL', 'false').lower() == 'true'
    
    # Check for Azure OpenAI configuration
    azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
    azure_model = os.getenv('AZURE_OPENAI_API_MODEL')
    azure_version = os.getenv('AZURE_OPENAI_API_VERSION')
    
    has_hf_config = bool(hf_model or hf_use_local)
    has_azure_config = bool(azure_endpoint and azure_model and azure_version)
    
    logger.info(f"Available configurations - HF: {has_hf_config}, Azure: {has_azure_config}")
    
    # Decide which client to use
    if prefer_huggingface and has_hf_config:
        logger.info("Using Hugging Face client")
        from .huggingface_client import HuggingFaceClient
        return HuggingFaceClient(
            model_name=hf_model,
            api_token=hf_token,
            use_local=hf_use_local
        )
    elif has_azure_config:
        logger.info("Using Azure OpenAI client")
        from openai import AzureOpenAI
        api_path = azure_endpoint + azure_model
        return AzureOpenAI(
            api_version=azure_version,
            base_url=api_path
        )
    elif has_hf_config:
        logger.info("Using Hugging Face client (fallback)")
        from .huggingface_client import HuggingFaceClient
        return HuggingFaceClient(
            model_name=hf_model,
            api_token=hf_token,
            use_local=hf_use_local
        )
    else:
        error_msg = """
No valid client configuration found. Please set one of:

For Hugging Face:
- HF_MODEL_NAME: Name of the Hugging Face model (e.g., 'microsoft/DialoGPT-medium')
- HF_API_TOKEN: Your Hugging Face API token (optional for public models)
- HF_USE_LOCAL: Set to 'true' for local inference (default: 'false')
- HF_DEVICE: Device for local inference ('cuda', 'cpu', 'auto')

For Azure OpenAI:
- AZURE_OPENAI_ENDPOINT: Your Azure OpenAI endpoint
- AZURE_OPENAI_API_MODEL: Your Azure OpenAI model deployment name
- AZURE_OPENAI_API_VERSION: Azure OpenAI API version
"""
        logger.error(error_msg)
        raise ValueError(error_msg)

def get_client_type() -> str:
    """
    Determine which type of client would be created without actually creating it.
    
    Returns:
        'huggingface' or 'azure' or 'none'
    """
    # Check for Hugging Face configuration
    hf_model = os.getenv('HF_MODEL_NAME')
    hf_use_local = os.getenv('HF_USE_LOCAL', 'false').lower() == 'true'
    
    # Check for Azure OpenAI configuration
    azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
    azure_model = os.getenv('AZURE_OPENAI_API_MODEL')
    azure_version = os.getenv('AZURE_OPENAI_API_VERSION')
    
    has_hf_config = bool(hf_model or hf_use_local)
    has_azure_config = bool(azure_endpoint and azure_model and azure_version)
    
    if has_hf_config:
        return 'huggingface'
    elif has_azure_config:
        return 'azure'
    else:
        return 'none'

def validate_environment() -> dict:
    """
    Validate the current environment configuration.
    
    Returns:
        Dictionary with validation results
    """
    result = {
        'valid': False,
        'client_type': 'none',
        'issues': [],
        'recommendations': []
    }
    
    # Check Hugging Face config
    hf_model = os.getenv('HF_MODEL_NAME')
    hf_token = os.getenv('HF_API_TOKEN')
    hf_use_local = os.getenv('HF_USE_LOCAL', 'false').lower() == 'true'
    
    # Check Azure config
    azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
    azure_model = os.getenv('AZURE_OPENAI_API_MODEL')
    azure_version = os.getenv('AZURE_OPENAI_API_VERSION')
    
    has_hf_config = bool(hf_model or hf_use_local)
    has_azure_config = bool(azure_endpoint and azure_model and azure_version)
    
    if has_hf_config:
        result['valid'] = True
        result['client_type'] = 'huggingface'
        
        if not hf_model and not hf_use_local:
            result['issues'].append("HF_MODEL_NAME not set and HF_USE_LOCAL is false")
        
        if not hf_token and not hf_use_local:
            result['recommendations'].append("Consider setting HF_API_TOKEN for better rate limits")
        
        if hf_use_local:
            result['recommendations'].append("Local inference requires significant GPU memory")
    
    elif has_azure_config:
        result['valid'] = True
        result['client_type'] = 'azure'
        
        if not azure_endpoint:
            result['issues'].append("AZURE_OPENAI_ENDPOINT not set")
        if not azure_model:
            result['issues'].append("AZURE_OPENAI_API_MODEL not set")
        if not azure_version:
            result['issues'].append("AZURE_OPENAI_API_VERSION not set")
    
    else:
        result['issues'].append("No valid client configuration found")
        result['recommendations'].extend([
            "Set HF_MODEL_NAME for Hugging Face inference",
            "Or set Azure OpenAI environment variables for Azure inference"
        ])
    
    return result
