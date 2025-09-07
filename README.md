# J4NE - AI Chat Bot with Data Visualizations

J4NE is a versatile chat bot with data visualization capabilities that supports multiple platforms including IRC, Twitch, Discord, and Twitter. The bot now supports both Azure OpenAI and Hugging Face models for AI inference.

## SYSTEM REQUIREMENTS
- Python 3.7 or later
- For local Hugging Face inference: CUDA-compatible GPU (recommended) or CPU
- The application uses Python's virtual environment feature with dependencies listed in `requirements.txt`

## QUICK START

### 1. Set up Python Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure AI Inference
Copy the example environment file and configure your preferred AI provider:
```bash
cp .env.example .env
```

Edit `.env` to configure either Hugging Face (recommended) or Azure OpenAI:

#### Option A: Hugging Face (Recommended)
```bash
# For API inference (easier setup)
HF_MODEL_NAME=microsoft/DialoGPT-medium
HF_API_TOKEN=your_hugging_face_token_here
HF_USE_LOCAL=false

# For local inference (requires GPU)
HF_MODEL_NAME=microsoft/DialoGPT-medium
HF_USE_LOCAL=true
HF_DEVICE=auto
```

#### Option B: Azure OpenAI (Legacy)
```bash
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_MODEL=your-deployment-name
AZURE_OPENAI_API_VERSION=2023-12-01-preview
```

### 3. Get Hugging Face Token (if using HF API)
1. Visit [Hugging Face Settings](https://huggingface.co/settings/tokens)
2. Create a new token with read permissions
3. Add it to your `.env` file as `HF_API_TOKEN`

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

## AI MODEL RECOMMENDATIONS

### For Tool Calling and Structured Output
- `mistralai/Mistral-7B-Instruct-v0.1` - Excellent for tool calling
- `codellama/CodeLlama-7b-Instruct-hf` - Good for code-related tasks
- `meta-llama/Llama-2-7b-chat-hf` - Strong instruction following

### For Conversational Chat
- `microsoft/DialoGPT-medium` - Lightweight, good for casual chat
- `microsoft/DialoGPT-large` - Better quality, more resource intensive

### Local vs API Inference
- **API Inference**: Easier setup, no local resources needed, subject to rate limits
- **Local Inference**: Full control, no rate limits, requires GPU memory (4-8GB+ recommended)

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

## TROUBLESHOOTING

### Hugging Face Issues
- **Model not found**: Ensure the model name is correct and publicly available
- **API rate limits**: Get a Hugging Face token or switch to local inference
- **Out of memory**: Use a smaller model or switch to API inference
- **Slow local inference**: Ensure CUDA is available and properly configured

### Environment Issues
- **Import errors**: Ensure all dependencies are installed with `pip install -r requirements.txt`
- **Client initialization fails**: Check your `.env` configuration matches the examples above

### Tool Calling Issues
- **Tools not working**: Some models handle structured output better than others
- **Try switching to**: `mistralai/Mistral-7B-Instruct-v0.1` for better tool calling support
