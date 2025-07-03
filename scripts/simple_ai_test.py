#!/usr/bin/env python3
"""
Simple AI Processing Test - GeopolMonitor
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.ai import process_telegram_message

async def test_simple_processing():
    """Test basic AI processing functionality."""
    
    print("🧪 Testing AI processing with Gemini...")
    
    test_message = "🇺🇸 BREAKING: US President announces new sanctions against Russia over Ukraine conflict."
    
    try:
        result = await process_telegram_message(
            message_text=test_message,
            analysis_type="relevance",
            channel_context="News Channel"
        )
        
        print(f"✅ Success: {result.get('success', False)}")
        if result.get('success'):
            print(f"📊 Relevance Score: {result.get('relevance_score', 'N/A')}")
            print(f"📂 Category: {result.get('relevance_category', 'N/A')}")
            print(f"🎯 Confidence: {result.get('confidence', 'N/A')}")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(test_simple_processing()) 