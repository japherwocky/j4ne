#!/usr/bin/env python3
"""
Live tests of the OpenCode connection, through the same settings and client
the bot uses. Skipped unless J4NE_LIVE_TESTS=1 (see conftest.py), because
each one is a real, billed API call.
"""

import os
import uuid
import pytest
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.live


def require_key():
    if not os.getenv("OPENCODE_ZEN_API_KEY"):
        pytest.skip("OPENCODE_ZEN_API_KEY not set. Skipping OpenCode test.")


@pytest.mark.asyncio
async def test_opencode_zen_connection():
    """The configured endpoint answers a request carrying j4ne's headers"""
    require_key()
    from tools.direct_client import opencode_settings, make_llm_client

    settings = opencode_settings()
    client = make_llm_client(settings["api_key"], settings["base_url"])
    logger.info(f"Testing {settings['plan_name']} with model: {settings['default_model']}")

    try:
        response = await client.chat.completions.create(
            model=settings["default_model"],
            max_tokens=200,
            messages=[{"role": "user", "content": "Reply with just the word: pong"}],
            extra_headers={"x-opencode-session": str(uuid.uuid4())},
        )
    finally:
        await client.close()

    assert response.choices and response.choices[0].message
    logger.info(f"{settings['plan_name']} connection successful!")


@pytest.mark.asyncio
async def test_direct_client():
    """A whole query through DirectClient, which raises if the API refuses it"""
    require_key()
    from tools.direct_client import DirectClient

    client = DirectClient(context="slack")
    try:
        response = await client.process_query(
            [{"role": "user", "content": "Write a simple Python function to calculate factorial"}]
        )
    finally:
        await client.cleanup()

    assert response and len(response.strip()) > 0
    logger.info("DirectClient test successful!")
