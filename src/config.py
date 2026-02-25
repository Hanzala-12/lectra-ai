"""
Configuration management with environment variables
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Environment
    ENV: str = "development"
    DEBUG: bool = True
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_KEY: Optional[str] = None
    
    # Model Configuration
    MODEL_CACHE_DIR: str = "./models"
    DEFAULT_WHISPER_MODEL: str = "base"
    MAX_FILE_SIZE_MB: int = 500
    ENABLE_GPU: bool = True
    
    # Processing
    MAX_WORKERS: int = 4
    ENABLE_DIARIZATION: bool = True
    
    # Cache
    REDIS_URL: str = "redis://localhost:6379/0"
    ENABLE_CACHING: bool = False
    
    # Monitoring
    ENABLE_METRICS: bool = True
    LOG_LEVEL: str = "INFO"
    
    # HuggingFace
    HF_TOKEN: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()
