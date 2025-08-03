# Project Setup and Usage Guide

---

## SYSTEM REQUIREMENTS
- The application can be set up using Python's virtual environment feature, with dependencies listed in `requirements.txt`.

---

## PYTHON REQUIREMENTS

1. **Set up a Python Virtual Environment**:
   - Ensure you're using Python 3.5 or later.
   - Execute the following commands:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

---

## GETTING J4NE UP AND RUNNING

**Important:** Ensure that a file named `keys.py` exists in the project root. This file will store the credentials for various networks (e.g., Discord, Twitch, etc.).

#### Example `keys.py`:
```python
discord_token = "your-discord-token"
discord_app_id = "your-discord-application-id"
twitch_client_id = "your-twitch-client-id"
twitch_client_secret = "your-twitch-client-secret"
```

## LLM PROVIDER CONFIGURATION

j4ne supports multiple LLM providers including Azure OpenAI, OpenAI, and Anthropic. Configure your preferred provider using environment variables in a `.env` file:

### Azure OpenAI (Default)
```bash
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_MODEL=your-deployment-name
AZURE_OPENAI_API_VERSION=2024-02-15-preview
OPENAI_MODEL=gpt-4
OPENAI_FOLLOWUP_MODEL=gpt-4.1-mini
```

### OpenAI
```bash
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4
OPENAI_FOLLOWUP_MODEL=gpt-4-turbo
```

### Anthropic Claude
```bash
ANTHROPIC_API_KEY=your-anthropic-api-key
ANTHROPIC_MODEL=claude-3-sonnet-20240229
ANTHROPIC_FOLLOWUP_MODEL=claude-3-haiku-20240307
```

### Managing Providers

Use the built-in commands to manage LLM providers:

- `/llm list` - List available providers
- `/llm show` - Show current provider details
- `/llm set <provider>` - Switch providers (e.g., `/llm set openai`)
- `/llm status` - Check provider health
- `/llm help` - Show detailed help

The system will automatically detect and use the first available provider based on your environment variables.

---

## DISCORD CONFIGURATION

1. **Create a Discord Application**:
   - Visit [Discord Developer Portal](https://discord.com/developers/applications).
   - Copy the "Client ID" and "Token" into your `keys.py`.

2. **Generate an Invitation Link**:
   - Run the bot with the `--newbot` option to get an invitation link for your server:
   ```bash
   python j4ne.py --newbot
   ```

---

## BOT OPTIONS

1. **First-Time Setup**:
   - On your first run, use the following options:
     ```bash
     python j4ne.py --mktables
     ```

2. **Network-Specific Configuration**:
   - To disable a network, pass an argument like `--twitter=False` when launching:
     ```bash
     python j4ne.py --twitter=False
     ```

---

## STATIC ASSETS
Static files (like GIFs, customized CSS, and JavaScript) are stored in the `/static` directory:
- Images for reactions (e.g., `anneLewd4.gif`, `lul.PNG`).
- Web application frontend components (e.g., `charts.js`, `webchat.js`).
- Libraries such as `moment.2.13.0.min.js`.

---

## DATABASE MANAGEMENT

1. The bot uses SQLite by default.
   - The main database is located in `database.db`.

2. Migrations or updates to the database structure can be handled via the `db.py` script.

---

## PROJECT STRUCTURE OVERVIEW

- **`api/`:** REST API handlers.
- **`chatters/` and `commands/`:** Chat functionality and command-specific handlers.
- **`networks/`:** Classes handling network integrations (e.g., Discord, Twitch, IRC).
- **`static/` and `templates/`:** Assets and templates for the bot's web interface.
- **`tests/`:** Unit tests for the project.

---

## RUNNING THE BOT

To start the bot, run:
```bash
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
