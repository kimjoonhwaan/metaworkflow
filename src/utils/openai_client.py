"""OpenAI client utility for RAG system"""

from openai import AsyncOpenAI
from .config import get_settings
from .logger import get_logger

logger = get_logger(__name__)

# Global OpenAI client instance
_openai_client = None

def get_openai_client() -> AsyncOpenAI:
    """Get global OpenAI client instance"""
    global _openai_client
    if _openai_client is None:
        settings = get_settings()
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client
