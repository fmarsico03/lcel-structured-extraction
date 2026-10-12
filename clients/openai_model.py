from langchain_openai import ChatOpenAI
from schemas import LLMConfig, Provider
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


def build_openai(config: LLMConfig, api_key: str | None) -> ChatOpenAI:
    """OpenAI y NVIDIA NIM (API compatible con OpenAI)."""
    return ChatOpenAI(
        model=config.model,
        api_key=api_key,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        base_url=NVIDIA_BASE_URL if config.provider == Provider.NVIDIA else None,
    )
