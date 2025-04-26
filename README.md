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
