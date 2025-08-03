"""
Tests for the LLM provider management commands.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

# Import the command functions
from commands.llm_command import register_llm_commands
from commands.handler import CommandHandler


class TestLLMCommands:
    """Test the LLM provider management commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.command_handler = CommandHandler()
        
        # Mock the provider registry and config
        self.mock_registry = Mock()
        self.mock_config = Mock()
        
        # Register commands with mocked dependencies
        with patch('commands.llm_command.provider_registry', self.mock_registry), \
             patch('commands.llm_command.ProviderConfig', return_value=self.mock_config):
            register_llm_commands()
    
    def test_llm_command_registration(self):
        """Test that LLM commands are properly registered."""
        # The commands should be registered in the global command_handler
        # For this test, we'll create a fresh handler and register commands
        handler = CommandHandler()
        
        with patch('commands.llm_command.provider_registry', self.mock_registry), \
             patch('commands.llm_command.ProviderConfig', return_value=self.mock_config):
            
            # Import and register the commands
            from commands.llm_command import register_llm_commands
            
            # Temporarily replace the global command_handler
            import commands.llm_command
            original_handler = commands.llm_command.command_handler
            commands.llm_command.command_handler = handler
            
            try:
                register_llm_commands()
                assert 'llm' in handler.commands
                
                # Test aliases
                llm_command = handler.commands['llm']
                assert 'ai' in llm_command.aliases
                assert 'provider' in llm_command.aliases
            finally:
                commands.llm_command.command_handler = original_handler
    
    def test_llm_list_command(self):
        """Test the /llm list command."""
        # Mock the registry and config responses
        self.mock_registry.get_available_providers.return_value = ['azure_openai', 'openai', 'anthropic']
        self.mock_config.get_available_providers.return_value = ['azure_openai']
        self.mock_registry.get_current_provider_name.return_value = 'azure_openai'
        
        # Execute the command
        with patch('commands.llm_command.provider_registry', self.mock_registry), \
             patch('commands.llm_command.ProviderConfig', return_value=self.mock_config):
            
            from commands.llm_command import register_llm_commands
            handler = CommandHandler()
            
            import commands.llm_command
            original_handler = commands.llm_command.command_handler
            commands.llm_command.command_handler = handler
            
            try:
                register_llm_commands()
                result = handler.handle_message('/llm list')
                
                assert 'Available LLM Providers' in result
                assert 'azure_openai' in result
                assert 'Configured' in result
                assert 'Not configured' in result
            finally:
                commands.llm_command.command_handler = original_handler
    
    def test_llm_show_command(self):
        """Test the /llm show command."""
        # Mock current provider
        mock_provider = Mock()
        mock_provider.name = 'azure_openai'
        mock_provider.get_default_model.return_value = 'gpt-4'
        mock_provider.get_followup_model.return_value = 'gpt-4-turbo'
        mock_provider.get_available_models.return_value = ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo']
        mock_provider.health_check.return_value = {'status': 'healthy'}
        mock_provider.endpoint = 'https://test.openai.azure.com/'
        mock_provider.api_version = '2024-02-15-preview'
        
        self.mock_registry.get_current_provider.return_value = mock_provider
        self.mock_registry.get_current_provider_name.return_value = 'azure_openai'
        
        with patch('commands.llm_command.provider_registry', self.mock_registry), \
             patch('commands.llm_command.ProviderConfig', return_value=self.mock_config):
            
            from commands.llm_command import register_llm_commands
            handler = CommandHandler()
            
            import commands.llm_command
            original_handler = commands.llm_command.command_handler
            commands.llm_command.command_handler = handler
            
            try:
                register_llm_commands()
                result = handler.handle_message('/llm show')
                
                assert 'Current LLM Provider: azure_openai' in result
                assert 'Status: ✅ healthy' in result
                assert 'Default Model: gpt-4' in result
                assert 'Followup Model: gpt-4-turbo' in result
                assert 'Available Models:' in result
            finally:
                commands.llm_command.command_handler = original_handler
    
    def test_llm_show_command_no_provider(self):
        """Test the /llm show command with no active provider."""
        self.mock_registry.get_current_provider.return_value = None
        self.mock_registry.get_current_provider_name.return_value = None
        
        with patch('commands.llm_command.provider_registry', self.mock_registry), \
             patch('commands.llm_command.ProviderConfig', return_value=self.mock_config):
            
            from commands.llm_command import register_llm_commands
            handler = CommandHandler()
            
            import commands.llm_command
            original_handler = commands.llm_command.command_handler
            commands.llm_command.command_handler = handler
            
            try:
                register_llm_commands()
                result = handler.handle_message('/llm show')
                
                assert 'No LLM provider currently active' in result
                assert '/llm list' in result
                assert '/llm set' in result
            finally:
                commands.llm_command.command_handler = original_handler
    
    def test_llm_set_command_success(self):
        """Test the /llm set command with successful provider switch."""
        self.mock_config.get_available_providers.return_value = ['azure_openai', 'openai']
        self.mock_config.get_provider_config.return_value = {'api_key': 'test-key'}
        
        mock_provider = Mock()
        self.mock_registry.create_provider.return_value = mock_provider
        self.mock_registry.set_current_provider.return_value = True
        self.mock_registry._ensure_providers_registered = Mock()
        
        self.mock_config.set_default_provider.return_value = True
        self.mock_config.save_config.return_value = True
        
        with patch('commands.llm_command.provider_registry', self.mock_registry), \
             patch('commands.llm_command.ProviderConfig', return_value=self.mock_config):
            
            from commands.llm_command import register_llm_commands
            handler = CommandHandler()
            
            import commands.llm_command
            original_handler = commands.llm_command.command_handler
            commands.llm_command.command_handler = handler
            
            try:
                register_llm_commands()
                result = handler.handle_message('/llm set openai')
                
                assert 'Successfully switched to provider: openai' in result
                self.mock_registry.create_provider.assert_called_once_with('openai', {'api_key': 'test-key'})
                self.mock_registry.set_current_provider.assert_called_once_with('openai')
                self.mock_config.set_default_provider.assert_called_once_with('openai')
                self.mock_config.save_config.assert_called_once()
            finally:
                commands.llm_command.command_handler = original_handler
    
    def test_llm_set_command_invalid_provider(self):
        """Test the /llm set command with invalid provider."""
        self.mock_config.get_available_providers.return_value = ['azure_openai']
        
        with patch('commands.llm_command.provider_registry', self.mock_registry), \
             patch('commands.llm_command.ProviderConfig', return_value=self.mock_config):
            
            from commands.llm_command import register_llm_commands
            handler = CommandHandler()
            
            import commands.llm_command
            original_handler = commands.llm_command.command_handler
            commands.llm_command.command_handler = handler
            
            try:
                register_llm_commands()
                result = handler.handle_message('/llm set nonexistent')
                
                assert 'Provider \'nonexistent\' not configured' in result
                assert 'Available providers: azure_openai' in result
            finally:
                commands.llm_command.command_handler = original_handler
    
    def test_llm_set_command_no_args(self):
        """Test the /llm set command without arguments."""
        with patch('commands.llm_command.provider_registry', self.mock_registry), \
             patch('commands.llm_command.ProviderConfig', return_value=self.mock_config):
            
            from commands.llm_command import register_llm_commands
            handler = CommandHandler()
            
            import commands.llm_command
            original_handler = commands.llm_command.command_handler
            commands.llm_command.command_handler = handler
            
            try:
                register_llm_commands()
                result = handler.handle_message('/llm set')
                
                assert 'Please specify a provider name' in result
                assert '/llm list' in result
            finally:
                commands.llm_command.command_handler = original_handler
    
    def test_llm_status_command(self):
        """Test the /llm status command."""
        self.mock_config.get_available_providers.return_value = ['azure_openai', 'openai']
        self.mock_config.get_provider_config.side_effect = [
            {'endpoint': 'https://test.openai.azure.com/', 'api_key': 'key1'},
            {'api_key': 'key2'}
        ]
        
        # Mock providers
        mock_provider1 = Mock()
        mock_provider1.health_check.return_value = {'status': 'healthy', 'models_available': 5}
        
        mock_provider2 = Mock()
        mock_provider2.health_check.return_value = {'status': 'unhealthy', 'error': 'Invalid API key'}
        
        self.mock_registry.create_provider.side_effect = [mock_provider1, mock_provider2]
        self.mock_registry.get_current_provider_name.return_value = 'azure_openai'
        self.mock_registry._ensure_providers_registered = Mock()
        
        with patch('commands.llm_command.provider_registry', self.mock_registry), \
             patch('commands.llm_command.ProviderConfig', return_value=self.mock_config):
            
            from commands.llm_command import register_llm_commands
            handler = CommandHandler()
            
            import commands.llm_command
            original_handler = commands.llm_command.command_handler
            commands.llm_command.command_handler = handler
            
            try:
                register_llm_commands()
                result = handler.handle_message('/llm status')
                
                assert 'LLM Provider Health Status' in result
                assert '✅ azure_openai: Healthy' in result
                assert '❌ openai: Unhealthy - Invalid API key' in result
                assert 'Current Provider: azure_openai' in result
            finally:
                commands.llm_command.command_handler = original_handler
    
    def test_llm_help_command(self):
        """Test the /llm help command."""
        with patch('commands.llm_command.provider_registry', self.mock_registry), \
             patch('commands.llm_command.ProviderConfig', return_value=self.mock_config):
            
            from commands.llm_command import register_llm_commands
            handler = CommandHandler()
            
            import commands.llm_command
            original_handler = commands.llm_command.command_handler
            commands.llm_command.command_handler = handler
            
            try:
                register_llm_commands()
                result = handler.handle_message('/llm help')
                
                assert 'LLM Provider Management Commands' in result
                assert '/llm list' in result
                assert '/llm show' in result
                assert '/llm set' in result
                assert '/llm status' in result
                assert 'azure_openai' in result
                assert 'openai' in result
                assert 'anthropic' in result
            finally:
                commands.llm_command.command_handler = original_handler
    
    def test_llm_command_no_args(self):
        """Test the /llm command without arguments (should show help)."""
        with patch('commands.llm_command.provider_registry', self.mock_registry), \
             patch('commands.llm_command.ProviderConfig', return_value=self.mock_config):
            
            from commands.llm_command import register_llm_commands
            handler = CommandHandler()
            
            import commands.llm_command
            original_handler = commands.llm_command.command_handler
            commands.llm_command.command_handler = handler
            
            try:
                register_llm_commands()
                result = handler.handle_message('/llm')
                
                # Should return help text
                assert 'LLM Provider Management Commands' in result
            finally:
                commands.llm_command.command_handler = original_handler
    
    def test_llm_command_invalid_subcommand(self):
        """Test the /llm command with invalid subcommand."""
        with patch('commands.llm_command.provider_registry', self.mock_registry), \
             patch('commands.llm_command.ProviderConfig', return_value=self.mock_config):
            
            from commands.llm_command import register_llm_commands
            handler = CommandHandler()
            
            import commands.llm_command
            original_handler = commands.llm_command.command_handler
            commands.llm_command.command_handler = handler
            
            try:
                register_llm_commands()
                result = handler.handle_message('/llm invalid')
                
                assert 'Unknown LLM subcommand: invalid' in result
                assert '/llm help' in result
            finally:
                commands.llm_command.command_handler = original_handler
    
    def test_command_error_handling(self):
        """Test error handling in commands."""
        # Mock an exception in the registry
        self.mock_registry.get_available_providers.side_effect = Exception("Test error")
        
        with patch('commands.llm_command.provider_registry', self.mock_registry), \
             patch('commands.llm_command.ProviderConfig', return_value=self.mock_config):
            
            from commands.llm_command import register_llm_commands
            handler = CommandHandler()
            
            import commands.llm_command
            original_handler = commands.llm_command.command_handler
            commands.llm_command.command_handler = handler
            
            try:
                register_llm_commands()
                result = handler.handle_message('/llm list')
                
                assert 'Error listing providers' in result
                assert 'Test error' in result
            finally:
                commands.llm_command.command_handler = original_handler


if __name__ == '__main__':
    pytest.main([__file__])

