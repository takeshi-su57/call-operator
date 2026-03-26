"""LangChain LLM factory — returns the configured chat model."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from call_operator.config import Settings

logger = logging.getLogger(__name__)


def get_llm(settings: Settings) -> BaseChatModel:
    """Return a LangChain chat model based on the configured provider.

    Supports: openai, anthropic, google, openrouter. Provider-specific packages
    are imported lazily to avoid requiring all SDKs.
    """
    provider = settings.llm_provider
    model = settings.llm_model

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            api_key=settings.openai_api_key,  # type: ignore[arg-type]
            temperature=settings.llm_temperature,
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(  # type: ignore[call-arg]
            model_name=model,
            api_key=settings.anthropic_api_key,  # type: ignore[arg-type]
            temperature=settings.llm_temperature,
        )
    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=settings.google_api_key,
            temperature=settings.llm_temperature,
        )
    elif provider == "openrouter":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            api_key=settings.openrouter_api_key,  # type: ignore[arg-type]
            base_url="https://openrouter.ai/api/v1",
            temperature=settings.llm_temperature,
        )
    else:
        msg = f"Unknown LLM provider: {provider}"
        raise ValueError(msg)
