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

    Supports: openai, anthropic, google. Provider-specific packages
    are imported lazily to avoid requiring all SDKs.
    """
    provider = settings.llm_provider
    model = settings.llm_model

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model, api_key=settings.openai_api_key)  # type: ignore[arg-type]
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model, api_key=settings.anthropic_api_key)  # type: ignore[arg-type]
    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=model, google_api_key=settings.google_api_key)  # type: ignore[arg-type]
    else:
        msg = f"Unknown LLM provider: {provider}"
        raise ValueError(msg)
