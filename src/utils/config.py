"""Application configuration"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-5-mini"
    
    # LangSmith Configuration
    langchain_tracing_v2: bool = True
    langchain_endpoint: str = "https://api.smith.langchain.com"
    langchain_api_key: Optional[str] = None
    langchain_project: str = "workflow-manager"
    
    # Database Configuration
    database_url: str = "sqlite:///./workflows.db"
    
    # Application Configuration
    app_env: str = "development"
    log_level: str = "INFO"
    
    # Workflow Configuration
    workflow_scripts_dir: str = "./workflow_scripts"
    logs_dir: str = "./logs"
    max_retry_count: int = 3
    step_timeout_seconds: int = 300
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

