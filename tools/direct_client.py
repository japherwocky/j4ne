"""Direct Client Implementation - A client that uses the direct tools architecture.

This module provides a client that uses the DirectMultiplexer to call tools directly
as Python functions rather than through subprocess communication.

Tool Access Control:
- Local contexts ("cli", "proactive") get the filesystem, SQLite, git and Slack tools
- Every other context ("slack", "irc") gets PUBLIC_TOOLS only: those providers are
  never even registered for it
- Pass allowed_tools=[...] to restrict tools further
"""

import os
import json
import time
import uuid
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from collections import deque
from typing import List, Dict, Any, Optional, Set

from openai import AsyncOpenAI
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown

from tools.direct_tools import (
    DirectMultiplexer,
    FilesystemToolProvider,
    SQLiteToolProvider,
    GitToolProvider,
    SlackToolProvider,
)
from tools.web_search_tool import WebSearchToolProvider
from tools.github_tool import GitHubToolProvider

# Import memory system
try:
    import memory as memory_module
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    logging.warning("Memory system not available - install dependencies: peewee-async aiosqlite sentence-transformers")

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger('direct_client')

# Agent thought logging - separate log for thinking and tool calls
agent_logger = logging.getLogger('agent_thoughts')
agent_logger.setLevel(logging.DEBUG)
# Create agent log file handler
agent_log_path = os.path.join(os.path.dirname(__file__), '..', 'logs', 'agent_thoughts.log')
os.makedirs(os.path.dirname(agent_log_path), exist_ok=True)
agent_file_handler = RotatingFileHandler(
    agent_log_path, maxBytes=10*1024*1024, backupCount=5  # 10MB, 5 files
)
agent_file_handler.setFormatter(logging.Formatter(
    '%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
agent_logger.addHandler(agent_file_handler)

# Rich console for pretty output
console = Console()

J4NE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---- Tool access ----

# Contexts that run on the owner's own machine. They get every tool,
# including the local ones (filesystem, SQLite, git, slack_send_message).
LOCAL_CONTEXTS = {"cli", "proactive"}

# Every other context (Slack, IRC) gets only these: tools that are safe for
# anyone who can message the bot, because they call public APIs and never
# touch this machine
PUBLIC_TOOLS: Set[str] = {
    "web_search",
    "github_explore_repo",
    "github_search_repos",
    "github_get_file",
}

# ---- LLM settings ----

# Rounds of tool calls one query may make before it has to answer
MAX_TOOL_ROUNDS = int(os.getenv("J4NE_MAX_TOOL_ROUNDS", "10"))

# Completion token limit per call. Reasoning models spend part of it thinking.
MAX_TOKENS = int(os.getenv("OPENCODE_MAX_TOKENS", "3000"))

# The most of one tool result that goes back to the model
MAX_TOOL_RESULT_CHARS = 20000

# OpenCode turns away callers that look anonymous: a generic HTTP-library
# User-Agent or a missing x-opencode-session gets 400 MissingSessionID on Go,
# and Zen words the same rejection as a free-tier lockout. Same fix as
# wolverine's b3857bb. https://opencode.ai/docs/go/#where-can-i-use-it
USER_AGENT = "j4ne/0.1"

ZEN_BASE_URL = "https://opencode.ai/zen/v1"
# Go's documented chat-completions endpoint, for the GLM, Kimi and DeepSeek
# models. Go's docs put MiniMax and Qwen on Anthropic Messages instead; through
# this endpoint minimax-m2.7 is refused and minimax-m3 leaks <think> text.
GO_BASE_URL = "https://opencode.ai/inference/go/openai/v1"
GO_DEFAULT_MODEL = "glm-5.3"

SYSTEM_PROMPTS = {
    "slack": "You are j4ne, a helpful AI assistant. You communicate through Slack and your name is j4ne. When users ask about your identity or name, you should confidently identify yourself as j4ne. You're here to help with various tasks and conversations.",
    "irc": "You are j4ne, a helpful AI assistant. You communicate through IRC and your name is j4ne. When users ask about your identity or name, you should confidently identify yourself as j4ne. Keep replies short: IRC shows each one as a single line.",
    "cli": "You are j4ne, a helpful AI assistant. Your name is j4ne. When users ask about your identity or name, you should confidently identify yourself as j4ne. You're here to help with various tasks and conversations through this command-line interface.",
}


def opencode_settings() -> Dict[str, str]:
    """Which OpenCode endpoint and models to use, from the environment.

    Go is the default: the account is on the Go plan, and Zen's free models
    refuse callers outside OpenCode itself.
    """
    api_key = os.getenv('OPENCODE_ZEN_API_KEY')
    if not api_key:
        raise ValueError(
            "Missing OPENCODE_ZEN_API_KEY environment variable. "
            "Set it using 'export OPENCODE_ZEN_API_KEY=your_key' or add it to your .env file. "
            "Get your API key from: https://opencode.ai/auth"
        )

    use_go = os.getenv('OPENCODE_USE_GO', 'true').lower() == 'true'
    if use_go:
        # The OPENCODE_ZEN_* model settings name the model on either plan, as
        # they always have. OpenCode itself spells Go models opencode-go/<name>;
        # the API wants the bare name.
        default_model = (os.getenv('OPENCODE_ZEN_MODEL') or GO_DEFAULT_MODEL).removeprefix('opencode-go/')
        followup_model = (os.getenv('OPENCODE_ZEN_FOLLOWUP_MODEL') or default_model).removeprefix('opencode-go/')
        return {
            "api_key": api_key,
            "base_url": GO_BASE_URL,
            "default_model": default_model,
            "followup_model": followup_model,
            "plan_name": "OpenCode Go",
        }

    return {
        "api_key": api_key,
        "base_url": ZEN_BASE_URL,
        "default_model": os.getenv('OPENCODE_ZEN_MODEL', 'gpt-5.1-codex'),
        "followup_model": os.getenv('OPENCODE_ZEN_FOLLOWUP_MODEL', 'gpt-5.1-codex-mini'),
        "plan_name": "OpenCode Zen",
    }


def make_llm_client(api_key: str, base_url: str) -> AsyncOpenAI:
    """An OpenAI-compatible client that identifies itself to OpenCode"""
    return AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        default_headers={"User-Agent": USER_AGENT},
    )


def session_id_for(key: str) -> str:
    """A stable x-opencode-session for one conversation (a Slack thread, an
    IRC channel), so OpenCode can route and cache it as one caller"""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"j4ne:{key}"))


class DirectClient:
    """Client that uses the DirectMultiplexer to call tools directly"""

    # Class variable to store the singleton instance
    _instance = None

    @classmethod
    def get_instance(cls):
        """Get the singleton instance of DirectClient"""
        return cls._instance

    def __init__(self, root_path: str = "./", db_path: str = os.path.join(J4NE_DIR, "database.db"),
                 allowed_tools: Optional[Set[str]] = None, context: str = "cli"):
        """Initialize the client with tool providers

        Args:
            root_path: Root path for filesystem tools
            db_path: Path to SQLite database
            allowed_tools: Set of tool names allowed for this client.
                          If None, all tools registered for the context are available.
            context: Where the client is used: "cli", "proactive", "slack" or "irc"
        """
        logger.info(f"Initializing DirectClient (allowed_tools: {allowed_tools}, context: {context})")
        self.context = context

        # The slash commands act on the CLI's client; other contexts must not
        # replace it
        if context == "cli":
            DirectClient._instance = self

        # Anything that is not local is public: never more than PUBLIC_TOOLS
        if context not in LOCAL_CONTEXTS:
            allowed_tools = PUBLIC_TOOLS if allowed_tools is None else set(allowed_tools) & PUBLIC_TOOLS

        # Store allowed tools (None means all tools allowed)
        self.allowed_tools = allowed_tools

        # Initialize history
        self.history = deque(maxlen=8)

        # Session-wide display toggles
        self.show_thinking = False
        self.show_tool_calls = False

        # x-opencode-session for calls that do not name a conversation
        self.session_id = str(uuid.uuid4())

        # Set up the multiplexer with tool providers
        self.multiplexer = DirectMultiplexer()

        if self.context in LOCAL_CONTEXTS:
            # Filesystem, SQLite and git tools touch this machine
            self.multiplexer.add_provider(FilesystemToolProvider(root_path))
            self.multiplexer.add_provider(SQLiteToolProvider(db_path))
            self.multiplexer.add_provider(GitToolProvider(root_path))

            # Posts to Slack as the bot (the proactive agent's voice)
            self.multiplexer.add_provider(SlackToolProvider())

        # Add Web Search tools (public)
        self.multiplexer.add_provider(WebSearchToolProvider())

        # Add GitHub tools (public repos only)
        self.multiplexer.add_provider(GitHubToolProvider())

        # Set up OpenCode client
        self._setup_opencode_client()

        # Initialize memory system
        self.memory_enabled = False
        self.conversation_id = None
        if MEMORY_AVAILABLE:
            try:
                memory_module.init_db()
                self.memory_enabled = True
                logger.info("Memory system initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize memory system: {e}")

        # Log available tools
        all_tools = self.multiplexer.get_available_tools()
        if self.allowed_tools is not None:
            filtered = [t for t in all_tools if t["function"]["name"] in self.allowed_tools]
            logger.info(f"DirectClient initialized with {len(filtered)}/{len(all_tools)} tools (filtered)")
        else:
            logger.info(f"DirectClient initialized with all {len(all_tools)} tools")

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get definitions of available tools, filtered by allowed_tools if set"""
        all_tools = self.multiplexer.get_available_tools()

        if self.allowed_tools is None:
            return all_tools

        # Filter to only allowed tools
        filtered = [t for t in all_tools if t["function"]["name"] in self.allowed_tools]
        logger.debug(f"Filtered tools: {len(filtered)} allowed from {len(all_tools)} total")
        return filtered

    def toggle_thinking(self) -> bool:
        """Toggle session-wide thinking display (raw LLM messages)

        Returns:
            The new state after toggling
        """
        self.show_thinking = not self.show_thinking
        logger.info(f"Thinking display toggled: {'ON' if self.show_thinking else 'OFF'}")
        return self.show_thinking

    def toggle_tools(self) -> bool:
        """Toggle session-wide tool call display (detailed tool execution)

        Returns:
            The new state after toggling
        """
        self.show_tool_calls = not self.show_tool_calls
        logger.info(f"Tool visibility toggled: {'ON' if self.show_tool_calls else 'OFF'}")
        return self.show_tool_calls

    def _setup_opencode_client(self):
        """Set up the OpenCode client using environment variables"""
        try:
            settings = opencode_settings()
            self.client = make_llm_client(settings["api_key"], settings["base_url"])
            self.default_model = settings["default_model"]
            self.followup_model = settings["followup_model"]
            logger.info(f"{settings['plan_name']} client initialized with base URL: {settings['base_url']}, model: {self.default_model}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenCode client: {str(e)}")
            raise

    def _system_prompt(self, memory_context: str) -> Dict[str, str]:
        content = SYSTEM_PROMPTS.get(self.context, SYSTEM_PROMPTS["cli"])
        if memory_context:
            content += f"\n\n{memory_context}"
        return {"role": "system", "content": content}

    async def process_query(self, history: List[Dict[str, str]], session_key: Optional[str] = None) -> str:
        """Process a query using available tools.

        Args:
            history: The conversation so far, as role/content messages
            session_key: Names the conversation (a Slack thread, an IRC
                channel) so its calls share one x-opencode-session

        Raises whatever the API raises; callers decide what the user sees.
        """
        logger.info("Processing query")

        # Inject memories into system prompt
        memory_context = ""
        if self.memory_enabled:
            try:
                memory_context = memory_module.inject_memories()
                logger.debug(f"Injected memory context: {memory_context[:100]}..." if memory_context else "No memories found")
            except Exception as e:
                logger.warning(f"Failed to inject memories: {e}")

        messages = list(history)
        if not messages or messages[0].get("role") != "system":
            messages = [self._system_prompt(memory_context)] + messages

        available_tools = self.get_available_tools()
        logger.debug(f"Available tools: {len(available_tools)}")

        headers = {"x-opencode-session": session_id_for(session_key) if session_key else self.session_id}

        final_response = None
        for round_number in range(MAX_TOOL_ROUNDS + 1):
            request = {
                "model": self.default_model if round_number == 0 else self.followup_model,
                "max_tokens": MAX_TOKENS,
                "messages": messages,
                "extra_headers": headers,
            }
            if available_tools:
                request["tools"] = available_tools

            try:
                response = await self.client.chat.completions.create(**request)
            except Exception as e:
                logger.error(f"Error processing query: {str(e)}")
                raise

            choice = response.choices[0]
            message = choice.message
            tool_calls = message.tool_calls or []

            if message.content:
                agent_logger.info(f"THINKING:\n{message.content}")
                if self.show_thinking:
                    console.print(f"\n[bold magenta]💭 Raw LLM response:[/bold magenta]")
                    console.print(f"[dim]{message.content}[/dim]\n")

            if not tool_calls:
                # Whatever the finish reason, a reply without tool calls is the answer.
                # Sending the same request again would only get the same reply.
                final_response = message.content or ""
                if choice.finish_reason == "length":
                    logger.warning("Response cut off at the token limit")
                    final_response += "\n\n_(cut off at the token limit)_" if final_response else \
                        "_(The model used up its token limit before answering.)_"
                elif choice.finish_reason == "content_filter":
                    logger.warning("Response stopped by the content filter")
                    final_response = final_response or "_(The response was blocked by a content filter.)_"
                break

            if round_number == MAX_TOOL_ROUNDS:
                logger.warning(f"Stopped after {MAX_TOOL_ROUNDS} rounds of tool calls")
                final_response = (message.content or "") + \
                    f"\n\n_(Stopped after {MAX_TOOL_ROUNDS} rounds of tool calls without a final answer.)_"
                break

            # The assistant's turn, tool calls included, as the API returned it.
            # Some reasoning models need their extra fields sent back.
            messages.append(message.model_dump(exclude_none=True))

            agent_logger.info("TOOL_CALLS:")
            for tool_call in tool_calls:
                agent_logger.info(f"  - {tool_call.function.name}: {tool_call.function.arguments}")
            if self.show_thinking:
                console.print(f"\n[bold magenta]💭 LLM requested tool calls:[/bold magenta]")
                for tool_call in tool_calls:
                    console.print(f"[dim]  - {tool_call.function.name}: {tool_call.function.arguments}[/dim]")
                console.print()

            for tool_call in tool_calls:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": await self._run_tool_call(tool_call),
                })

        self._archive(history, final_response)
        return final_response

    async def _run_tool_call(self, tool_call) -> str:
        """Run one tool call and return its result as text for the model"""
        tool_name = tool_call.function.name

        try:
            tool_args = json.loads(tool_call.function.arguments or "{}")
            if not isinstance(tool_args, dict):
                raise ValueError("arguments must be a JSON object")
        except ValueError as e:
            agent_logger.warning(f"Bad arguments for {tool_name}: {tool_call.function.arguments!r}")
            return json.dumps({"error": f"Arguments were not valid JSON ({e}). Call {tool_name} again with valid JSON."})

        logger.info(f"Calling tool: {tool_name} with args: {tool_args}")
        if self.show_tool_calls:
            console.print(f"[bold cyan]🔧 Called tool:[/bold cyan] {tool_name}")
            console.print(f"[bold cyan]📋 Args:[/bold cyan] {json.dumps(tool_args, indent=2)}")

        if self.allowed_tools is not None and tool_name not in self.allowed_tools:
            logger.warning(f"Tool {tool_name} is not allowed, skipping")
            agent_logger.warning(f"Tool {tool_name} is not allowed, skipping")
            return json.dumps({"error": f"Tool {tool_name} is not available here."})

        # Tools block (HTTP, git, SQLite), so they run off the event loop
        start_time = time.time()
        result = await asyncio.to_thread(self.multiplexer.execute_tool, tool_name, tool_args)
        tool_time = time.time() - start_time

        text = json.dumps(result, default=str, ensure_ascii=False)

        if "error" in result:
            agent_logger.info(f"TOOL_RESULT ({tool_name}): ERROR - {result['error']}")
        else:
            agent_logger.info(f"TOOL_RESULT ({tool_name}): {text[:500]}")

        if self.show_tool_calls:
            if "error" in result:
                console.print(f"[bold red]❌ Tool error:[/bold red] {result['error']}")
            else:
                result_summary = json.dumps(result, indent=2, default=str)
                if len(result_summary) > 500:
                    result_summary = result_summary[:500] + "..."
                console.print(f"[bold green]✅ Tool result:[/bold green] {result_summary}")
            console.print(f"[dim]💭 Tool executed in {tool_time:.3f}s[/dim]\n")

        if len(text) > MAX_TOOL_RESULT_CHARS:
            text = text[:MAX_TOOL_RESULT_CHARS] + " ...(truncated)"
        return text

    def _archive(self, history: List[Dict[str, str]], final_response: str) -> None:
        """Archive the last user message and the answer, if memory is on"""
        if not (self.memory_enabled and self.conversation_id):
            return
        try:
            conv_id = self.conversation_id.id if hasattr(self.conversation_id, 'id') else self.conversation_id
            # Archive user message (last user message in history)
            for msg in reversed(history):
                if msg.get('role') == 'user':
                    memory_module.store_message(conv_id, msg['role'], msg['content'])
                    break
            # Archive assistant response
            if final_response:
                memory_module.store_message(conv_id, 'assistant', final_response)
        except Exception as e:
            logger.warning(f"Failed to archive messages: {e}")

    async def chat_loop(self):
        """Run an interactive chat loop"""
        console.print("\nDirect Tool Client Started!")
        console.print("Type your queries or '/quit' to exit.")
        console.print("Type '/help' to see available commands.")

        # Start a new conversation in memory if enabled
        if self.memory_enabled:
            try:
                self.conversation_id = memory_module.start_conversation(
                    user="cli_user",
                    platform="cli"
                )
                logger.info(f"Started conversation {self.conversation_id.id}")
            except Exception as e:
                logger.warning(f"Failed to start conversation: {e}")

        from commands import handle_slash_command

        while True:
            try:
                query = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not query:
                continue

            # Check if this is a command
            if query.startswith('/'):
                result = await handle_slash_command(query)
                if result == "QUIT":
                    break
                if result and result != "__HANDLED__":
                    console.print(result)
                continue
            # Legacy support for 'quit' and 'exit' without slash
            if query.lower() in ('quit', 'exit'):
                break

            self.history.append({'role': 'user', 'content': query})
            console.print('\n')

            try:
                response = await self.process_query(list(self.history))
            except Exception as e:
                # One failed query should not end the session
                logger.error(f"Error in chat loop: {str(e)}")
                self.history.pop()
                console.print(f"[red]Error: {e}[/red]")
                continue

            self.history.append({'role': 'assistant', 'content': response})
            console.print(Markdown("\n" + response))

    async def connect_to_server(self):
        """
        Compatibility method with the old direct client interface.
        In the direct implementation, there's no server to connect to.
        """
        logger.info("Direct client doesn't need to connect to a server")
        # Nothing to do here, as we're not connecting to any server
        pass

    async def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources")

        # Clean up async tool providers that have resources
        for provider in self.multiplexer.providers:
            if hasattr(provider, 'cleanup'):
                try:
                    await provider.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up provider {type(provider).__name__}: {e}")

        try:
            await self.client.close()
        except Exception as e:
            logger.error(f"Error closing the LLM client: {e}")
