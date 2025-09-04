"""Model equivalence and capability mappings."""
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class ModelCapabilities:
    """Model capabilities and constraints."""
    max_tokens: int
    context_window: int
    supports_functions: bool
    expected_style: str

class ModelEquivalence:
    """Maps models across different providers and their capabilities."""
    
    _MODEL_CAPABILITIES: Dict[str, ModelCapabilities] = {
        # OpenRouter Models
        "deepseek/deepseek-r1:free": ModelCapabilities(
            max_tokens=512,
            context_window=4096,
            supports_functions=True,
            expected_style="balanced"
        ),
        "google/gemma-3-12b-it:free": ModelCapabilities(
            max_tokens=512,
            context_window=4096,
            supports_functions=True,
            expected_style="balanced"
        ),
        "deepseek/deepseek-chat:free": ModelCapabilities(
            max_tokens=512,
            context_window=4096,
            supports_functions=True,
            expected_style="balanced"
        ),
        "deepseek/deepseek-r1-zero:free": ModelCapabilities(
            max_tokens=512,
            context_window=4096,
            supports_functions=True,
            expected_style="balanced"
        ),
        "moonshotai/moonlight-16b-a3b-instruct:free": ModelCapabilities(
            max_tokens=512,
            context_window=4096,
            supports_functions=True,
            expected_style="balanced"
        ),
        "qwen/qwen-1-5-72b:free": ModelCapabilities(
            max_tokens=512,
            context_window=4096,
            supports_functions=True,
            expected_style="balanced"
        ),
        
        # Gemini Models
        "gemini-pro": ModelCapabilities(
            max_tokens=2048,
            context_window=32768,
            supports_functions=True,
            expected_style="precise"
        ),
        "gemini-2.0-flash-thinking-exp-01-21": ModelCapabilities(
            max_tokens=512,
            context_window=4096,
            supports_functions=True,
            expected_style="analytical"
        )
    }
    
    _MODEL_EQUIVALENCE = {
        # Gemini -> OpenRouter
        "gemini-pro": ["deepseek/deepseek-r1:free", "google/gemma-3-12b-it:free"],
        "gemini-2.0-flash-thinking-exp-01-21": [
            "google/gemma-3-12b-it:free",
            "deepseek/deepseek-r1:free",
            "deepseek/deepseek-chat:free",
            "moonshotai/moonlight-16b-a3b-instruct:free"
        ],
        
        # OpenRouter -> Gemini
        "deepseek/deepseek-r1:free": ["gemini-pro"],
        "google/gemma-3-12b-it:free": ["gemini-pro"],
        "deepseek/deepseek-chat:free": ["gemini-pro"],
        "deepseek/deepseek-r1-zero:free": ["gemini-pro"],
        "moonshotai/moonlight-16b-a3b-instruct:free": ["gemini-pro"]
    }
    
    @classmethod
    def get_equivalent_models(cls, model_name: str) -> List[str]:
        """Get equivalent models across providers."""
        return cls._MODEL_EQUIVALENCE.get(model_name, [])
    
    @classmethod
    def get_capabilities(cls, model_name: str) -> Optional[ModelCapabilities]:
        """Get model capabilities if known."""
        return cls._MODEL_CAPABILITIES.get(model_name)