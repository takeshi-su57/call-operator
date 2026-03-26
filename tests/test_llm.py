"""Tests for LLM provider factory."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from call_operator.config import Settings


class TestLLMProvider:
    @patch.dict("os.environ", {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"})
    def test_returns_openai_model(self) -> None:
        from call_operator.llm.provider import get_llm

        settings = Settings()
        llm = get_llm(settings)
        assert llm is not None

    @patch.dict("os.environ", {"LLM_PROVIDER": "unknown"})
    def test_raises_on_unknown_provider(self) -> None:
        from call_operator.llm.provider import get_llm

        settings = Settings()
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_llm(settings)
