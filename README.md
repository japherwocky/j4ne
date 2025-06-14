# J4NE - Multi-Platform Chat Bot with Agent Capabilities

J4NE is a versatile chat bot that supports multiple platforms including IRC, Twitch, Discord, and Twitter. It also includes a local agent system that can access software tools and perform various tasks.

## System Requirements

- Python 3.9 or later
- Dependencies listed in `requirements.txt`

## Setup Instructions

### 1. Python Environment Setup

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `keys.py` file in the project root with your API credentials:

```python
# Platform credentials
discord_token = "your-discord-token"
discord_app_id = "your-discord-application-id"
twitch_client_id = "your-twitch-client-id"
twitch_client_secret = "your-twitch-client-secret"

# Optional: Twitter credentials
twitter_appkey = ""
twitter_appsecret = ""
twitter_token = ""
twitter_tokensecret = ""

# Optional: Other API keys
cleverbot_key = ""
```

### 3. First-Time Setup

Initialize the database tables:

```bash
python j4ne.py --mktables
```

## Running the Bot

### Basic Usage

```bash
# Start the bot with default settings
python j4ne.py

# Disable specific networks
python j4ne.py --twitter=False --twitch=False
```

### Discord Setup

1. Create a Discord application at [Discord Developer Portal](https://discord.com/developers/applications)
2. Copy the "Client ID" and "Token" into your `keys.py`
3. Generate an invitation link:
   ```bash
   python j4ne.py --newbot
   ```

## Agent Capabilities

J4NE includes a local agent system that can access various tools:

### 1. Starting the Agent Server

The agent system uses a multiplexer to connect to different tool servers:

```bash
# Start the multiplexer server
python servers/multiplexer.py
```

### 2. Available Tool Servers

- **Filesystem Server**: Provides file system access tools
  ```bash
  python servers/filesystem.py /path/to/directory
  ```

- **SQLite Server**: Provides database query tools
  ```bash
  python servers/localsqlite.py --db-path=./database.db
  ```

### 3. Agent Tools

The agent has access to the following tools:

- **Filesystem Tools**:
  - `fs_list-files`: List files in a directory
  - `fs_read-file`: Read file contents
  - `fs_write-file`: Write to a file
  - `fs_delete-file`: Delete a file or directory

- **Database Tools**:
  - `db_read_query`: Execute SELECT queries
  - `db_write_query`: Execute INSERT/UPDATE/DELETE queries
  - `db_create_table`: Create database tables
  - `db_list_tables`: List all tables
  - `db_describe_table`: Get table schema
  - `db_append_insight`: Add business insights

### 4. OpenAI Diff Tool

The project includes a tool for applying patches to files:

```bash
# Apply a patch from stdin
cat patch.txt | python servers/openaidiff.py
```

## Web Interface

J4NE includes a Kanban board web interface:

```bash
# Start the web server
python j4ne.py web
```

This starts a web server on `http://localhost:8000/` with the following features:

- Main board view: [http://localhost:8000/](http://localhost:8000/)
- API endpoints:
  - `GET /api/kanban` — fetch the board
  - `POST /api/kanban/add` — add a card
  - `POST /api/kanban/move` — move a card
  - `POST /api/kanban/delete` — delete a card

## Project Structure

- **`api/`**: REST API handlers
- **`chatters/` and `commands/`**: Chat functionality and command handlers
- **`networks/`**: Platform integrations (Discord, Twitch, IRC, Twitter)
- **`servers/`**: Agent tool servers
  - `filesystem.py`: File system access tools
  - `localsqlite.py`: Database query tools
  - `multiplexer.py`: Tool server multiplexer
  - `openaidiff.py`: File patching utility
- **`static/` and `templates/`**: Web interface assets
- **`tests/`**: Unit tests

## Command-Line Options

```bash
# Show help
python j4ne.py --help

# Enable verbose logging
python j4ne.py --verbose

# Start the chat loop (default)
python j4ne.py chat

# Start the web server
python j4ne.py web

# Send a greeting
python j4ne.py greet <name>
```

## Development

The project is structured to allow easy extension with new features:

1. Add new commands in the `commands/` directory
2. Add new network integrations in the `networks/` directory
3. Add new agent tools in the `servers/` directory

## Future Work

See [PLAN.md](PLAN.md) for planned features and improvements.

