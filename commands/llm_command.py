"""
LLM Provider management commands for j4ne.

This module provides commands for managing LLM providers including listing,
showing current provider, switching providers, and checking provider health.
"""

import logging
from typing import Dict, Any
from commands.handler import command_handler
from llm_providers import provider_registry
from llm_providers.config import ProviderConfig

logger = logging.getLogger(__name__)


def register_llm_commands():
    """Register all LLM provider management commands."""
    
    def llm_command(args: str) -> str:
        """
        Main LLM command handler that routes to subcommands.
        
        Usage:
        /llm list - List available providers
        /llm show - Show current provider and configuration
        /llm set <provider> - Switch to a different provider
        /llm status - Show health status of all providers
        /llm help - Show this help message
        """
        if not args:
            return llm_help_command("")
        
        parts = args.strip().split(maxsplit=1)
        subcommand = parts[0].lower()
        subargs = parts[1] if len(parts) > 1 else ""
        
        if subcommand == "list":
            return llm_list_command(subargs)
        elif subcommand == "show":
            return llm_show_command(subargs)
        elif subcommand == "set":
            return llm_set_command(subargs)
        elif subcommand == "status":
            return llm_status_command(subargs)
        elif subcommand == "help":
            return llm_help_command(subargs)
        else:
            return f"Unknown LLM subcommand: {subcommand}. Use '/llm help' for available commands."
    
    def llm_list_command(args: str) -> str:
        """List all available LLM providers."""
        try:
            config = ProviderConfig()
            available_providers = provider_registry.get_available_providers()
            configured_providers = config.get_available_providers()
            
            if not available_providers and not configured_providers:
                return "No LLM providers available. Please configure at least one provider."
            
            result = "📋 **Available LLM Providers:**\n\n"
            
            # Show registered providers
            if available_providers:
                result += "**Registered Providers:**\n"
                for provider in available_providers:
                    status = "✅ Configured" if provider in configured_providers else "⚠️ Not configured"
                    result += f"  • {provider} - {status}\n"
                result += "\n"
            
            # Show configured providers
            if configured_providers:
                result += "**Configured Providers:**\n"
                current_provider = provider_registry.get_current_provider_name()
                for provider in configured_providers:
                    current_marker = " (current)" if provider == current_provider else ""
                    result += f"  • {provider}{current_marker}\n"
                result += "\n"
            
            result += "Use '/llm show' to see current provider details.\n"
            result += "Use '/llm set <provider>' to switch providers."
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing LLM providers: {str(e)}")
            return f"Error listing providers: {str(e)}"
    
    def llm_show_command(args: str) -> str:
        """Show current LLM provider and configuration."""
        try:
            current_provider = provider_registry.get_current_provider()
            current_name = provider_registry.get_current_provider_name()
            
            if not current_provider:
                return "❌ No LLM provider currently active.\n\nUse '/llm list' to see available providers and '/llm set <provider>' to activate one."
            
            result = f"🤖 **Current LLM Provider: {current_name}**\n\n"
            
            # Get provider health info
            health = current_provider.health_check()
            status_emoji = "✅" if health['status'] == 'healthy' else "❌"
            result += f"**Status:** {status_emoji} {health['status'].title()}\n"
            
            if health['status'] == 'unhealthy' and 'error' in health:
                result += f"**Error:** {health['error']}\n"
            
            # Show models
            result += f"**Default Model:** {current_provider.get_default_model()}\n"
            result += f"**Followup Model:** {current_provider.get_followup_model()}\n"
            
            # Show available models
            try:
                models = current_provider.get_available_models()
                if models:
                    result += f"**Available Models:** {', '.join(models[:5])}"
                    if len(models) > 5:
                        result += f" (and {len(models) - 5} more)"
                    result += "\n"
            except Exception as e:
                result += f"**Available Models:** Error retrieving models: {str(e)}\n"
            
            # Show provider-specific info
            if hasattr(current_provider, 'endpoint'):
                result += f"**Endpoint:** {getattr(current_provider, 'endpoint', 'N/A')}\n"
            
            if hasattr(current_provider, 'api_version'):
                result += f"**API Version:** {getattr(current_provider, 'api_version', 'N/A')}\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error showing LLM provider: {str(e)}")
            return f"Error showing provider: {str(e)}"
    
    def llm_set_command(args: str) -> str:
        """Switch to a different LLM provider."""
        if not args:
            return "❌ Please specify a provider name. Use '/llm list' to see available providers."
        
        provider_name = args.strip().lower()
        
        try:
            config = ProviderConfig()
            available_providers = config.get_available_providers()
            
            if provider_name not in available_providers:
                return f"❌ Provider '{provider_name}' not configured.\n\nAvailable providers: {', '.join(available_providers)}\n\nUse '/llm list' for more details."
            
            # Get provider configuration
            provider_config = config.get_provider_config(provider_name)
            if not provider_config:
                return f"❌ No configuration found for provider '{provider_name}'."
            
            # Ensure providers are registered
            provider_registry._ensure_providers_registered()
            
            # Create and initialize the provider
            provider = provider_registry.create_provider(provider_name, provider_config)
            if not provider:
                return f"❌ Failed to initialize provider '{provider_name}'. Check your configuration."
            
            # Set as current provider
            if provider_registry.set_current_provider(provider_name):
                # Update default in config
                config.set_default_provider(provider_name)
                config.save_config()
                
                return f"✅ Successfully switched to provider: **{provider_name}**\n\nUse '/llm show' to see provider details."
            else:
                return f"❌ Failed to set '{provider_name}' as current provider."
            
        except Exception as e:
            logger.error(f"Error setting LLM provider: {str(e)}")
            return f"Error setting provider: {str(e)}"
    
    def llm_status_command(args: str) -> str:
        """Show health status of all configured providers."""
        try:
            config = ProviderConfig()
            configured_providers = config.get_available_providers()
            
            if not configured_providers:
                return "❌ No LLM providers configured.\n\nPlease configure at least one provider using environment variables or configuration file."
            
            result = "🏥 **LLM Provider Health Status:**\n\n"
            
            # Ensure providers are registered
            provider_registry._ensure_providers_registered()
            
            for provider_name in configured_providers:
                provider_config = config.get_provider_config(provider_name)
                if not provider_config:
                    result += f"❌ **{provider_name}**: No configuration found\n"
                    continue
                
                # Try to create provider for health check
                provider = provider_registry.create_provider(provider_name, provider_config)
                if not provider:
                    result += f"❌ **{provider_name}**: Failed to initialize\n"
                    continue
                
                # Get health status
                health = provider.health_check()
                status_emoji = "✅" if health['status'] == 'healthy' else "❌"
                result += f"{status_emoji} **{provider_name}**: {health['status'].title()}"
                
                if health['status'] == 'unhealthy' and 'error' in health:
                    result += f" - {health['error']}"
                elif health['status'] == 'healthy' and 'models_available' in health:
                    result += f" ({health['models_available']} models available)"
                
                result += "\n"
            
            current_provider = provider_registry.get_current_provider_name()
            if current_provider:
                result += f"\n🎯 **Current Provider:** {current_provider}"
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking LLM provider status: {str(e)}")
            return f"Error checking status: {str(e)}"
    
    def llm_help_command(args: str) -> str:
        """Show help for LLM commands."""
        return """🤖 **LLM Provider Management Commands:**

**/llm list** - List all available and configured providers
**/llm show** - Show current provider and its configuration
**/llm set <provider>** - Switch to a different provider
**/llm status** - Show health status of all configured providers
**/llm help** - Show this help message

**Examples:**
• `/llm list` - See what providers are available
• `/llm show` - Check current provider details
• `/llm set azure_openai` - Switch to Azure OpenAI
• `/llm set openai` - Switch to OpenAI
• `/llm status` - Check if all providers are working

**Supported Providers:**
• **azure_openai** - Azure OpenAI (requires AZURE_OPENAI_* env vars)
• **openai** - OpenAI (requires OPENAI_API_KEY env var)
• **anthropic** - Anthropic Claude (requires ANTHROPIC_API_KEY env var)

Configure providers using environment variables or the config file at `config/llm_providers.json`."""
    
    # Register the main LLM command
    command_handler.register_function(
        "llm",
        llm_command,
        "Manage LLM providers (list, show, set, status)",
        ["ai", "provider"]
    )

