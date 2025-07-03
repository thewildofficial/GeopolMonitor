#!/usr/bin/env python3
"""
Test script for AI-powered relevance filtering in the Telegram monitoring system.
Tests both AI-based and keyword fallback filtering methods.
"""

import asyncio
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from telegram.telethon_redis_integration import TelethonRedisIntegration
from telegram.telethon_client import TelethonMonitorClient
from core.services.redis_pubsub import RedisPubSubService, Priority
from utils.ai import ContentProcessor

# Test messages with known relevance levels
TEST_MESSAGES = [
    {
        "text": "Breaking: Russia launches new military operation in eastern Ukraine. Multiple explosions reported in Donetsk region.",
        "expected_relevance": "high",
        "category": "highly_relevant"
    },
    {
        "text": "President Biden announces new sanctions package against Russian oligarchs following emergency NATO summit.",
        "expected_relevance": "high", 
        "category": "highly_relevant"
    },
    {
        "text": "China's Foreign Ministry responds to EU trade restrictions with diplomatic protest, warns of economic consequences.",
        "expected_relevance": "medium",
        "category": "moderately_relevant"
    },
    {
        "text": "Local election results in German municipality show green party gains, environmentalist policies supported.",
        "expected_relevance": "low",
        "category": "low_relevance"
    },
    {
        "text": "Beautiful sunset photos from my vacation in Paris! 🌅 #travel #photography",
        "expected_relevance": "none",
        "category": "irrelevant"
    },
    {
        "text": "🎮 New video game just dropped! Who's playing tonight? DM me for multiplayer sessions.",
        "expected_relevance": "none", 
        "category": "irrelevant"
    },
    {
        "text": "Cryptocurrency market volatility continues as investors react to Federal Reserve policy announcements.",
        "expected_relevance": "low",
        "category": "economic_relevance"
    },
    {
        "text": "Emergency UN Security Council meeting called following reports of cyber attacks on critical infrastructure.",
        "expected_relevance": "high",
        "category": "security_crisis"
    }
]

async def test_ai_relevance_analysis():
    """Test the AI-based relevance analysis directly."""
    print("=" * 60)
    print("🤖 TESTING AI RELEVANCE ANALYSIS")
    print("=" * 60)
    
    processor = ContentProcessor()
    results = []
    
    for i, test_msg in enumerate(TEST_MESSAGES, 1):
        print(f"\n📝 Test {i}: {test_msg['category'].upper()}")
        print(f"Text: {test_msg['text'][:80]}{'...' if len(test_msg['text']) > 80 else ''}")
        
        try:
            result = await processor.process_telegram_message(
                message_text=test_msg['text'],
                analysis_type="relevance",
                channel_context="Test Channel",
                metadata={"priority": "medium"}
            )
            
            if result.get("success", False):
                score = result.get("relevance_score", 0.0)
                category = result.get("relevance_category", "unknown")
                confidence = result.get("confidence", 0.0)
                reasoning = result.get("reasoning", "")
                
                print(f"✅ AI Analysis:")
                print(f"   Score: {score:.3f}")
                print(f"   Category: {category}")
                print(f"   Confidence: {confidence:.3f}")
                print(f"   Expected: {test_msg['expected_relevance']}")
                print(f"   Reasoning: {reasoning}")
                
                results.append({
                    "test_case": test_msg['category'],
                    "text": test_msg['text'],
                    "expected": test_msg['expected_relevance'],
                    "actual_score": score,
                    "actual_category": category,
                    "confidence": confidence,
                    "success": True
                })
                
            else:
                print(f"❌ AI Analysis failed: {result.get('error', 'Unknown error')}")
                results.append({
                    "test_case": test_msg['category'],
                    "success": False,
                    "error": result.get('error')
                })
                
        except Exception as e:
            print(f"❌ Exception during analysis: {e}")
            results.append({
                "test_case": test_msg['category'],
                "success": False,
                "error": str(e)
            })
            
        # Small delay between requests
        await asyncio.sleep(1)
    
    return results

async def test_keyword_fallback():
    """Test the keyword-based fallback system."""
    print("\n" + "=" * 60)
    print("🔑 TESTING KEYWORD FALLBACK ANALYSIS")
    print("=" * 60)
    
    # Create a mock integration for testing
    class MockTelethonClient:
        def get_stats(self):
            return {}
    
    class MockRedisService:
        def get_stats(self):
            return {}
    
    integration = TelethonRedisIntegration(
        MockTelethonClient(),
        MockRedisService(),
        enable_ai_filtering=False,  # Disable AI to test fallback
        relevance_threshold=0.3
    )
    
    results = []
    
    for i, test_msg in enumerate(TEST_MESSAGES, 1):
        print(f"\n📝 Test {i}: {test_msg['category'].upper()}")
        print(f"Text: {test_msg['text'][:80]}{'...' if len(test_msg['text']) > 80 else ''}")
        
        try:
            channel_metadata = {"title": "Test Channel", "identifier": "test"}
            result = await integration._analyze_geopolitical_relevance(
                test_msg['text'], 
                channel_metadata
            )
            
            score = result.get("relevance_score", 0.0)
            category = result.get("relevance_category", "unknown")
            method = result.get("method", "unknown")
            keywords_found = result.get("total_keyword_matches", 0)
            
            print(f"✅ Keyword Analysis:")
            print(f"   Score: {score:.3f}")
            print(f"   Category: {category}")
            print(f"   Method: {method}")
            print(f"   Keywords found: {keywords_found}")
            print(f"   Expected: {test_msg['expected_relevance']}")
            
            results.append({
                "test_case": test_msg['category'],
                "text": test_msg['text'],
                "expected": test_msg['expected_relevance'],
                "actual_score": score,
                "actual_category": category,
                "keywords_found": keywords_found,
                "success": True
            })
            
        except Exception as e:
            print(f"❌ Exception during analysis: {e}")
            results.append({
                "test_case": test_msg['category'],
                "success": False,
                "error": str(e)
            })
    
    return results

async def test_filtering_integration():
    """Test the complete message filtering workflow."""
    print("\n" + "=" * 60)
    print("🔧 TESTING COMPLETE FILTERING INTEGRATION")
    print("=" * 60)
    
    # Test various threshold levels
    thresholds = [0.1, 0.3, 0.5, 0.7]
    
    for threshold in thresholds:
        print(f"\n🎯 Testing with threshold: {threshold}")
        
        class MockTelethonClient:
            def get_stats(self):
                return {}
        
        class MockRedisService:
            def get_stats(self):
                return {}
        
        integration = TelethonRedisIntegration(
            MockTelethonClient(),
            MockRedisService(),
            enable_ai_filtering=True,
            relevance_threshold=threshold
        )
        
        # Test filtering decisions
        relevant_count = 0
        irrelevant_count = 0
        
        for test_msg in TEST_MESSAGES[:4]:  # Test subset to save API calls
            try:
                channel_metadata = {"title": "Test Channel", "identifier": "test"}
                result = await integration._analyze_geopolitical_relevance(
                    test_msg['text'], 
                    channel_metadata
                )
                
                if result.get("is_relevant", False):
                    relevant_count += 1
                    print(f"   ✅ PASS: {test_msg['category']} (score: {result.get('relevance_score', 0.0):.3f})")
                else:
                    irrelevant_count += 1
                    print(f"   🚫 FILTER: {test_msg['category']} (score: {result.get('relevance_score', 0.0):.3f})")
                    
            except Exception as e:
                print(f"   ❌ ERROR: {test_msg['category']} - {e}")
            
            await asyncio.sleep(0.5)
        
        print(f"   📊 Results: {relevant_count} relevant, {irrelevant_count} filtered")

def save_test_results(ai_results, keyword_results):
    """Save test results to a JSON file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"relevance_filtering_test_results_{timestamp}.json"
    
    test_results = {
        "timestamp": datetime.now().isoformat(),
        "ai_analysis_results": ai_results,
        "keyword_analysis_results": keyword_results,
        "summary": {
            "ai_tests_run": len(ai_results),
            "ai_successful": len([r for r in ai_results if r.get("success", False)]),
            "keyword_tests_run": len(keyword_results),
            "keyword_successful": len([r for r in keyword_results if r.get("success", False)])
        }
    }
    
    with open(filename, 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\n💾 Test results saved to: {filename}")

async def main():
    """Run all relevance filtering tests."""
    print("🚀 Starting Relevance Filtering Tests")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Test AI-based analysis
        ai_results = await test_ai_relevance_analysis()
        
        # Test keyword fallback
        keyword_results = await test_keyword_fallback()
        
        # Test complete integration
        await test_filtering_integration()
        
        # Save results
        save_test_results(ai_results, keyword_results)
        
        print("\n" + "=" * 60)
        print("📊 FINAL SUMMARY")
        print("=" * 60)
        
        ai_success_rate = len([r for r in ai_results if r.get("success", False)]) / len(ai_results) * 100
        keyword_success_rate = len([r for r in keyword_results if r.get("success", False)]) / len(keyword_results) * 100
        
        print(f"AI Analysis Success Rate: {ai_success_rate:.1f}%")
        print(f"Keyword Analysis Success Rate: {keyword_success_rate:.1f}%")
        print(f"Total Test Cases: {len(TEST_MESSAGES)}")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 