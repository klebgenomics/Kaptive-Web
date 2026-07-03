from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Kaptive Web"
    database_url: str = "sqlite+aiosqlite:///kaptive_web.db"
    
    # OAuth2 GitHub Settings
    github_client_id: str = ""
    github_client_secret: str = ""
    
    # OAuth2 ORCID Settings
    orcid_client_id: str = ""
    orcid_client_secret: str = ""
    
    # API Key Settings
    api_key_length: int = 32
    
    # Concurrency
    max_pipeline_workers: int = 2 # Max number of threads per Serotyper instance

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
