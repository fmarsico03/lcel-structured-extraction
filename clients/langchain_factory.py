from langchain_core.language_models.chat_models import BaseChatModel

from clients.anthropic_model import build_anthropic
from clients.gemini_model import build_gemini
from clients.openai_model import build_openai
from schemas import LLMConfig, Provider

_BUILDERS = {
    Provider.OPENAI: build_openai,
    Provider.NVIDIA: build_openai,
    Provider.ANTHROPIC: build_anthropic,
    Provider.GEMINI: build_gemini,
}


def get_chat_model(config: LLMConfig) -> BaseChatModel:
    """Devuelve un chat model de LangChain según el proveedor configurado."""
    api_key = config.api_key.get_secret_value() if config.api_key else None
    try:
        builder = _BUILDERS[config.provider]
    except KeyError:
        raise ValueError(f"Proveedor no soportado: {config.provider}")
    return builder(config, api_key)
