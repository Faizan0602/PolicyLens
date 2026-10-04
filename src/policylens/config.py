"""Configuration management for PolicyLens using pydantic-settings.

Centralizes environment-driven configuration with safe representation output.
"""

import json
from functools import lru_cache
from typing import Any, Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

SENSITIVE_KEY_SUBSTRINGS = ("key", "secret", "password", "token", "auth", "credential")


class Settings(BaseSettings):
    """Core application settings for PolicyLens.

    Loads from environment variables prefixed with POLICYLENS_ or an optional .env file.
    """

    model_config = SettingsConfigDict(
        env_prefix="POLICYLENS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "PolicyLens"
    environment: Literal["development", "staging", "production", "test"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    debug: bool = False

    # Model and Provider Settings
    llm_provider: str = "mock"
    llm_model: str = "gemini-2.5-flash"
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    # Sensitive API Credentials (masked in safe_dump/safe_repr)
    openai_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None

    def safe_dump(self) -> dict[str, Any]:
        """Return a dictionary representation with sensitive values masked."""
        data: dict[str, Any] = {}
        for key, value in self.model_dump().items():
            if isinstance(value, SecretStr) or any(
                sensitive in key.lower() for sensitive in SENSITIVE_KEY_SUBSTRINGS
            ):
                data[key] = "**********"
            else:
                data[key] = value
        return data

    def safe_repr(self) -> str:
        """Return a formatted, safe string representation of settings."""
        return json.dumps(self.safe_dump(), indent=2)


@lru_cache
def get_settings() -> Settings:
    """Return a cached instance of application settings."""
    return Settings()


if __name__ == "__main__":
    settings = get_settings()
    print("PolicyLens Configuration:")
    print(settings.safe_repr())
