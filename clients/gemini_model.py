from langchain_google_genai import ChatGoogleGenerativeAI
from schemas import LLMConfig


def build_gemini(config: LLMConfig, api_key: str | None) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=config.model,
        google_api_key=api_key,
        temperature=config.temperature,
        max_output_tokens=config.max_tokens,
    )
