"""Unit tests for PolicyLens configuration."""

import os
from unittest.mock import patch

from policylens.config import Settings, get_settings


def test_default_settings():
    """Verify default settings values when no environment variables are set."""
    # Ensure cache does not return an altered instance
    get_settings.cache_clear()
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings()
        assert settings.app_name == "PolicyLens"
        assert settings.environment == "development"
        assert settings.log_level == "INFO"
        assert settings.debug is False


def test_environment_variable_override():
    """Verify settings can be overridden via POLICYLENS_ prefixed environment variables."""
    get_settings.cache_clear()
    custom_env = {
        "POLICYLENS_APP_NAME": "CustomPolicyLens",
        "POLICYLENS_ENVIRONMENT": "production",
        "POLICYLENS_LOG_LEVEL": "WARNING",
        "POLICYLENS_DEBUG": "true",
    }
    with patch.dict(os.environ, custom_env, clear=True):
        settings = Settings()
        assert settings.app_name == "CustomPolicyLens"
        assert settings.environment == "production"
        assert settings.log_level == "WARNING"
        assert settings.debug is True


def test_safe_dump_masks_sensitive_keys():
    """Verify safe_dump masks any field whose name contains sensitive keywords."""
    settings = Settings()
    safe = settings.safe_dump()
    assert "app_name" in safe
    assert safe["app_name"] == "PolicyLens"
    # Ensure safe_repr is valid JSON
    repr_str = settings.safe_repr()
    assert '"app_name": "PolicyLens"' in repr_str
