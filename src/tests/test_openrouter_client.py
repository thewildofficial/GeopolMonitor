"""Tests for OpenRouter integration and fallback functionality."""
import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.utils.openrouter_client import OpenRouterClient
from src.utils.model_mapping import ModelEquivalence

@pytest.fixture
def mock_client():
    """Create a mock OpenRouter client for testing."""
    with patch('src.utils.openrouter_client.OpenRouter') as mock_openrouter:
        with patch('src.utils.openrouter_client.OPENROUTER_FALLBACK_MODELS', [
            'deepseek/deepseek-chat:free',
            'deepseek/deepseek-r1-zero:free',
            'moonshotai/moonlight-16b-a3b-instruct:free'
        ]):
            client = OpenRouterClient()
            mock_openrouter.return_value.achat = AsyncMock()
            mock_openrouter.return_value.max_tokens = 512
            mock_openrouter.return_value.context_window = 4096
            client.client = mock_openrouter.return_value
            yield client

@pytest.mark.asyncio
async def test_init_client(mock_client):
    """Test client initialization with primary model."""
    assert mock_client.current_model == 'deepseek/deepseek-r1:free'
    assert mock_client.fallback_index == 0
    assert mock_client.max_retries == 3

@pytest.mark.asyncio
async def test_rotate_model(mock_client):
    """Test model rotation functionality."""
    initial_model = mock_client.current_model
    await mock_client.rotate_model()
    assert mock_client.current_model == 'deepseek/deepseek-chat:free'

@pytest.mark.asyncio
async def test_rotate_model_exhaustion(mock_client):
    """Test behavior when all fallback models are exhausted."""
    # Exhaust all models
    await mock_client.rotate_model()  # First rotation
    await mock_client.rotate_model()  # Second rotation
    await mock_client.rotate_model()  # Third rotation
    
    with pytest.raises(Exception, match="All fallback models exhausted"):
        await mock_client.rotate_model()

@pytest.mark.asyncio
async def test_generate_content_success(mock_client):
    """Test successful content generation."""
    mock_response = AsyncMock()
    mock_response.message.content = "Test response"
    mock_client.client.achat.return_value = mock_response
    
    response = await mock_client.generate_content("Test prompt")
    assert response == {"text": "Test response"}

@pytest.mark.asyncio
async def test_generate_content_rate_limit(mock_client):
    """Test rate limit handling with automatic fallback."""
    mock_client.client.achat.side_effect = [
        Exception("rate limit exceeded"),
        AsyncMock(message=Mock(content="Fallback response"))
    ]
    
    response = await mock_client.generate_content("Test prompt")
    assert response == {"text": "Fallback response"}

@pytest.mark.asyncio
async def test_generate_content_quota_exceeded(mock_client):
    """Test quota exceeded handling."""
    mock_client.client.achat.side_effect = Exception("quota exceeded")
    
    with pytest.raises(Exception, match="All fallback models exhausted"):
        await mock_client.generate_content("Test prompt")

@pytest.mark.asyncio
async def test_generate_content_validation(mock_client):
    """Test response validation."""
    mock_response = AsyncMock()
    mock_response.message.content = None
    mock_client.client.achat.return_value = mock_response
    
    with pytest.raises(Exception, match="Invalid response format"):
        await mock_client.generate_content("Test prompt")

@pytest.mark.asyncio
async def test_exponential_backoff(mock_client):
    """Test exponential backoff behavior on rate limits."""
    sleep_times = []

    async def mock_sleep(seconds):
        sleep_times.append(seconds)

    with patch('asyncio.sleep', new=mock_sleep):
        mock_client.client.achat.side_effect = [
            Exception("rate limit"),
            Exception("rate limit"),
            Exception("rate limit")
        ]
        
        try:
            await mock_client.generate_content("Test prompt")
        except Exception:
            pass

        assert len(sleep_times) > 1
        assert sleep_times[0] == 2  # First retry: 2^1
        assert sleep_times[1] == 4  # Second retry: 2^2

@pytest.mark.asyncio
async def test_client_respects_model_capabilities(mock_client):
    """Test that client initialization respects model capabilities."""
    capabilities = ModelEquivalence.get_capabilities('deepseek/deepseek-r1:free')
    assert capabilities is not None
    assert mock_client.client.max_tokens == capabilities.max_tokens
    assert mock_client.client.context_window == capabilities.context_window