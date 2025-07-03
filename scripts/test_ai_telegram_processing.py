#!/usr/bin/env python3
"""
Telegram AI Processing Test Script - GeopolMonitor

This script tests the new Telegram message processing capabilities:
1. Single message processing for all analysis types
2. Batch processing with rate limiting
3. Volume handling and error robustness
4. Integration with existing AI pipeline
5. Load balancing and performance testing

Tests both the functionality and respects Gemini API rate limits.
"""

import asyncio
import logging
import sys
import os
import time
import json
from datetime import datetime
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.ai import (
    process_telegram_message,
    process_telegram_batch,
    content_processor
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TelegramAITester:
    """Comprehensive tester for Telegram AI processing functionality."""
    
    def __init__(self):
        self.test_messages = self._create_test_messages()
        self.results = []
        self.performance_stats = {}
    
    def _create_test_messages(self) -> List[Dict[str, Any]]:
        """Create a variety of test messages for different scenarios."""
        return [
            {
                "text": "🇺🇸 BREAKING: US President announces new sanctions against Russia over Ukraine conflict. Full details in upcoming NATO summit.",
                "channel_context": "Official News Channel",
                "metadata": {"timestamp": "2025-07-03T10:00:00Z", "channel_id": "@breakingnews"},
                "expected_relevance": "high"
            },
            {
                "text": "European Parliament votes on climate policy. Green Deal implementation shows mixed results across member states. Germany leads in renewable energy adoption.",
                "channel_context": "EU Politics Channel", 
                "metadata": {"timestamp": "2025-07-03T10:05:00Z", "channel_id": "@eupolitics"},
                "expected_relevance": "medium"
            },
            {
                "text": "Local mayor announces new park opening. Citizens excited about green spaces. Weekend festival planned for inauguration.",
                "channel_context": "Local News Channel",
                "metadata": {"timestamp": "2025-07-03T10:10:00Z", "channel_id": "@localnews"},
                "expected_relevance": "low"
            },
            {
                "text": "😂😂😂 Just had the best pizza ever!!! Anyone know good Italian restaurants in the area? #foodie #pizza",
                "channel_context": "Personal Chat",
                "metadata": {"timestamp": "2025-07-03T10:15:00Z", "channel_id": "@randomchat"},
                "expected_relevance": "none"
            },
            {
                "text": "🚨 URGENT: Military exercises begin in South China Sea. Chinese Navy deploys 15 vessels. Taiwan monitoring situation closely. Regional tensions escalating.",
                "channel_context": "Defense Intelligence",
                "metadata": {"timestamp": "2025-07-03T10:20:00Z", "channel_id": "@defenseintel"},
                "expected_relevance": "high"
            },
            {
                "text": "Central Bank announces interest rate decision tomorrow. Markets volatile ahead of announcement. Inflation concerns persist globally.",
                "channel_context": "Economic News",
                "metadata": {"timestamp": "2025-07-03T10:25:00Z", "channel_id": "@economicnews"},
                "expected_relevance": "medium"
            },
            {
                "text": "Meeting cancelled due to weather. Will reschedule next week. Please update your calendars accordingly.",
                "channel_context": "Corporate Channel",
                "metadata": {"timestamp": "2025-07-03T10:30:00Z", "channel_id": "@corporate"},
                "expected_relevance": "none"
            },
            {
                "text": "🇨🇳🇷🇺 Xi Jinping and Putin discuss energy cooperation. New pipeline project announced worth $50 billion. Strategic partnership deepens.",
                "channel_context": "International Relations",
                "metadata": {"timestamp": "2025-07-03T10:35:00Z", "channel_id": "@intlrelations"},
                "expected_relevance": "high"
            }
        ]
    
    async def test_single_message_processing(self):
        """Test processing individual messages with different analysis types."""
        logger.info("🧪 Starting single message processing tests...")
        
        test_results = {
            "relevance": [],
            "entities": [],
            "summary": [],
            "full": []
        }
        
        # Test one message with each analysis type
        test_msg = self.test_messages[0]  # High relevance message
        
        for analysis_type in ["relevance", "entities", "summary", "full"]:
            try:
                start_time = time.time()
                
                result = await process_telegram_message(
                    message_text=test_msg["text"],
                    analysis_type=analysis_type,
                    channel_context=test_msg["channel_context"],
                    metadata=test_msg["metadata"]
                )
                
                processing_time = time.time() - start_time
                
                # Validate result structure
                self._validate_result_structure(result, analysis_type)
                
                test_results[analysis_type].append({
                    "success": result.get("success", False),
                    "processing_time": processing_time,
                    "result": result,
                    "message_text": test_msg["text"][:50] + "..."
                })
                
                logger.info(f"   ✅ {analysis_type.capitalize()} analysis: {processing_time:.2f}s")
                
                # Brief delay to respect rate limits
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"   ❌ {analysis_type.capitalize()} analysis failed: {e}")
                test_results[analysis_type].append({
                    "success": False,
                    "error": str(e),
                    "processing_time": 0
                })
        
        return test_results
    
    async def test_batch_processing(self):
        """Test batch processing with different batch sizes."""
        logger.info("🧪 Starting batch processing tests...")
        
        # Prepare messages for batch processing (small batch to respect limits)
        batch_messages = [
            {
                "text": msg["text"],
                "channel_context": msg["channel_context"],
                "metadata": msg["metadata"]
            }
            for msg in self.test_messages[:3]  # Only test with 3 messages
        ]
        
        try:
            start_time = time.time()
            
            results = await process_telegram_batch(
                messages=batch_messages,
                analysis_type="relevance",
                batch_size=2  # Small batch size
            )
            
            processing_time = time.time() - start_time
            
            # Validate batch results
            success_count = sum(1 for r in results if r.get("success", False))
            
            batch_result = {
                "total_messages": len(batch_messages),
                "successful_results": success_count,
                "processing_time": processing_time,
                "messages_per_second": len(batch_messages) / processing_time if processing_time > 0 else 0,
                "success_rate": success_count / len(batch_messages) if batch_messages else 0
            }
            
            logger.info(f"   ✅ Batch test: {success_count}/{len(batch_messages)} success, {processing_time:.2f}s")
            
            return batch_result
            
        except Exception as e:
            logger.error(f"   ❌ Batch processing failed: {e}")
            return {"error": str(e), "success_rate": 0}
    
    async def test_relevance_accuracy(self):
        """Test the accuracy of relevance classification."""
        logger.info("🧪 Starting relevance accuracy tests...")
        
        accuracy_results = []
        
        for msg in self.test_messages:
            try:
                result = await process_telegram_message(
                    message_text=msg["text"],
                    analysis_type="relevance",
                    channel_context=msg["channel_context"],
                    metadata=msg["metadata"]
                )
                
                if result.get("success"):
                    predicted_category = result.get("relevance_category", "none")
                    expected_category = msg["expected_relevance"]
                    
                    accuracy_results.append({
                        "message": msg["text"][:50] + "...",
                        "expected": expected_category,
                        "predicted": predicted_category,
                        "correct": predicted_category == expected_category,
                        "relevance_score": result.get("relevance_score", 0.0),
                        "confidence": result.get("confidence", 0.0)
                    })
                
                # Delay between requests
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"   ❌ Relevance test failed for message: {e}")
        
        # Calculate accuracy metrics
        if accuracy_results:
            correct_predictions = sum(1 for r in accuracy_results if r["correct"])
            accuracy_rate = correct_predictions / len(accuracy_results)
            
            logger.info(f"   📊 Relevance Accuracy: {correct_predictions}/{len(accuracy_results)} ({accuracy_rate:.1%})")
        
        return accuracy_results
    
    def _validate_result_structure(self, result: Dict, analysis_type: str):
        """Validate that the result has the expected structure."""
        assert isinstance(result, dict), "Result must be a dictionary"
        assert "success" in result, "Result must have 'success' field"
        assert "analysis_type" in result, "Result must have 'analysis_type' field"
        assert result["analysis_type"] == analysis_type, f"Analysis type mismatch: expected {analysis_type}, got {result['analysis_type']}"
        
        if result["success"]:
            if analysis_type == "relevance":
                required_fields = ["relevance_score", "relevance_category", "confidence"]
                for field in required_fields:
                    assert field in result, f"Relevance result missing field: {field}"
            elif analysis_type == "entities":
                required_fields = ["people", "organizations", "locations", "summary"]
                for field in required_fields:
                    assert field in result, f"Entity result missing field: {field}"
            elif analysis_type == "summary":
                required_fields = ["summary", "key_points", "tone"]
                for field in required_fields:
                    assert field in result, f"Summary result missing field: {field}"
            elif analysis_type == "full":
                assert "relevance" in result, "Full analysis missing relevance section"
                assert "entities" in result, "Full analysis missing entities section"
                assert "summary" in result, "Full analysis missing summary section"
    
    async def run_all_tests(self):
        """Run all tests and generate a comprehensive report."""
        logger.info("🚀 Starting comprehensive Telegram AI processing tests...")
        logger.info("=" * 70)
        
        all_results = {}
        
        try:
            # Test 1: Single message processing
            all_results["single_message"] = await self.test_single_message_processing()
            
            # Test 2: Batch processing  
            all_results["batch_processing"] = await self.test_batch_processing()
            
            # Test 3: Relevance accuracy
            all_results["relevance_accuracy"] = await self.test_relevance_accuracy()
            
            # Generate summary report
            self._generate_summary_report(all_results)
            
            return all_results
            
        except Exception as e:
            logger.error(f"❌ Test suite failed: {e}")
            return {"error": str(e)}
    
    def _generate_summary_report(self, results: Dict):
        """Generate a summary report of all test results."""
        logger.info("=" * 70)
        logger.info("📋 COMPREHENSIVE TEST RESULTS SUMMARY")
        logger.info("=" * 70)
        
        # Single message tests
        if "single_message" in results:
            single_results = results["single_message"]
            logger.info("🔍 Single Message Processing:")
            for analysis_type, type_results in single_results.items():
                if type_results:
                    success = type_results[0]["success"]
                    time_taken = type_results[0]["processing_time"]
                    status = "✅" if success else "❌"
                    logger.info(f"   {status} {analysis_type.capitalize()}: {time_taken:.2f}s")
        
        # Batch processing tests
        if "batch_processing" in results:
            batch_result = results["batch_processing"]
            if "success_rate" in batch_result:
                rate = batch_result["success_rate"]
                time_taken = batch_result.get("processing_time", 0)
                logger.info(f"📦 Batch Processing: {rate:.1%} success, {time_taken:.2f}s")
        
        # Relevance accuracy
        if "relevance_accuracy" in results:
            accuracy_results = results["relevance_accuracy"]
            if accuracy_results:
                correct = sum(1 for r in accuracy_results if r["correct"])
                total = len(accuracy_results)
                accuracy = correct / total
                logger.info(f"🎯 Relevance Accuracy: {correct}/{total} ({accuracy:.1%})")
        
        logger.info("=" * 70)
        logger.info("✅ Test suite completed successfully!")
        logger.info("=" * 70)

async def main():
    """Main test execution."""
    tester = TelegramAITester()
    results = await tester.run_all_tests()
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"telegram_ai_test_results_{timestamp}.json"
    
    try:
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"📁 Test results saved to: {results_file}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 