"""Configuration management with environment-based settings."""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/nyaya_marga"
    database_echo: bool = False

    # Redis & Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Storage
    upload_base_path: str = "/tmp/nyaya_uploads"
    max_upload_size_mb: int = 50

    # NLP
    nlp_model_name: str = "law-ai/InLegalBERT"
    nlp_chunk_size: int = 400
    nlp_chunk_overlap: int = 50
    nlp_confidence_threshold: float = 0.75

    # API
    api_title: str = "Nyaya Marga - Intelligent Ingestion Engine"
    api_version: str = "0.1.0"
    debug: bool = False

    # Authentication
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_hours: int = 8

    # LLM / Ollama (Phase 3)
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1:8b"
    llm_temperature: float = 0.3
    embeddings_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Primary LLM: NVIDIA NIM API
    nvidia_nim_api_key: Optional[str] = None
    nvidia_nim_model: str = "meta/llama-3.1-8b-instruct"
    use_nvidia_nim: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure upload directory exists
        os.makedirs(self.upload_base_path, exist_ok=True)
        
        # Automatically fix standard PostgreSQL URLs to use the asyncpg driver
        if self.database_url:
            if self.database_url.startswith("postgresql://"):
                self.database_url = self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif self.database_url.startswith("postgres://"):
                self.database_url = self.database_url.replace("postgres://", "postgresql+asyncpg://", 1)


settings = Settings()
