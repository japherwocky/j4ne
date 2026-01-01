#!/usr/bin/env python3
"""
⚠️  DEPRECATED: This configuration file is no longer used! ⚠️

J4NE has moved to a modern environment variable-based configuration.
This file is kept for backward compatibility but is no longer read by the application.

🔧 MIGRATION INSTRUCTIONS:
1. Copy .env.example to .env:
   cp .env.example .env

2. Edit .env and set your API key:
   OPENCODE_ZEN_API_KEY=your_api_key_here

3. Get your API key from: https://opencode.ai/auth

4. Optional: Set custom models:
   OPENCODE_ZEN_MODEL=gpt-5.1-codex
   OPENCODE_ZEN_FOLLOWUP_MODEL=gpt-5.1-codex-mini

For more information, see the README.md file.
"""

# ⚠️ DEPRECATED - These variables are no longer used
# Use environment variables instead (see instructions above)
opencode_zen_api_key = ''
opencode_zen_model = 'gpt-5.1-codex'

# Add other API keys as needed for future integrations
# Example:
# discord_token = 'your-discord-token'
# twitch_client_id = 'your-twitch-client-id'
