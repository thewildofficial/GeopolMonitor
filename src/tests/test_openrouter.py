#!/usr/bin/env python3
"""
Test script to verify OpenRouter integration in GeopolMonitor.
This script tests the OpenRouter fallback mechanism by:
1. Testing direct OpenRouter client functionality
2. Testing the ContentProcessor's fallback mechanism
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Add the project root to the Python path to allow imports to work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Check for required environment variables
if not os.getenv("OPENROUTER_API_KEY"):
    logger.error("OPENROUTER_API_KEY environment variable is not set. Please set it in your .env file.")
    sys.exit(1)

# Import after environment variables are loaded
from src.utils.openrouter_client import openrouter_client
from src.utils.ai import content_processor
from config.settings import OPENROUTER_ENABLED, OPENROUTER_API_KEY

async def test_openrouter_direct():
    """Test OpenRouter client directly."""
    logger.info("Testing OpenRouter client directly...")
    
    try:
        # Test with a simple prompt
        prompt = "Summarize the following news article in one paragraph: The European Union has announced new climate targets for 2030, aiming to reduce greenhouse gas emissions by at least 55% compared to 1990 levels."
        
        logger.info(f"Using model: {openrouter_client.current_model}")
        response = await openrouter_client.generate_content(prompt)
        
        if response and "text" in response:
            logger.info("✅ OpenRouter direct test successful!")
            logger.info(f"Response: {response['text'][:100]}...")
            return True
        else:
            logger.error("❌ OpenRouter direct test failed: Invalid response format")
            return False
            
    except Exception as e:
        logger.error(f"❌ OpenRouter direct test failed with error: {str(e)}")
        return False

async def test_openrouter_fallback():
    """Test OpenRouter fallback mechanism in ContentProcessor."""
    logger.info("Testing OpenRouter fallback mechanism...")
    
    # Store original state
    original_enabled = content_processor.openrouter_enabled
    
    try:
        # Ensure OpenRouter is enabled
        content_processor.openrouter_enabled = True
        
        # Force a failure in Gemini by using an invalid API key temporarily
        original_key = os.environ.get("GEMINI_API_KEY", "")
        os.environ["GEMINI_API_KEY"] = "invalid_key"
        content_processor._init_client()  # Reinitialize with invalid key
        
        # Test with a news article
        article = """
        The United Nations Security Council has called for an immediate ceasefire in Gaza 
        after months of conflict. The resolution, which passed with 14 votes in favor and 
        one abstention, demands an immediate cessation of hostilities and the release of 
        all hostages. Humanitarian aid organizations have welcomed the move, but expressed 
        concerns about implementation on the ground.
        """
        
        url = "https://example.com/news/un-calls-for-ceasefire"
        
        logger.info("Processing content with forced Gemini failure (should trigger OpenRouter fallback)...")
        emoji_str, processed_text = await content_processor.process_content(article, url)
        
        if emoji_str and processed_text:
            logger.info("✅ OpenRouter fallback test successful!")
            logger.info(f"Emoji: {emoji_str}")
            logger.info(f"Processed text: {processed_text[:100]}...")
            return True
        else:
            logger.error("❌ OpenRouter fallback test failed: Invalid response")
            return False
            
    except Exception as e:
        logger.error(f"❌ OpenRouter fallback test failed with error: {str(e)}")
        return False
    finally:
        # Restore original state
        content_processor.openrouter_enabled = original_enabled
        if original_key:
            os.environ["GEMINI_API_KEY"] = original_key
        content_processor._init_client()  # Reinitialize with valid key

async def test_model_rotation():
    """Test OpenRouter model rotation capability."""
    logger.info("Testing OpenRouter model rotation...")
    
    try:
        # Store original model
        original_model = openrouter_client.current_model
        original_index = openrouter_client.fallback_index
        
        # Rotate model
        await openrouter_client.rotate_model()
        new_model = openrouter_client.current_model
        
        if new_model != original_model:
            logger.info(f"✅ Model rotation successful: {original_model} -> {new_model}")
            
            # Test the new model
            prompt = "What is the capital of France?"
            response = await openrouter_client.generate_content(prompt)
            
            if response and "text" in response:
                logger.info(f"✅ Rotated model test successful!")
                logger.info(f"Response: {response['text'][:100]}...")
                return True
            else:
                logger.error("❌ Rotated model test failed: Invalid response format")
                return False
        else:
            logger.error(f"❌ Model rotation failed: Still using {original_model}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Model rotation test failed with error: {str(e)}")
        return False
    finally:
        # Reset to original state
        openrouter_client.current_model = original_model
        openrouter_client.fallback_index = original_index
        openrouter_client.client = None  # Force reinitialization

async def main():
    """Run all tests."""
    logger.info("Starting OpenRouter integration tests...")
    logger.info(f"OpenRouter enabled: {OPENROUTER_ENABLED}")
    logger.info(f"OpenRouter API key: {OPENROUTER_API_KEY[:5]}...{OPENROUTER_API_KEY[-5:] if OPENROUTER_API_KEY else ''}")
    
    # Run tests
    direct_test = await test_openrouter_direct()
    fallback_test = await test_openrouter_fallback()
    rotation_test = await test_model_rotation()
    
    # Summary
    logger.info("\n--- Test Summary ---")
    logger.info(f"Direct OpenRouter client test: {'✅ PASSED' if direct_test else '❌ FAILED'}")
    logger.info(f"OpenRouter fallback mechanism test: {'✅ PASSED' if fallback_test else '❌ FAILED'}")
    logger.info(f"OpenRouter model rotation test: {'✅ PASSED' if rotation_test else '❌ FAILED'}")
    
    if direct_test and fallback_test and rotation_test:
        logger.info("🎉 All tests passed! OpenRouter integration is working correctly.")
        return 0
    else:
        logger.error("❌ Some tests failed. See logs above for details.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
