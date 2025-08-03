# Project Setup and Usage Guide

## SYSTEM REQUIREMENTS
- The application can be set up using Python's virtual environment feature, with dependencies listed in `requirements.txt`.

## PYTHON REQUIREMENTS
1. **Set up a Python Virtual Environment**:
   - Ensure you're using Python 3.5 or later.
   - Execute the following commands:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

## GETTING J4NE UP AND RUNNING
**Important:** Ensure that a file named `keys.py` exists in the project root. This file will store credentials for various networks (e.g., Discord, Twitch, etc.).

#### Example `keys.py`:
```python
discord_token = "your-discord-token"
discord_app_id = "your-discord-application-id"
twitch_client_id = "your-twitch-client-id"
twitch_client_secret = "your-twitch-client-secret"
```

## DISCORD CONFIGURATION
1. **Create a Discord Application**:
   - Visit [Discord Developer Portal](https://discord.com/developers/applications).
   - Copy the "Client ID" and "Token" into your `keys.py`.
2. **Generate an Invitation Link**:
   - Run the bot with the `--newbot` option to get an invitation link for your server:
   ```bash
   python j4ne.py --newbot
   ```

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

## STATIC ASSETS
Static files (e.g., GIFs, customized CSS) are stored in the `/static` directory:
- Images for reactions (e.g., `anneLewd4.gif`, `lul.PNG`).
- Libraries such as `moment.2.13.0.min.js`.

## DATABASE MANAGEMENT
1. The bot uses SQLite by default:
   - The database is located in `database.db`.
2. Migrations or updates can be handled via `db.py`.

## PROJECT STRUCTURE
- **`api/`:** REST API handlers.
- **`chatters/`, `commands/`:** Chat functionality.
- **`networks/`, `static/`, `templates/`:** Integrations and assets.
- **`tests/`:** Unit tests.

## RUNNING THE BOT
To start the bot, run:
```bash
python j4ne.py
```

## COMMAND-LINE USAGE
You can execute different modules/features using subcommands:
- **Chat Loop**:
  ```bash
  python j4ne.py chat
  ```
- **Greet**:
  ```bash
  python j4ne.py greet <NAME>
  ```
- **Kanban Board Web App**:
  ```bash
  python j4ne.py web
  ```
  Access the app at `http://localhost:8000/`.