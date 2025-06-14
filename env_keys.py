"""
Environment-based configuration module.
This module loads configuration from .env file and provides it as attributes,
maintaining backward compatibility with the old keys.py approach.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Twitch credentials
twitch_name = os.getenv('TWITCH_NAME', '')
twitch_token = os.getenv('TWITCH_TOKEN', '')
twitch_key = os.getenv('TWITCH_KEY', '')

# Discord credentials
discord_token = os.getenv('DISCORD_TOKEN', 'your-secret-token')
discord_app_id = os.getenv('DISCORD_APP_ID', 'your-discord-client/application-ID')

# Twitter credentials
twitter_appkey = os.getenv('TWITTER_APPKEY', '')
twitter_appsecret = os.getenv('TWITTER_APPSECRET', '')
twitter_token = os.getenv('TWITTER_TOKEN', '')
twitter_tokensecret = os.getenv('TWITTER_TOKENSECRET', '')

# Other API keys
cleverbot_key = os.getenv('CLEVERBOT_KEY', '')

# Square API (if used)
square_appid = os.getenv('SQUARE_APPID', '')
square_token = os.getenv('SQUARE_TOKEN', '')

# Function to check if required keys are set
def check_required_keys(service):
    """
    Check if required keys for a specific service are set.
    Returns True if all required keys are set, False otherwise.
    """
    if service == 'discord':
        return bool(discord_token and discord_app_id)
    elif service == 'twitch':
        return bool(twitch_name and twitch_token and twitch_key)
    elif service == 'twitter':
        return bool(twitter_appkey and twitter_appsecret and twitter_token and twitter_tokensecret)
    elif service == 'square':
        return bool(square_appid and square_token)
    elif service == 'cleverbot':
        return bool(cleverbot_key)
    elif service == 'azure_openai':
        return bool(os.getenv('AZURE_OPENAI_API_KEY') and 
                   os.getenv('AZURE_OPENAI_ENDPOINT') and
                   os.getenv('AZURE_OPENAI_API_VERSION') and
                   os.getenv('AZURE_OPENAI_API_MODEL'))
    return False

