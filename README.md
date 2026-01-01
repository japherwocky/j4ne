# J4NE - Chat Bot with Kanban Board

A modern chat bot with data visualizations and a web-based Kanban board interface.

## Features

- **Interactive Chat Interface**: CLI-based chat with MCP (Model Context Protocol) integration
- **Kanban Board**: Web-based task management interface
- **OpenAI Integration**: Powered by OpenAI for intelligent responses
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

2. **Configure API Keys** (optional):
   - Copy and edit `keys.py` to add your OpenAI API key if needed
   - The file contains examples for other integrations

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

### 3. Web Interface (Kanban Board)
Start the web server with Kanban board:
```bash
python j4ne.py web
```
Then visit: http://localhost:8000

The Kanban board allows you to:
- Create, move, and delete task cards
- Organize tasks in To Do, Doing, and Done columns
- Persist data automatically

## Project Structure

- **`j4ne.py`**: Main entry point with CLI and web server
- **`api/`**: REST API handlers for the Kanban board
- **`chatters/`**: Chat functionality and CLI interface
- **`commands/`**: Command handlers and processing
- **`tools/`**: MCP tools integration and direct client
- **`static/`**: Web assets for the Kanban board interface
- **`tests/`**: Unit tests

## Development

The application uses:
- **Starlette**: Modern async web framework
- **Uvicorn**: ASGI server for web interface
- **MCP**: Model Context Protocol for tool integration
- **OpenAI**: AI-powered chat responses
- **Rich**: Beautiful terminal output

## Database

The application uses SQLite for data persistence:
- Kanban board data is stored in `kanban.json`
- Other data may use `database.db` (created automatically)

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

