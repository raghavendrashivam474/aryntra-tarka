"""
Centralised configuration for Aryntra Tarka.

Responsibilities:
- Load environment variables from .env
- Expose typed configuration values
- Prevent direct os.getenv() calls elsewhere in the application

Usage:
    from backend.config.settings import settings
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All fields map directly to keys defined in .env
    """

    # Application
    app_name: str = "Aryntra Tarka"
    app_version: str = "1.0.0"
    app_env: str = "development"
    debug: bool = True

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "llama3.2"
    ollama_default_embedding_model: str = "nomic-embed-text"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Single shared instance
# Import this everywhere configuration is needed
settings = Settings()
