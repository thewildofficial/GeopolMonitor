"""Tests for ContentProcessor with OpenRouter integration."""
import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.utils.ai import ContentProcessor
from src.utils.openrouter_client import OpenRouterClient

@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with patch('src.utils.ai.OPENROUTER_ENABLED', True):
        with patch('src.utils.ai.GEMINI_API_KEYS', ['test-key']):
            with patch('src.utils.ai.genai') as mock_genai:
                mock_genai.configure = Mock()
                yield

@pytest.fixture
def content_processor(mock_settings):
    """Create a ContentProcessor instance for testing."""
    with patch('src.utils.ai.ContentProcessor._init_client'):
        processor = ContentProcessor()
        processor.client = Mock()
        processor.client.models = Mock()
        processor.client.models.generate_content = AsyncMock()
        yield processor

@pytest.mark.asyncio
async def test_content_processor_with_openrouter_fallback(content_processor):
    """Test ContentProcessor falls back to OpenRouter on Gemini failure."""
    # Mock Gemini API failure
    content_processor.client.models.generate_content.side_effect = Exception("RESOURCE_EXHAUSTED")
    
    # Mock OpenRouter response
    mock_response = {"text": "\nEMOJI_1: 🌍\nEMOJI_2: 📰\nTEXT: Processed by OpenRouter"}
    
    # Create a proper mock for OpenRouter client
    mock_openrouter = Mock()
    mock_openrouter.generate_content = AsyncMock(return_value=mock_response)
    
    with patch('src.utils.ai.openrouter_client', mock_openrouter):
        result = await content_processor.process_content(
            "Test content",
            "https://example.com",
            is_title=False
        )
        
        assert result[0] == "🌍📰"
        assert result[1] == "Processed by OpenRouter"

@pytest.mark.asyncio
async def test_openrouter_model_rotation(content_processor):
    """Test OpenRouter model rotation on failures."""
    # Mock Gemini API failure
    content_processor.client.models.generate_content.side_effect = Exception("RESOURCE_EXHAUSTED")
    
    # Create OpenRouter mock with state
    mock_openrouter = Mock()
    mock_openrouter.generate_content = AsyncMock(side_effect=[
        Exception("quota exceeded"),
        {"text": "\nEMOJI_1: 🌍\nEMOJI_2: 📰\nTEXT: Success with fallback model"}
    ])
    mock_openrouter.rotate_model = AsyncMock()
    
    with patch('src.utils.ai.openrouter_client', mock_openrouter):
        result = await content_processor.process_content(
            "Test content",
            "https://example.com",
            is_title=False
        )
        
        assert mock_openrouter.rotate_model.called
        assert result[0] == "🌍📰"
        assert result[1] == "Success with fallback model"

@pytest.mark.asyncio
async def test_content_processor_error_handling(content_processor):
    """Test error handling in ContentProcessor with both APIs failing."""
    # Mock both APIs failing
    content_processor.client.models.generate_content.side_effect = Exception("Gemini error")
    
    mock_openrouter = Mock()
    mock_openrouter.generate_content = AsyncMock(side_effect=Exception("OpenRouter error"))
    
    with patch('src.utils.ai.openrouter_client', mock_openrouter):
        result = await content_processor.process_content(
            "Test content",
            "https://example.com",
            is_title=False
        )
        
        # Should return default values on complete failure
        assert result[0] == "📰🌐"  # Default emoji
        assert result[1] == "Test content"  # Original text

@pytest.mark.asyncio
async def test_sentiment_analysis_with_openrouter(content_processor):
    """Test sentiment analysis using OpenRouter."""
    # Mock Gemini API failure
    content_processor.client.models.generate_content.side_effect = Exception("Gemini error")
    
    # Mock OpenRouter response
    mock_response = {
        "text": "SENTIMENT: 0.8\nBIAS_CATEGORY: western\nBIAS_SCORE: 0.6"
    }
    
    mock_openrouter = Mock()
    mock_openrouter.generate_content = AsyncMock(return_value=mock_response)
    
    with patch('src.utils.ai.openrouter_client', mock_openrouter):
        result = await content_processor.analyze_sentiment_and_bias(
            "Test content"
        )
        
        assert isinstance(result, tuple)
        assert len(result) == 3
        sentiment, category, bias = result
        assert sentiment == 0.8
        assert category == "western"
        assert bias == 0.6