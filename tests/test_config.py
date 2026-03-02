"""Tests for configuration module."""

import pytest
from src.config import Config


def test_config_default_values():
    """Test that default configuration values are set correctly."""
    config = Config()

    assert config.ocr_lang == "ch"
    assert config.asr_model_size == "base"
    assert config.frame_interval == 1.0


def test_config_get_set():
    """Test getting and setting configuration values."""
    config = Config()

    # Get existing value
    assert config.get("ocr.lang") == "ch"

    # Set new value
    config.set("ocr.lang", "en")
    assert config.get("ocr.lang") == "en"

    # Get with default
    assert config.get("nonexistent.key", "default") == "default"


def test_config_from_dict():
    """Test creating config from dictionary."""
    config = Config()

    # Check structure
    assert isinstance(config._config, dict)
    assert "glm" in config._config
    assert "ocr" in config._config
    assert "asr" in config._config
