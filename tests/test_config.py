"""Unit tests for PolicyLens configuration."""

import os
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from policylens.config import Settings, get_settings


def test_groq_credentials_default_to_none():
    with patch.dict(os.environ, {}, clear=True):
        assert Settings(_env_file=None).groq_api_key is None


def test_groq_settings_load_synthetic_environment_and_mask_secret():
    test_key = "synthetic-groq-test-key"
    with patch.dict(
        os.environ,
        {
            "POLICYLENS_LLM_PROVIDER": "groq",
            "POLICYLENS_LLM_MODEL": "configured-groq-model",
            "POLICYLENS_GROQ_API_KEY": test_key,
        },
        clear=True,
    ):
        settings = Settings(_env_file=None)
    assert settings.llm_provider == "groq"
    assert settings.llm_model == "configured-groq-model"
    assert isinstance(settings.groq_api_key, SecretStr)
    assert settings.groq_api_key.get_secret_value() == test_key
    assert settings.safe_dump()["groq_api_key"] == "**********"
    assert test_key not in settings.safe_repr()
    assert test_key not in repr(settings)


def test_gemini_ipv4_default():
    """The workaround is opt-in and independent of the developer's .env."""
    with patch.dict(os.environ, {}, clear=True):
        assert Settings(_env_file=None).gemini_force_ipv4 is False


@pytest.mark.parametrize("value, expected", [("true", True), ("false", False)])
def test_gemini_ipv4_environment_override(value, expected):
    with patch.dict(os.environ, {"POLICYLENS_GEMINI_FORCE_IPV4": value}, clear=True):
        assert Settings(_env_file=None).gemini_force_ipv4 is expected


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
    from pydantic import SecretStr

    settings = Settings(
        openai_api_key=SecretStr("super-secret-key-123"),
        gemini_api_key=SecretStr("gemini-secret-token-456"),
    )
    safe = settings.safe_dump()
    assert "app_name" in safe
    assert safe["app_name"] == "PolicyLens"
    # Ensure safe_repr is valid JSON
    assert safe["openai_api_key"] == "**********"
    assert safe["gemini_api_key"] == "**********"
    # Ensure safe_repr is valid JSON and does not expose the secrets
    repr_str = settings.safe_repr()
    assert '"app_name": "PolicyLens"' in repr_str
    assert "super-secret-key-123" not in repr_str
    assert "gemini-secret-token-456" not in repr_str
