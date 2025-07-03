#!/usr/bin/env python3
"""
Simple test script for AI-powered relevance filtering.
Tests the core AI analysis functionality.
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

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
        "text": "Beautiful sunset photos from my vacation in Paris! 🌅 #travel #photography",
        "expected_relevance": "none",
        "category": "irrelevant"
    },
    {
        "text": "🎮 New video game just dropped! Who's playing tonight? DM me for multiplayer sessions.",
        "expected_relevance": "none", 
        "category": "irrelevant"
    }
]

async def test_ai_relevance_filtering():
    """Test the AI-based relevance analysis with filtering logic."""
    print("🚀 Testing AI-Powered Relevance Filtering")
    print("=" * 60)
    
    processor = ContentProcessor()
    threshold = 0.3  # Our filtering threshold
    
    results = {
        "passed": 0,
        "filtered": 0,
        "errors": 0,
        "details": []
    }
    
    for i, test_msg in enumerate(TEST_MESSAGES, 1):
        print(f"\n📝 Test {i}: {test_msg['category'].upper()}")
        print(f"Text: {test_msg['text'][:80]}{'...' if len(test_msg['text']) > 80 else ''}")
        
        try:
            # Get AI analysis
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
                
                # Apply filtering logic
                is_relevant = score >= threshold
                
                if is_relevant:
                    results["passed"] += 1
                    status = "✅ PASSED FILTER"
                else:
                    results["filtered"] += 1
                    status = "🚫 FILTERED OUT"
                
                print(f"{status}")
                print(f"   Score: {score:.3f} (threshold: {threshold})")
                print(f"   Category: {category}")
                print(f"   Confidence: {confidence:.3f}")
                print(f"   Expected: {test_msg['expected_relevance']}")
                print(f"   Reasoning: {reasoning}")
                
                results["details"].append({
                    "test_case": test_msg['category'],
                    "text": test_msg['text'],
                    "expected": test_msg['expected_relevance'],
                    "actual_score": score,
                    "actual_category": category,
                    "confidence": confidence,
                    "is_relevant": is_relevant,
                    "passed_filter": is_relevant,
                    "success": True
                })
                
            else:
                print(f"❌ AI Analysis failed: {result.get('error', 'Unknown error')}")
                results["errors"] += 1
                results["details"].append({
                    "test_case": test_msg['category'],
                    "success": False,
                    "error": result.get('error')
                })
                
        except Exception as e:
            print(f"❌ Exception during analysis: {e}")
            results["errors"] += 1
            results["details"].append({
                "test_case": test_msg['category'],
                "success": False,
                "error": str(e)
            })
            
        # Small delay between requests
        await asyncio.sleep(1)
    
    return results

async def test_different_thresholds():
    """Test filtering with different threshold values."""
    print("\n" + "=" * 60)
    print("🎯 TESTING DIFFERENT THRESHOLD VALUES")
    print("=" * 60)
    
    processor = ContentProcessor()
    thresholds = [0.1, 0.3, 0.5, 0.7, 0.9]
    
    # Use only geopolitical messages for this test
    geo_messages = [msg for msg in TEST_MESSAGES if msg['expected_relevance'] in ['high', 'medium']]
    
    threshold_results = {}
    
    for threshold in thresholds:
        print(f"\n🎯 Testing threshold: {threshold}")
        
        passed = 0
        filtered = 0
        
        for test_msg in geo_messages:
            try:
                result = await processor.process_telegram_message(
                    message_text=test_msg['text'],
                    analysis_type="relevance",
                    channel_context="Test Channel"
                )
                
                if result.get("success", False):
                    score = result.get("relevance_score", 0.0)
                    is_relevant = score >= threshold
                    
                    if is_relevant:
                        passed += 1
                        print(f"   ✅ {test_msg['category']}: {score:.3f}")
                    else:
                        filtered += 1
                        print(f"   🚫 {test_msg['category']}: {score:.3f}")
                        
            except Exception as e:
                print(f"   ❌ {test_msg['category']}: Error - {e}")
            
            await asyncio.sleep(0.5)
        
        threshold_results[threshold] = {
            "passed": passed,
            "filtered": filtered,
            "pass_rate": passed / len(geo_messages) * 100 if geo_messages else 0
        }
        
        print(f"   📊 Results: {passed} passed, {filtered} filtered ({threshold_results[threshold]['pass_rate']:.1f}% pass rate)")
    
    return threshold_results

def save_test_results(filtering_results, threshold_results):
    """Save test results to a JSON file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"basic_relevance_test_results_{timestamp}.json"
    
    test_results = {
        "timestamp": datetime.now().isoformat(),
        "filtering_test": filtering_results,
        "threshold_test": threshold_results,
        "summary": {
            "total_tests": len(TEST_MESSAGES),
            "passed_filter": filtering_results["passed"],
            "filtered_out": filtering_results["filtered"],
            "errors": filtering_results["errors"],
            "success_rate": (filtering_results["passed"] + filtering_results["filtered"]) / len(TEST_MESSAGES) * 100
        }
    }
    
    with open(filename, 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\n💾 Test results saved to: {filename}")

async def main():
    """Run all relevance filtering tests."""
    print("🤖 AI-Powered Relevance Filtering Test")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Test basic filtering
        filtering_results = await test_ai_relevance_filtering()
        
        # Test different thresholds
        threshold_results = await test_different_thresholds()
        
        # Save results
        save_test_results(filtering_results, threshold_results)
        
        print("\n" + "=" * 60)
        print("📊 FINAL SUMMARY")
        print("=" * 60)
        
        total_tests = len(TEST_MESSAGES)
        success_rate = (filtering_results["passed"] + filtering_results["filtered"]) / total_tests * 100
        
        print(f"Total Messages Tested: {total_tests}")
        print(f"Passed Filter: {filtering_results['passed']}")
        print(f"Filtered Out: {filtering_results['filtered']}")
        print(f"Errors: {filtering_results['errors']}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Threshold recommendations
        print(f"\n🎯 Threshold Analysis:")
        for threshold, data in threshold_results.items():
            print(f"   {threshold}: {data['pass_rate']:.1f}% pass rate")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 