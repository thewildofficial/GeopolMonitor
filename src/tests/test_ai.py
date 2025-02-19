"""Tests for AI processing utilities."""
import pytest
import asyncio
from unittest.mock import Mock, patch
from src.utils.ai import ContentProcessor

@pytest.fixture
def content_processor():
    """Create a ContentProcessor instance for testing."""
    return ContentProcessor()

@pytest.mark.asyncio
async def test_analyze_sentiment_and_bias(content_processor):
    """Test sentiment and bias analysis functionality."""
    # Test cases with expected results
    test_cases = [
        {
            'text': 'Chinese military conducts exercises near Taiwan',
            'expected_bias_category': 'chinese',
            'sentiment_range': (-0.5, 0.0),
            'bias_range': (0.6, 1.0)
        },
        {
            'text': 'UN peacekeepers successfully negotiate ceasefire agreement',
            'expected_bias_category': 'neutral',
            'sentiment_range': (0.3, 1.0),
            'bias_range': (0.0, 0.3)
        },
        {
            'text': 'Western sanctions impact Russian economy significantly',
            'expected_bias_category': 'western',
            'sentiment_range': (-0.8, -0.2),
            'bias_range': (0.5, 1.0)
        }
    ]

    for case in test_cases:
        with patch.object(content_processor.client.models, 'generate_content') as mock_generate:
            mock_response = Mock()
            mock_response.text = f"SENTIMENT: {case['sentiment_range'][0]}\nBIAS_CATEGORY: {case['expected_bias_category']}\nBIAS_SCORE: {case['bias_range'][0]}"
            mock_generate.return_value = mock_response
            
            sentiment_score, bias_category, bias_score = await content_processor.analyze_sentiment_and_bias(case['text'])

            # Verify bias category matches expected
            assert bias_category == case['expected_bias_category'], \
                f"Expected bias category {case['expected_bias_category']}, got {bias_category}"

            # Verify sentiment score is within expected range
            assert case['sentiment_range'][0] <= sentiment_score <= case['sentiment_range'][1], \
                f"Sentiment score {sentiment_score} outside expected range {case['sentiment_range']}"

            # Verify bias score is within expected range
            assert case['bias_range'][0] <= bias_score <= case['bias_range'][1], \
                f"Bias score {bias_score} outside expected range {case['bias_range']}"

@pytest.mark.asyncio
async def test_analyze_sentiment_and_bias_error_handling(content_processor):
    """Test error handling during analysis."""
    with patch.object(content_processor.client.models, 'generate_content', side_effect=Exception('Test error')):
        sentiment_score, bias_category, bias_score = await content_processor.analyze_sentiment_and_bias('test text')
        assert sentiment_score == 0.0
        assert bias_category == 'neutral'
        assert bias_score == 0.0

@pytest.mark.asyncio
async def test_analyze_sentiment_and_bias_api_error(content_processor):
    """Test handling of API errors during analysis."""
    with patch.object(content_processor.client.models, 'generate_content', side_effect=Exception('API Error')):
        sentiment_score, bias_category, bias_score = await content_processor.analyze_sentiment_and_bias('test text')
        assert sentiment_score == 0.0
        assert bias_category == 'neutral'
        assert bias_score == 0.0

@pytest.mark.asyncio
async def test_analyze_sentiment_and_bias_rate_limit(content_processor):
    """Test rate limiting behavior."""
    # Simulate rate limit exceeded
    with patch.object(content_processor.client.models, 'generate_content',
              side_effect=Exception('RESOURCE_EXHAUSTED: Rate limit exceeded')):
        sentiment_score, bias_category, bias_score = await content_processor.analyze_sentiment_and_bias('test text')
        assert sentiment_score == 0.0
        assert bias_category == 'neutral'
        assert bias_score == 0.0

@pytest.mark.asyncio
async def test_analyze_sentiment_and_bias_invalid_input(content_processor):
    """Test handling of invalid input."""
    with patch.object(content_processor.client.models, 'generate_content',
              side_effect=Exception('INVALID_ARGUMENT: Invalid input')):
        sentiment_score, bias_category, bias_score = await content_processor.analyze_sentiment_and_bias('test text')
        assert sentiment_score == 0.0
        assert bias_category == 'neutral'
        assert bias_score == 0.0