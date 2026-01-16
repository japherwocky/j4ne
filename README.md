# J4NE - Chat Bot

A modern chat bot with CLI and web interfaces for IRC and Slack platforms.

## Features

- **CLI Interface**: Interactive command-line chat with rich terminal output
- **Web Interface**: Starlette-based web server for HTTP interactions
- **Multi-Platform Support**: Works with IRC and Slack
- **Modern Architecture**: Built with Starlette web framework and async Python

## Requirements

- Python 3.7 or later
- Dependencies listed in `requirements.txt`

## Installation

1. **Set up a Python Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate
   pip install -r requirements.txt
   ```

## Slack Configuration

To enable Slack integration:

1. **Create a Slack App**:
   - Go to https://api.slack.com/apps and click "Create New App"
   - Choose "From scratch" and give your app a name
   - Select the workspace where you want to install the bot

2. **Configure OAuth Scopes**:
   - Go to "OAuth & Permissions" in your app settings
   - Add the following Bot Token Scopes:
     - `app_mentions:read` - Listen for @mentions
     - `chat:write` - Send messages
     - `channels:history` - Read channel messages
     - `groups:history` - Read private channel messages
     - `im:history` - Read direct messages
     - `mpim:history` - Read group direct messages

3. **Enable Socket Mode** (optional):
   - Go to "Socket Mode" in your app settings
   - Enable Socket Mode and create an App Token
   - Copy the App Token (starts with `xapp-`)

4. **Install the App**:
   - Go to "Install App" and install to your workspace
   - Copy the Bot User OAuth Token (starts with `xoxb-`)

5. **Configure Environment Variables**:
   ```bash
   # Add to your .env file
   SLACK_BOT_TOKEN=xoxb-your-bot-token-here
   SLACK_APP_TOKEN=xapp-your-app-token-here  # Optional: for Socket Mode
   ```

6. **Enable Events**:
   - Go to "Event Subscriptions" in your app settings
   - Enable Events and subscribe to:
     - `app_mention` - When users @mention your bot
     - `message.im` - Direct messages to your bot

## Using Slack Integration

1. **Start the web server** (this starts both IRC and Slack clients):
   ```bash
   python j4ne.py web
   ```

2. **Invite the bot to channels**:
   - In Slack, type `/invite @your-bot-name` in any channel
   - Or add the bot through the channel settings

3. **Chat with the bot**:
   - **In channels**: @mention the bot: `@j4ne-bot Hello!`
   - **Direct messages**: Just send a message directly
   - The bot will respond in threads for better conversation context

## Usage

J4NE provides two main interfaces:

### CLI Interface

The CLI provides interactive chat and quick commands:

1. **Interactive Chat** (default):
   ```bash
   python j4ne.py chat
   ```
   or simply:
   ```bash
   python j4ne.py
   ```

2. **Quick Greeting**:
   ```bash
   python j4ne.py greet "Your Name"
   ```

### Web Interface

Start the web server for platform integrations:
```bash
python j4ne.py web
```

The web server runs on http://localhost:8000 and provides endpoints for Slack integration.

## Project Structure

- **`j4ne.py`**: Main entry point with CLI and web server
- **`chatters/`**: Chat functionality and CLI interface
- **`commands/`**: Command handlers and processing
- **`clients/`**: Client implementations for different platforms
- **`networks/`**: Platform-specific integrations (IRC, Slack)
- **`tools/`**: Tool integrations
- **`tests/`**: Unit tests

## Development

The application uses:
- **Starlette**: Modern async web framework
- **Uvicorn**: ASGI server for web interface
- **Rich**: Beautiful terminal output

## Command Line Options

```bash
python j4ne.py --help          # Show all available commands
python j4ne.py --verbose       # Enable verbose logging
python j4ne.py chat            # Start interactive chat (default)
python j4ne.py greet <name>    # Send greeting
python j4ne.py web             # Start web server
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details