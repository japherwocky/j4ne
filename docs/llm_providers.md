# LLM Provider System Documentation

The j4ne chatbot includes a flexible LLM provider system that supports multiple AI services including Azure OpenAI, OpenAI, and Anthropic Claude. This system allows you to switch between providers at runtime and manage configurations easily.

## Overview

The LLM provider system consists of several components:

- **Provider Registry**: Manages available providers and handles switching
- **Provider Implementations**: Specific implementations for each AI service
- **Configuration Management**: Handles loading and saving provider settings
- **Health Monitoring**: Monitors provider status and availability
- **Command Interface**: User-friendly commands for managing providers

## Supported Providers

### Azure OpenAI
- **Provider Name**: `azure_openai`
- **Description**: Microsoft's Azure OpenAI service
- **Required Environment Variables**:
  - `AZURE_OPENAI_ENDPOINT` - Your Azure OpenAI endpoint URL
  - `AZURE_OPENAI_API_MODEL` - Your deployment name
  - `AZURE_OPENAI_API_VERSION` - API version (e.g., "2024-02-15-preview")
  - `OPENAI_MODEL` - Default model name (optional, defaults to "gpt-4")
  - `OPENAI_FOLLOWUP_MODEL` - Followup model name (optional, defaults to "gpt-4.1-mini")

### OpenAI
- **Provider Name**: `openai`
- **Description**: OpenAI's direct API service
- **Required Environment Variables**:
  - `OPENAI_API_KEY` - Your OpenAI API key
  - `OPENAI_MODEL` - Default model name (optional, defaults to "gpt-4")
  - `OPENAI_FOLLOWUP_MODEL` - Followup model name (optional, defaults to "gpt-4-turbo")
  - `OPENAI_BASE_URL` - Custom base URL (optional)

### Anthropic Claude
- **Provider Name**: `anthropic`
- **Description**: Anthropic's Claude AI models
- **Required Environment Variables**:
  - `ANTHROPIC_API_KEY` - Your Anthropic API key
  - `ANTHROPIC_MODEL` - Default model name (optional, defaults to "claude-3-sonnet-20240229")
  - `ANTHROPIC_FOLLOWUP_MODEL` - Followup model name (optional, defaults to "claude-3-haiku-20240307")
  - `ANTHROPIC_BASE_URL` - Custom base URL (optional)

## Configuration

### Environment Variables (.env file)

Create a `.env` file in your project root with the appropriate variables for your chosen provider(s):

```bash
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_MODEL=your-deployment-name
AZURE_OPENAI_API_VERSION=2024-02-15-preview
OPENAI_MODEL=gpt-4
OPENAI_FOLLOWUP_MODEL=gpt-4.1-mini

# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4
OPENAI_FOLLOWUP_MODEL=gpt-4-turbo

# Anthropic Configuration
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key
ANTHROPIC_MODEL=claude-3-sonnet-20240229
ANTHROPIC_FOLLOWUP_MODEL=claude-3-haiku-20240307
```

### Configuration File

The system also supports a JSON configuration file at `config/llm_providers.json`:

```json
{
  "default_provider": "azure_openai",
  "providers": {
    "azure_openai": {
      "endpoint": "https://your-resource.openai.azure.com/",
      "api_model": "your-deployment-name",
      "api_version": "2024-02-15-preview",
      "model": "gpt-4",
      "followup_model": "gpt-4.1-mini"
    },
    "openai": {
      "api_key": "sk-your-openai-api-key",
      "model": "gpt-4",
      "followup_model": "gpt-4-turbo"
    }
  }
}
```

**Note**: Environment variables take precedence over configuration file settings.

## Commands

The system provides several commands for managing LLM providers:

### `/llm list`
Lists all available and configured providers.

**Example output**:
```
📋 Available LLM Providers:

Registered Providers:
  • azure_openai - ✅ Configured
  • openai - ⚠️ Not configured
  • anthropic - ⚠️ Not configured

Configured Providers:
  • azure_openai (current)

Use '/llm show' to see current provider details.
Use '/llm set <provider>' to switch providers.
```

### `/llm show`
Shows details about the current active provider.

**Example output**:
```
🤖 Current LLM Provider: azure_openai

Status: ✅ Healthy
Default Model: gpt-4
Followup Model: gpt-4.1-mini
Available Models: gpt-4, gpt-4.1-mini, gpt-35-turbo (and 2 more)
Endpoint: https://your-resource.openai.azure.com/
API Version: 2024-02-15-preview
```

### `/llm set <provider>`
Switches to a different provider.

**Examples**:
- `/llm set openai` - Switch to OpenAI
- `/llm set anthropic` - Switch to Anthropic Claude
- `/llm set azure_openai` - Switch to Azure OpenAI

### `/llm status`
Shows health status of all configured providers.

**Example output**:
```
🏥 LLM Provider Health Status:

✅ azure_openai: Healthy (5 models available)
❌ openai: Unhealthy - Invalid API key
⚠️ anthropic: Not configured

🎯 Current Provider: azure_openai
```

### `/llm help`
Shows detailed help for all LLM commands.

## Health Monitoring

The system includes built-in health monitoring that:

- Validates API keys and configurations
- Checks model availability
- Monitors response times
- Tracks provider uptime
- Provides detailed error messages

Health checks are performed:
- When switching providers
- When running `/llm status`
- Automatically in the background (optional)

## Backward Compatibility

The new provider system is fully backward compatible with existing Azure OpenAI configurations. If you have the following environment variables set:

```bash
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_MODEL=...
AZURE_OPENAI_API_VERSION=...
```

The system will automatically detect and use Azure OpenAI as the default provider, maintaining the same behavior as before.

## Troubleshooting

### Common Issues

1. **"No LLM provider available"**
   - Check that you have configured at least one provider with valid credentials
   - Use `/llm list` to see available providers
   - Use `/llm status` to check provider health

2. **"Failed to initialize provider"**
   - Verify your API keys are correct
   - Check that all required environment variables are set
   - Ensure your API endpoints are accessible

3. **"Provider unhealthy"**
   - Check your internet connection
   - Verify API key permissions
   - Check for service outages with the provider

### Debug Mode

Enable debug logging to see detailed provider initialization:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Manual Configuration

You can manually edit the configuration file at `config/llm_providers.json` to add or modify provider settings. The system will automatically reload the configuration.

## Adding New Providers

To add support for a new LLM provider:

1. Create a new provider class inheriting from `LLMProvider`
2. Implement the required abstract methods
3. Register the provider with the registry
4. Add configuration support
5. Update documentation

See the existing provider implementations in `llm_providers/` for examples.

## API Reference

### LLMProvider Base Class

```python
class LLMProvider(ABC):
    def __init__(self, name: str, config: Dict[str, Any])
    def initialize(self) -> bool
    def chat_completion(self, messages: List[Dict], model: str = None, max_tokens: int = 3000, tools: List[Dict] = None) -> Dict[str, Any]
    def get_available_models(self) -> List[str]
    def validate_config(self) -> bool
    def health_check(self) -> Dict[str, Any]
    def get_default_model(self) -> str
    def get_followup_model(self) -> str
```

### ProviderRegistry

```python
class ProviderRegistry:
    def register_provider(self, name: str, provider_class: Type[LLMProvider])
    def get_available_providers(self) -> List[str]
    def create_provider(self, name: str, config: Dict[str, Any]) -> Optional[LLMProvider]
    def set_current_provider(self, name: str) -> bool
    def get_current_provider(self) -> Optional[LLMProvider]
    def auto_detect_provider(self) -> Optional[str]
```

### ProviderConfig

```python
class ProviderConfig:
    def load_config(self)
    def save_config(self) -> bool
    def get_provider_config(self, provider_name: str) -> Optional[Dict[str, Any]]
    def set_provider_config(self, provider_name: str, config: Dict[str, Any])
    def get_default_provider(self) -> Optional[str]
    def set_default_provider(self, provider_name: str) -> bool
```

