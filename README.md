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

Create a `.env` file in the project root with your API credentials. You can use the provided `.env.example` as a template:

```bash
# Copy the example file and edit it with your credentials
cp .env.example .env
```

At minimum, you'll need to set up the following for basic functionality:

```
# Discord credentials (required for Discord integration)
DISCORD_TOKEN=your-discord-bot-token
DISCORD_APP_ID=your-discord-application-id

# Twitch credentials (required for Twitch integration)
TWITCH_NAME=your-twitch-username
TWITCH_TOKEN=your-twitch-oauth-token
TWITCH_KEY=your-twitch-client-id

# Azure OpenAI credentials (required for agent functionality)
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_API_MODEL=deployments/gpt-4.1
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
```

Add any optional arguments as needed (e.g., enabling/disabling networks, setting debug mode).

---

## COMMAND-LINE USAGE

You can launch different modules and features using subcommands:

- **Default / Chat Loop** (start interactive chat):
  ```bash
  python j4ne.py chat
  ```
  Or just:
  ```bash
  python j4ne.py
  ```

- **Greet** (print a styled greeting in the logs):
  ```bash
  python j4ne.py greet <NAME>
  ```

- **Kanban Board Web App** (launch web server):
  ```bash
  python j4ne.py web
  ```
  This starts a web server on `http://localhost:8000/`, hosting the Kanban board interface and API. Static files are served from `/static`. The Kanban board persists data in `kanban.json`.

  - Main board view: [http://localhost:8000/](http://localhost:8000/)
  - API endpoints:
    - `GET /api/kanban` — fetch the board
    - `POST /api/kanban/add` — add a card
    - `POST /api/kanban/move` — move a card
    - `POST /api/kanban/delete` — delete a card

- **Verbose Logging**: Add `--verbose` to any command for debug output.

---

Let me know if you want any further customization or info included! I can write this to README.md if you’re happy with it.