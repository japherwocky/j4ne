# J4NE - AI Chat Bot

A versatile chat bot with data visualizations for IRC, Twitch, Discord, and Twitter. J4NE provides an interactive AI-powered chat experience with support for multiple platforms and rich data visualization capabilities.

## Features

- 🤖 **AI-Powered Chat**: Interactive chat loop with AI responses
- 🌐 **Multi-Platform Support**: IRC, Twitch, Discord, and Twitter integration
- 📊 **Data Visualizations**: Rich data visualization capabilities
- 🖥️ **Web Interface**: Built-in web server with Starlette
- 🎯 **CLI Interface**: Easy-to-use command-line interface with Typer
- ⚙️ **Configurable**: Environment-based configuration

## Installation

Install J4NE from PyPI:

```bash
pip install j4ne
```

## Quick Start

After installation, you can use J4NE in several ways:

### Start Interactive Chat (Default)
```bash
j4ne
# or explicitly
j4ne chat
```

### Start Web Server
```bash
j4ne web
```

### Send a Greeting
```bash
j4ne greet "World"
```

### Get Help
```bash
j4ne --help
```

## Configuration

J4NE uses environment variables for configuration. Create a `.env` file in your working directory or set environment variables:

```bash
# Copy the example configuration
cp .env.example .env
# Edit with your settings
```

Key configuration options:
- IRC server settings
- AI service API keys
- Platform-specific tokens and credentials

## Commands

- `j4ne` or `j4ne chat` - Start interactive chat loop
- `j4ne web` - Start web server on port 8000
- `j4ne greet <name>` - Send a greeting message
- `j4ne --help` - Show help information

All commands support `--verbose` flag for detailed logging.

## Development

For development setup:

```bash
# Clone the repository
git clone https://github.com/japherwocky/j4ne.git
cd j4ne

# Install in development mode
pip install -e .

# Or install dependencies directly
pip install -r requirements.txt
```

## Platform Support

- **IRC**: Full IRC client with configurable servers and channels
- **Twitch**: Twitch chat integration
- **Discord**: Discord bot capabilities
- **Twitter**: Twitter API integration
- **Web**: Built-in web interface

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
