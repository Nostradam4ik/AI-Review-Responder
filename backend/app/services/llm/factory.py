from app.config import settings
from .base import LLMProvider
from .groq_provider import GroqProvider


def get_llm_provider() -> LLMProvider:
    providers = {
        "groq": lambda: GroqProvider(settings.GROQ_API_KEY),
    }
    return providers[settings.LLM_PROVIDER]()
