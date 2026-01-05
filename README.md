# J4NE - Chat Bot

A modern chat bot with data visualizations for IRC, Twitch, Discord, and Twitter.

## Features

- **Interactive Chat Interface**: CLI-based chat with MCP (Model Context Protocol) integration
- **Multi-Platform Support**: Works with IRC, Twitch, Discord, and Twitter
- **OpenCode Zen Integration**: Powered by OpenCode Zen for intelligent responses with coding-optimized models
- **Modern Architecture**: Built with Starlette web framework and async Python

## Requirements

- Python 3.7 or later
- Dependencies listed in `requirements.txt`

## Installation

1. **Set up a Python Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure API Keys**:
   - Get your OpenCode Zen API key from: https://opencode.ai/auth
   - Copy `.env.example` to `.env` and add your API key:
     ```bash
     cp .env.example .env
     # Edit .env and set OPENCODE_ZEN_API_KEY=your_api_key
     ```
   - Or set environment variable directly: `export OPENCODE_ZEN_API_KEY=your_api_key`

## Usage

J4NE provides three main commands:

### 1. Interactive Chat
Start an interactive chat session:
```bash
python j4ne.py chat
```
or simply:
```bash
python j4ne.py
```

### 2. Quick Greeting
Send a greeting message:
```bash
python j4ne.py greet "Your Name"
```

### 3. Web Interface
Start the web server:
```bash
python j4ne.py web
```
Then visit: http://localhost:8000

The web interface provides a simple endpoint for future web-based features.

## Project Structure

- **`j4ne.py`**: Main entry point with CLI and web server
- **`chatters/`**: Chat functionality and CLI interface
- **`commands/`**: Command handlers and processing
- **`tools/`**: MCP tools integration and direct client
- **`tests/`**: Unit tests

## Development

The application uses:
- **Starlette**: Modern async web framework
- **Uvicorn**: ASGI server for web interface
- **MCP**: Model Context Protocol for tool integration
- **OpenCode Zen**: AI-powered chat responses with coding-optimized models
- **Rich**: Beautiful terminal output

## Database

The application uses SQLite for data persistence:
- Chat data and other information is stored in `database.db` (created automatically)

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
