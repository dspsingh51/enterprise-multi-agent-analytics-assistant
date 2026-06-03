import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: str = "local"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # LLM Configuration
    LLM_PROVIDER: str = "google"  # Options: "google", "openai"
    LLM_MODEL: str = "gemini-2.5-flash"
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_BASE: Optional[str] = None

    # Conversation context window: number of messages (user+assistant) passed to the LLM.
    # 20 messages = 10 exchanges. Increase for deeper follow-ups, decrease to save tokens.
    CONVERSATION_HISTORY_LIMIT: int = 20

    # PostgreSQL Database
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres_secure_password"
    POSTGRES_DB: str = "analytics_assistant"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # Redis Cache & Memory
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Streamlit Config
    BACKEND_URL: str = "http://localhost:8000"

    # Directory for temporary file uploads
    UPLOAD_DIR: str = "uploads"
    # Directory for reports
    REPORTS_DIR: str = "reports"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate settings
settings = Settings()

# Ensure required directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.REPORTS_DIR, exist_ok=True)
