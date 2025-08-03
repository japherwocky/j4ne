"""
Tests for the LLM provider system.
"""

import os
import json
import pytest
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import the modules to test
from llm_providers.base import LLMProvider
from llm_providers.registry import ProviderRegistry
from llm_providers.config import ProviderConfig
from llm_providers.azure_openai import AzureOpenAIProvider
from llm_providers.openai import OpenAIProvider
from llm_providers.health import ProviderHealthMonitor


class MockProvider(LLMProvider):
    """Mock provider for testing."""
    
    def __init__(self, name: str, config: dict, should_fail: bool = False):
        super().__init__(name, config)
        self.should_fail = should_fail
        self.initialized = False
    
    def initialize(self) -> bool:
        if self.should_fail:
            return False
        self.initialized = True
        return True
    
    def chat_completion(self, messages, model=None, max_tokens=3000, tools=None):
        if not self.initialized:
            raise RuntimeError("Provider not initialized")
        return {
            'choices': [{
                'message': {'content': 'Mock response', 'role': 'assistant'},
                'finish_reason': 'stop'
            }],
            'model': model or 'mock-model'
        }
    
    def get_available_models(self):
        return ['mock-model-1', 'mock-model-2']
    
    def validate_config(self) -> bool:
        return 'api_key' in self.config


class TestLLMProvider:
    """Test the base LLMProvider class."""
    
    def test_provider_initialization(self):
        """Test provider initialization."""
        config = {'api_key': 'test-key'}
        provider = MockProvider('test', config)
        
        assert provider.name == 'test'
        assert provider.config == config
        assert not provider.initialized
    
    def test_provider_health_check(self):
        """Test provider health check."""
        config = {'api_key': 'test-key'}
        provider = MockProvider('test', config)
        provider.initialize()
        
        health = provider.health_check()
        assert health['status'] == 'healthy'
        assert health['provider'] == 'test'
        assert 'models_available' in health
    
    def test_provider_health_check_invalid_config(self):
        """Test health check with invalid config."""
        config = {}  # Missing api_key
        provider = MockProvider('test', config)
        
        health = provider.health_check()
        assert health['status'] == 'unhealthy'
        assert 'Invalid configuration' in health['error']
    
    def test_provider_string_representation(self):
        """Test string representation of provider."""
        config = {'api_key': 'test-key'}
        provider = MockProvider('test', config)
        
        assert str(provider) == 'test LLM Provider'
        assert 'test' in repr(provider)
        assert 'api_key' in repr(provider)


class TestProviderRegistry:
    """Test the ProviderRegistry class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.registry = ProviderRegistry()
    
    def test_register_provider(self):
        """Test provider registration."""
        self.registry.register_provider('mock', MockProvider)
        
        assert 'mock' in self.registry.get_available_providers()
    
    def test_register_invalid_provider(self):
        """Test registering invalid provider class."""
        with pytest.raises(ValueError):
            self.registry.register_provider('invalid', str)
    
    def test_create_provider(self):
        """Test provider creation."""
        self.registry.register_provider('mock', MockProvider)
        config = {'api_key': 'test-key'}
        
        provider = self.registry.create_provider('mock', config)
        
        assert provider is not None
        assert provider.name == 'mock'
        assert provider.initialized
    
    def test_create_provider_failure(self):
        """Test provider creation failure."""
        self.registry.register_provider('mock', MockProvider)
        config = {'api_key': 'test-key'}
        
        # Create a provider that fails to initialize
        with patch.object(MockProvider, '__init__', 
                         lambda self, name, config: super(MockProvider, self).__init__(name, config) or setattr(self, 'should_fail', True)):
            provider = self.registry.create_provider('mock', config)
            assert provider is None
    
    def test_set_current_provider(self):
        """Test setting current provider."""
        self.registry.register_provider('mock', MockProvider)
        config = {'api_key': 'test-key'}
        
        provider = self.registry.create_provider('mock', config)
        assert self.registry.set_current_provider('mock')
        assert self.registry.get_current_provider() == provider
        assert self.registry.get_current_provider_name() == 'mock'
    
    def test_set_nonexistent_provider(self):
        """Test setting nonexistent provider as current."""
        assert not self.registry.set_current_provider('nonexistent')
    
    @patch.dict(os.environ, {
        'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
        'AZURE_OPENAI_API_MODEL': 'test-model',
        'AZURE_OPENAI_API_VERSION': '2024-02-15-preview'
    })
    def test_auto_detect_azure_openai(self):
        """Test auto-detection of Azure OpenAI."""
        detected = self.registry.auto_detect_provider()
        assert detected == 'azure_openai'
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test-key'})
    def test_auto_detect_openai(self):
        """Test auto-detection of OpenAI."""
        detected = self.registry.auto_detect_provider()
        assert detected == 'openai'
    
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'sk-ant-test-key'})
    def test_auto_detect_anthropic(self):
        """Test auto-detection of Anthropic."""
        detected = self.registry.auto_detect_provider()
        assert detected == 'anthropic'
    
    def test_auto_detect_none(self):
        """Test auto-detection with no providers configured."""
        with patch.dict(os.environ, {}, clear=True):
            detected = self.registry.auto_detect_provider()
            assert detected is None


class TestProviderConfig:
    """Test the ProviderConfig class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.json"
        self.config = ProviderConfig(str(self.config_file))
    
    def test_config_initialization(self):
        """Test config initialization."""
        assert self.config.config_file == self.config_file
        assert isinstance(self.config.config_data, dict)
    
    def test_save_and_load_config(self):
        """Test saving and loading configuration."""
        test_data = {
            'default_provider': 'test',
            'providers': {
                'test': {'api_key': 'test-key'}
            }
        }
        
        self.config.config_data = test_data
        assert self.config.save_config()
        
        # Create new config instance to test loading
        new_config = ProviderConfig(str(self.config_file))
        assert new_config.config_data['default_provider'] == 'test'
        assert new_config.config_data['providers']['test']['api_key'] == 'test-key'
    
    def test_provider_config_management(self):
        """Test provider configuration management."""
        provider_config = {'api_key': 'test-key', 'model': 'test-model'}
        
        self.config.set_provider_config('test', provider_config)
        retrieved_config = self.config.get_provider_config('test')
        
        assert retrieved_config == provider_config
        assert 'test' in self.config.get_available_providers()
    
    def test_default_provider_management(self):
        """Test default provider management."""
        # Set up a provider first
        self.config.set_provider_config('test', {'api_key': 'test-key'})
        
        assert self.config.set_default_provider('test')
        assert self.config.get_default_provider() == 'test'
        
        # Test setting nonexistent provider as default
        assert not self.config.set_default_provider('nonexistent')
    
    def test_validate_provider_config(self):
        """Test provider configuration validation."""
        # Valid Azure OpenAI config
        azure_config = {
            'endpoint': 'https://test.openai.azure.com/',
            'api_model': 'test-model',
            'api_version': '2024-02-15-preview'
        }
        errors = self.config.validate_provider_config('azure_openai', azure_config)
        assert len(errors) == 0
        
        # Invalid Azure OpenAI config (missing endpoint)
        invalid_config = {'api_model': 'test-model'}
        errors = self.config.validate_provider_config('azure_openai', invalid_config)
        assert len(errors) > 0
        assert any('endpoint' in error for error in errors)
        
        # Valid OpenAI config
        openai_config = {'api_key': 'sk-test-key'}
        errors = self.config.validate_provider_config('openai', openai_config)
        assert len(errors) == 0
        
        # Invalid OpenAI config (missing api_key)
        invalid_openai_config = {}
        errors = self.config.validate_provider_config('openai', invalid_openai_config)
        assert len(errors) > 0
        assert any('api_key' in error for error in errors)
    
    def test_remove_provider(self):
        """Test removing provider configuration."""
        self.config.set_provider_config('test', {'api_key': 'test-key'})
        self.config.set_default_provider('test')
        
        assert self.config.remove_provider('test')
        assert self.config.get_provider_config('test') is None
        assert self.config.get_default_provider() is None
        
        # Test removing nonexistent provider
        assert not self.config.remove_provider('nonexistent')
    
    @patch.dict(os.environ, {
        'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
        'AZURE_OPENAI_API_MODEL': 'test-model',
        'AZURE_OPENAI_API_VERSION': '2024-02-15-preview'
    })
    def test_load_from_environment(self):
        """Test loading configuration from environment variables."""
        config = ProviderConfig(str(self.config_file))
        
        azure_config = config.get_provider_config('azure_openai')
        assert azure_config is not None
        assert azure_config['endpoint'] == 'https://test.openai.azure.com/'
        assert azure_config['api_model'] == 'test-model'
        assert azure_config['api_version'] == '2024-02-15-preview'
    
    def test_config_summary(self):
        """Test configuration summary."""
        self.config.set_provider_config('test', {'api_key': 'secret-key'})
        self.config.set_default_provider('test')
        
        summary = self.config.get_config_summary()
        
        assert summary['default_provider'] == 'test'
        assert 'test' in summary['configured_providers']
        assert summary['provider_details']['test']['api_key'] == '***'  # Should be sanitized


class TestAzureOpenAIProvider:
    """Test the Azure OpenAI provider."""
    
    def test_provider_initialization(self):
        """Test Azure OpenAI provider initialization."""
        config = {
            'endpoint': 'https://test.openai.azure.com/',
            'api_model': 'test-model',
            'api_version': '2024-02-15-preview'
        }
        
        provider = AzureOpenAIProvider('azure_openai', config)
        
        assert provider.name == 'azure_openai'
        assert provider.endpoint == 'https://test.openai.azure.com/'
        assert provider.api_model == 'test-model'
        assert provider.api_version == '2024-02-15-preview'
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        valid_config = {
            'endpoint': 'https://test.openai.azure.com/',
            'api_model': 'test-model',
            'api_version': '2024-02-15-preview'
        }
        provider = AzureOpenAIProvider('azure_openai', valid_config)
        assert provider.validate_config()
        
        # Invalid config (missing endpoint)
        invalid_config = {
            'api_model': 'test-model',
            'api_version': '2024-02-15-preview'
        }
        provider = AzureOpenAIProvider('azure_openai', invalid_config)
        assert not provider.validate_config()
    
    def test_get_available_models(self):
        """Test getting available models."""
        config = {
            'endpoint': 'https://test.openai.azure.com/',
            'api_model': 'test-model',
            'api_version': '2024-02-15-preview',
            'model': 'gpt-4',
            'followup_model': 'gpt-4-turbo'
        }
        
        provider = AzureOpenAIProvider('azure_openai', config)
        models = provider.get_available_models()
        
        assert 'gpt-4' in models
        assert 'gpt-4-turbo' in models
    
    @patch.dict(os.environ, {
        'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
        'AZURE_OPENAI_API_MODEL': 'test-model',
        'AZURE_OPENAI_API_VERSION': '2024-02-15-preview'
    })
    def test_from_environment(self):
        """Test creating provider from environment variables."""
        provider = AzureOpenAIProvider.from_environment()
        
        assert provider.endpoint == 'https://test.openai.azure.com/'
        assert provider.api_model == 'test-model'
        assert provider.api_version == '2024-02-15-preview'


class TestOpenAIProvider:
    """Test the OpenAI provider."""
    
    def test_provider_initialization(self):
        """Test OpenAI provider initialization."""
        config = {
            'api_key': 'sk-test-key',
            'model': 'gpt-4',
            'followup_model': 'gpt-4-turbo'
        }
        
        provider = OpenAIProvider('openai', config)
        
        assert provider.name == 'openai'
        assert provider.api_key == 'sk-test-key'
        assert provider.model == 'gpt-4'
        assert provider.followup_model == 'gpt-4-turbo'
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        valid_config = {'api_key': 'sk-test-key'}
        provider = OpenAIProvider('openai', valid_config)
        assert provider.validate_config()
        
        # Invalid config (missing api_key)
        invalid_config = {}
        provider = OpenAIProvider('openai', invalid_config)
        assert not provider.validate_config()
    
    def test_get_available_models(self):
        """Test getting available models."""
        config = {'api_key': 'sk-test-key'}
        provider = OpenAIProvider('openai', config)
        
        models = provider.get_available_models()
        
        # Should return fallback models when client not initialized
        assert 'gpt-4' in models
        assert 'gpt-3.5-turbo' in models


class TestProviderHealthMonitor:
    """Test the provider health monitoring system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.registry = ProviderRegistry()
        self.config = ProviderConfig()
        self.monitor = ProviderHealthMonitor(self.registry, self.config)
    
    def test_check_provider_health(self):
        """Test checking individual provider health."""
        config = {'api_key': 'test-key'}
        provider = MockProvider('test', config)
        provider.initialize()
        
        health = self.monitor.check_provider_health(provider)
        
        assert health['status'] == 'healthy'
        assert health['provider_name'] == 'test'
        assert 'timestamp' in health
    
    def test_check_provider_health_error(self):
        """Test health check with provider error."""
        config = {'api_key': 'test-key'}
        provider = MockProvider('test', config, should_fail=True)
        
        health = self.monitor.check_provider_health(provider)
        
        assert health['status'] == 'unhealthy'
        assert 'error' in health
    
    def test_health_history(self):
        """Test health check history tracking."""
        config = {'api_key': 'test-key'}
        provider = MockProvider('test', config)
        provider.initialize()
        
        # Perform multiple health checks
        self.monitor.check_provider_health(provider)
        self.monitor.check_provider_health(provider)
        
        history = self.monitor.get_provider_history('test')
        assert len(history) == 2
        assert all(check['status'] == 'healthy' for check in history)
    
    def test_get_summary_report(self):
        """Test getting summary health report."""
        # Mock some configured providers
        self.config.set_provider_config('test1', {'api_key': 'key1'})
        self.config.set_provider_config('test2', {'api_key': 'key2'})
        
        with patch.object(self.monitor, 'check_all_providers') as mock_check:
            mock_check.return_value = {
                'test1': {'status': 'healthy'},
                'test2': {'status': 'unhealthy'}
            }
            
            summary = self.monitor.get_summary_report()
            
            assert summary['total_providers'] == 2
            assert summary['healthy_providers'] == 1
            assert summary['unhealthy_providers'] == 1
            assert 'timestamp' in summary


if __name__ == '__main__':
    pytest.main([__file__])

