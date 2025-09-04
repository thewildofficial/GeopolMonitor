"""OpenRouter API client implementation."""
import os
import logging
import asyncio
from typing import Optional, Dict, Any, List
from llama_index.llms.openrouter import OpenRouter
from llama_index.core.llms import ChatMessage
from src.utils.model_mapping import ModelEquivalence

logger = logging.getLogger(__name__)

# Default model rotation sequence
OPENROUTER_FALLBACK_MODELS: List[str] = [
    'deepseek/deepseek-chat:free',
    'deepseek/deepseek-r1-zero:free',
    'moonshotai/moonlight-16b-a3b-instruct:free'
]

class OpenRouterClient:
    """Client for interacting with OpenRouter API with fallback support."""
    
    def __init__(self):
        self.current_model = "deepseek/deepseek-r1:free"
        self.fallback_index = 0
        self.max_retries = 3
        self.client = None
    
    def _init_client(self) -> None:
        """Initialize or reinitialize the OpenRouter client."""
        if self.client is not None:
            return
            
        # Get model capabilities
        capabilities = ModelEquivalence.get_capabilities(self.current_model)
        if not capabilities:
            raise ValueError(f"No capabilities found for model {self.current_model}")
            
        self.client = OpenRouter(
            api_key=os.getenv("OPENROUTER_API_KEY", "test-key"),
            model=self.current_model,
            max_tokens=capabilities.max_tokens,
            context_window=capabilities.context_window
        )

    async def rotate_model(self) -> None:
        """Rotate to the next available model."""
        if self.fallback_index >= len(OPENROUTER_FALLBACK_MODELS):
            logger.error("No more fallback models available")
            raise Exception("All fallback models exhausted")
            
        self.current_model = OPENROUTER_FALLBACK_MODELS[self.fallback_index]
        self.fallback_index += 1
        self.client = None  # Force client reinitialization
        
        try:
            self._init_client()
            logger.info(f"Switched to fallback model: {self.current_model}")
        except ValueError as e:
            logger.error(f"Model initialization failed: {e}")
            # If current model fails, try next one
            return await self.rotate_model()

    async def _handle_error(self, error: Exception, retry_count: int) -> None:
        """Handle errors with appropriate backoff and model rotation."""
        error_str = str(error).lower()
        
        if any(msg in error_str for msg in ["quota exceeded", "capacity", "unavailable"]):
            # For quota/capacity issues, try rotating models
            try:
                await self.rotate_model()
            except Exception as e:
                # If we run out of models, re-raise with the exhausted message
                if "all fallback models exhausted" in str(e).lower():
                    raise Exception("All fallback models exhausted") from error
                raise
        elif "rate limit" in error_str:
            # For rate limits, use exponential backoff starting from 2^1
            wait_time = 2 ** (retry_count + 1)  # Start from 2^1=2, then 2^2=4, 2^3=8
            await asyncio.sleep(wait_time)
        else:
            # Default backoff for other errors
            await asyncio.sleep(1)

    async def generate_content(self, prompt: str) -> Dict[str, Any]:
        """Generate content with automatic fallback to alternative models."""
        self._init_client()
        retries = 0
        last_error = None
        
        while retries < self.max_retries:
            try:
                message = ChatMessage(role="user", content=prompt)
                response = await self.client.achat([message])
                
                # Validate response
                if not response or not response.message or not response.message.content:
                    raise Exception("Invalid response format")
                    
                return {"text": response.message.content}
                
            except Exception as e:
                last_error = e
                
                # Handle the error with appropriate backoff/rotation
                try:
                    await self._handle_error(e, retries)
                except Exception as handle_error:
                    # If error handling itself failed (e.g., no more models), propagate that error
                    raise handle_error
                
                retries += 1
                if retries < self.max_retries:
                    logger.warning(f"Retry {retries}/{self.max_retries} after error: {e}")
        
        # After max retries, try one final model rotation before giving up
        try:
            await self.rotate_model()
            # One final attempt with the new model
            message = ChatMessage(role="user", content=prompt)
            response = await self.client.achat([message])
            if not response or not response.message or not response.message.content:
                raise Exception("Invalid response format")
            return {"text": response.message.content}
        except Exception as e:
            if "all fallback models exhausted" in str(e).lower():
                raise Exception("All fallback models exhausted") from e
            logger.error(f"Failed after all retries. Last error: {e}")
            raise e

# Create singleton instance
openrouter_client = OpenRouterClient()