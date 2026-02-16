#!/usr/bin/env python3
"""
Test script to validate OpenCode Zen integration.

This script tests the OpenCode Zen connection and basic functionality
without requiring the full j4ne application setup.
"""

import os
import pytest
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_opencode_zen_connection():
    """Test basic OpenCode Zen connection and response"""
    from openai import OpenAI

    # Get API key from environment variables
    api_key = os.getenv("OPENCODE_ZEN_API_KEY")

    if not api_key:
        pytest.skip("OPENCODE_ZEN_API_KEY not set. Skipping OpenCode Zen test.")

    # Set up client
    client = OpenAI(api_key=api_key, base_url="https://opencode.ai/zen/v1")

    # Get model from environment variables
    model = os.getenv("OPENCODE_ZEN_MODEL", "gpt-5.1-codex")

    logger.info(f"Testing OpenCode Zen with model: {model}")

    # Test basic completion
    response = client.chat.completions.create(
        model=model,
        max_tokens=100,
        messages=[
            {
                "role": "user",
                "content": "Hello! Can you write a simple Python function to add two numbers?",
            }
        ],
    )

    assert response.choices and response.choices[0].message
    logger.info("OpenCode Zen connection successful!")


@pytest.mark.asyncio
async def test_direct_client():
    """Test the DirectClient with OpenCode Zen"""
    from tools.direct_client import DirectClient

    api_key = os.getenv("OPENCODE_ZEN_API_KEY")
    if not api_key:
        pytest.skip("OPENCODE_ZEN_API_KEY not set. Skipping DirectClient test.")

    logger.info("Testing DirectClient with OpenCode Zen...")

    # Create client
    client = DirectClient()

    # Test a simple query
    history = [
        {
            "role": "user",
            "content": "Write a simple Python function to calculate factorial",
        }
    ]

    response = await client.process_query(history)

    assert response and len(response.strip()) > 0
    logger.info("DirectClient test successful!")
