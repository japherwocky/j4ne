"""
Proactive Agent Loop - Periodically runs the agent to act proactively.

This module implements the proactive agent pattern where the bot periodically
reads its SOUL.md file and performs tasks proactively based on those directives.
"""

import asyncio
import os
import logging
from typing import Optional
from pathlib import Path

from tools.direct_client import DirectClient

logger = logging.getLogger(__name__)


class ProactiveAgent:
    """Proactive agent that periodically reads SOUL.md and performs tasks."""

    def __init__(self):
        """
        Initialize the proactive agent.
        """
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Configuration from environment
        self.interval = int(os.getenv('PROACTIVE_INTERVAL_SECONDS', '0'))
        self.channel = os.getenv('PROACTIVE_CHANNEL', '#general')
        self.guardian_user = os.getenv('SLACK_GUARDIAN_USER', '')
        self.soul_path = Path(os.getenv('SOUL_PATH', 'SOUL.md'))

        # Determine target: guardian user takes priority for DMs
        self.target = self.guardian_user if self.guardian_user else self.channel

        # Check if proactive mode is enabled
        self.enabled = self.interval > 0

        if not self.enabled:
            logger.info("Proactive agent disabled (PROACTIVE_INTERVAL_SECONDS=0)")
        else:
            target_type = "DM" if self.guardian_user else "channel"
            logger.info(f"Proactive agent enabled: interval={self.interval}s, target={self.target} ({target_type})")

    def _load_soul(self) -> str:
        """
        Load the SOUL.md file contents.

        Returns:
            The contents of SOUL.md, or a default message if not found
        """
        if not self.soul_path.exists():
            logger.warning(f"SOUL.md not found at {self.soul_path}")
            return "No SOUL.md found. Please create a SOUL.md file to define proactive behavior."

        try:
            return self.soul_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Failed to read SOUL.md: {e}")
            return f"Error reading SOUL.md: {e}"

    async def _run_once(self) -> bool:
        """
        Run the proactive agent once.

        Returns:
            True if a message was sent, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Load SOUL.md
            soul_content = self._load_soul()

            # Check if SOUL.md has meaningful content
            if "Replace this with your specific task" in soul_content and "<!--" in soul_content:
                logger.debug("SOUL.md has default template content, skipping run")
                return False

            # Create a fresh DirectClient for this run
            # Use all tools since this is a controlled environment
            client = DirectClient(allowed_tools=None, context="proactive")

            # Build the prompt with default target info
            target_info = f"Default target: {self.target}"
            if self.guardian_user:
                target_info += f" (guardian user ID: {self.guardian_user})"
            if self.channel:
                target_info += f", Default channel: {self.channel}"

            prompt = f"""You are j4ne, running proactively based on your SOUL.md directives.

Your SOUL.md contains the following instructions:

---
{soul_content}
---

{target_info}

Based on these directives, determine if there's anything proactive you should do right now. 

If yes:
1. Do it using your available tools
2. If you want to notify someone, use the slack.send-message tool to send a message
3. If nothing needs to be shared, just respond with "NOACTION" without sending any message

If no:
- Simply respond with "NOACTION" (nothing to do)

Be concise - people don't want walls of text in proactive messages."""

            # Process the query (LLM will decide if/how to message)
            response = await client.process_query([
                {"role": "user", "content": prompt}
            ])

            # Check if we should send a message (LLM decides via tool calls now)
            if response.strip() == "NOACTION":
                logger.debug("Proactive agent had nothing to report")
                return False

            logger.info("Proactive agent run completed")
            return True

        except Exception as e:
            logger.error(f"Error in proactive agent run: {e}")
            return False

    async def _loop(self):
        """Main loop that runs the agent periodically."""
        logger.info(f"Proactive agent loop started (interval: {self.interval}s)")

        # Run once immediately on startup
        await self._run_once()

        while self._running:
            try:
                # Wait for the interval
                await asyncio.sleep(self.interval)

                # Check if still running (might have been stopped during sleep)
                if not self._running:
                    break

                # Run the agent
                await self._run_once()

            except asyncio.CancelledError:
                logger.info("Proactive agent loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in proactive agent loop: {e}")
                # Continue looping despite errors
                await asyncio.sleep(self.interval)

        logger.info("Proactive agent loop stopped")

    def start(self):
        """Start the proactive agent loop."""
        if not self.enabled:
            logger.info("Proactive agent not enabled, skipping start")
            return

        if self._running:
            logger.warning("Proactive agent already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Proactive agent started")

    async def stop(self):
        """Stop the proactive agent loop."""
        if not self._running:
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Proactive agent stopped")

    async def run_once(self) -> bool:
        """
        Manually trigger a single run of the proactive agent.

        Returns:
            True if a message was sent, False otherwise
        """
        return await self._run_once()
