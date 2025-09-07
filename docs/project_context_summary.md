# Project Context Summary

---

## **Project Overview**
This project appears to be a multi-functional bot called **J4NE** (or some similar name) that integrates with various platforms like Discord and Twitch, while also offering additional services like API handlers and a Kanban board web application.

---

## **Key Components**
1. **System Requirements:**
   - Requires **Python 3.5 or later.**
   - Dependency management is handled via `requirements.txt`.

2. **Core Features:**
   - **Discord Integration:** Provides support for Discord bots using APIs.
   - **Twitch Integration:** Includes handling for streaming network functionality.
   - **Chat Functionality:** Interactive chat capabilities with command-specific handlers.
   - **Web Server:** Hosts a Kanban board and APIs.
   - **Database Management:** Uses SQLite (`database.db`) for persistent storage.

3. **Static and Web Assets:**
   - Static files like CSS, JavaScript, and images are contained in the `/static` directory.
   - Templates for web interfaces are in the `/templates` directory.

4. **Structure Overview:**
   - `/api`: REST API handlers for the system.
   - `/chatters` and `/commands`: Manages chat and command handling functionalities.
   - `/networks`: Handles network-specific integrations like Discord, Twitch, or IRC.
   - `/tools`: Likely contains utility scripts or tools to facilitate the core application.
   - `/tests`: Unit tests for application stability.

---

## **Setup Instructions**
1. **Environment Setup:**
   - Use a virtual environment:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt
     ```

2. **Configuration:**
   - Create a `keys.py` file in the root directory with API credentials for Discord, Twitch, etc.
   - Example:
     ```python
     discord_token = "your-discord-token"
     twitch_client_id = "your-twitch-client-id"
     ```

3. **First-Time Setup:**
   - Initialize database tables:
     ```bash
     python j4ne.py --mktables
     ```

4. **Run the Application:**
   - Start the bot:
     ```bash
     python j4ne.py
     ```
   - Launch the Kanban web server:
     ```bash
     python j4ne.py web
     ```

---

## **Features and Optional Configurations**
1. **Network Toggling:**
   - Enable/disable networks when running the bot:
     ```bash
     python j4ne.py --twitter=False
     ```

2. **Kanban Board Functionality:**
   - Web interface hosted at [http://localhost:8000/](http://localhost:8000/).
   - API endpoints:
     - `GET /api/kanban`: Fetch the board.
     - `POST /api/kanban/add`: Add a new card.
     - `POST /api/kanban/move`: Move a card.
     - `POST /api/kanban/delete`: Remove a card.

---

## **Command-Line Options**
Several commands for various features:
- Default Chat Loop:
  ```bash
  python j4ne.py chat
  ```
- Greeting Log:
  ```bash
  python j4ne.py greet <NAME>
  ```
- Verbose Debugging:
  ```bash
  python j4ne.py --verbose
  ```

---

## **Summary**
The project is a robust, modular bot application with full-stack capabilities for chat handling, API integrations, and additional services like a Kanban board web interface. It includes options for first-time setup, network customization, and command-line functionality.