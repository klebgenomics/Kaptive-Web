"""Configuration module."""

import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict


# Classes --------------------------------------------------------------------------------------------------------------
class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "Kaptive-Web"
    database_url: str = "sqlite+aiosqlite:///kaptive_web.db"

    # OAuth2 GitHub Settings
    github_client_id: str = ""
    github_client_secret: str = ""

    # OAuth2 ORCID Settings
    orcid_client_id: str = ""
    orcid_client_secret: str = ""

    # API Key Settings
    api_key_prefix: str = "kw_live_"
    api_key_length: int = 32

    # Web Server Settings
    secret_key: str = secrets.token_hex(32)
    cors_origins: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]

    # Concurrency
    max_pipeline_workers: int = 2  # Max number of threads per Serotyper instance

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Globals --------------------------------------------------------------------------------------------------------------
settings = Settings()
