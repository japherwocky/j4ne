#!/usr/bin/env python3
"""
Test script to validate OpenCode Zen integration.

This script tests the OpenCode Zen connection and basic functionality
without requiring the full j4ne application setup.
"""

import os
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_opencode_zen_connection():
    """Test basic OpenCode Zen connection and response"""
    try:
        from openai import OpenAI
        
        # Get API key
        api_key = os.getenv('OPENCODE_ZEN_API_KEY')
        if not api_key:
            try:
                from keys import opencode_zen_api_key
                api_key = opencode_zen_api_key
            except ImportError:
                pass
        
        if not api_key:
            logger.error("No OpenCode Zen API key found. Set OPENCODE_ZEN_API_KEY or update keys.py")
            return False
        
        # Set up client
        client = OpenAI(
            api_key=api_key,
            base_url="https://opencode.ai/zen/v1"
        )
        
        # Get model
        model = os.getenv('OPENCODE_ZEN_MODEL', 'gpt-5.1-codex')
        try:
            from keys import opencode_zen_model
            if opencode_zen_model:
                model = opencode_zen_model
        except ImportError:
            pass
        
        logger.info(f"Testing OpenCode Zen with model: {model}")
        
        # Test basic completion
        response = client.chat.completions.create(
            model=model,
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Hello! Can you write a simple Python function to add two numbers?"}
            ]
        )
        
        if response.choices and response.choices[0].message:
            logger.info("✅ OpenCode Zen connection successful!")
            logger.info(f"Response: {response.choices[0].message.content[:200]}...")
            return True
        else:
            logger.error("❌ No response received from OpenCode Zen")
            return False
            
    except Exception as e:
        logger.error(f"❌ OpenCode Zen connection failed: {str(e)}")
        return False

async def test_direct_client():
    """Test the DirectClient with OpenCode Zen"""
    try:
        logger.info("Testing DirectClient with OpenCode Zen...")
        
        from tools.direct_client import DirectClient
        
        # Create client
        client = DirectClient()
        
        # Test a simple query
        history = [
            {"role": "user", "content": "Write a simple Python function to calculate factorial"}
        ]
        
        response = await client.process_query(history)
        
        if response and len(response.strip()) > 0:
            logger.info("✅ DirectClient test successful!")
            logger.info(f"Response: {response[:200]}...")
            return True
        else:
            logger.error("❌ DirectClient returned empty response")
            return False
            
    except Exception as e:
        logger.error(f"❌ DirectClient test failed: {str(e)}")
        return False

async def main():
    """Run all tests"""
    logger.info("🧪 Starting OpenCode Zen integration tests...")
    
    # Test 1: Basic connection
    logger.info("\n📡 Test 1: Basic OpenCode Zen connection")
    connection_ok = await test_opencode_zen_connection()
    
    # Test 2: DirectClient integration
    logger.info("\n🔧 Test 2: DirectClient integration")
    client_ok = await test_direct_client()
    
    # Summary
    logger.info("\n📊 Test Summary:")
    logger.info(f"  Basic Connection: {'✅ PASS' if connection_ok else '❌ FAIL'}")
    logger.info(f"  DirectClient:     {'✅ PASS' if client_ok else '❌ FAIL'}")
    
    if connection_ok and client_ok:
        logger.info("\n🎉 All tests passed! OpenCode Zen integration is working correctly.")
        return True
    else:
        logger.info("\n⚠️  Some tests failed. Please check your configuration.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
