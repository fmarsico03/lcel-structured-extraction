from langchain_anthropic import ChatAnthropic
from schemas import LLMConfig


def build_anthropic(config: LLMConfig, api_key: str | None) -> ChatAnthropic:
    return ChatAnthropic(
        model=config.model,
        api_key=api_key,
        temperature=min(config.temperature, 1.0),
        max_tokens=config.max_tokens,
    )
