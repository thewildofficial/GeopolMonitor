"""Tests for model capability and equivalence mappings."""
import pytest
from src.utils.model_mapping import ModelEquivalence, ModelCapabilities

def test_get_equivalent_models():
    """Test getting equivalent models across providers."""
    assert ModelEquivalence.get_equivalent_models("gemini-pro") == [
        "deepseek/deepseek-r1:free",
        "google/gemma-3-12b-it:free"
    ]

def test_get_nonexistent_model_equivalence():
    """Test getting equivalents for nonexistent model."""
    assert ModelEquivalence.get_equivalent_models("nonexistent-model") == []

def test_get_model_capabilities():
    """Test getting model capabilities."""
    caps = ModelEquivalence.get_capabilities("gemini-pro")
    assert isinstance(caps, ModelCapabilities)
    assert caps.max_tokens == 2048
    assert caps.context_window == 32768
    assert caps.supports_functions is True

def test_get_nonexistent_model_capabilities():
    """Test getting capabilities for nonexistent model."""
    assert ModelEquivalence.get_capabilities("nonexistent-model") is None

def test_all_mapped_models_have_capabilities():
    """Test that all mapped models have corresponding capabilities."""
    for source_model, target_models in ModelEquivalence._MODEL_EQUIVALENCE.items():
        # Source model should have capabilities
        assert ModelEquivalence.get_capabilities(source_model) is not None
        
        # All target models should have capabilities
        for target_model in target_models:
            assert ModelEquivalence.get_capabilities(target_model) is not None

def test_model_capabilities_dataclass():
    """Test ModelCapabilities dataclass functionality."""
    caps = ModelCapabilities(
        max_tokens=512,
        context_window=4096,
        supports_functions=True,
        expected_style="balanced"
    )
    assert caps.max_tokens == 512
    assert caps.context_window == 4096
    assert caps.supports_functions is True
    assert caps.expected_style == "balanced"