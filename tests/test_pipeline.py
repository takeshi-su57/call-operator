"""Tests for pipeline orchestration."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from call_operator.config import Settings


class TestPipeline:
    @pytest.mark.asyncio
    @patch.dict("os.environ", {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test"})
    async def test_pipeline_runs_without_error(self) -> None:
        """Stub test — pipeline currently logs a warning and returns."""
        from call_operator.pipeline import run_pipeline

        settings = Settings()
        await run_pipeline(url="https://meet.google.com/test", settings=settings)
