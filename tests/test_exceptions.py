"""Tests for custom exception hierarchy."""

from __future__ import annotations

from call_operator.exceptions import (
    AdapterDisconnectedError,
    AdapterError,
    AdapterTimeoutError,
    CallOperatorError,
    LLMError,
    LLMProviderUnavailableError,
    PipelineError,
    PipelineShutdownError,
    STTError,
    STTProviderUnavailableError,
    TTSError,
    TTSProviderUnavailableError,
)


class TestExceptionHierarchy:
    def test_base_is_exception(self) -> None:
        assert issubclass(CallOperatorError, Exception)

    def test_adapter_errors(self) -> None:
        assert issubclass(AdapterError, CallOperatorError)
        assert issubclass(AdapterDisconnectedError, AdapterError)
        assert issubclass(AdapterTimeoutError, AdapterError)

    def test_stt_errors(self) -> None:
        assert issubclass(STTError, CallOperatorError)
        assert issubclass(STTProviderUnavailableError, STTError)

    def test_tts_errors(self) -> None:
        assert issubclass(TTSError, CallOperatorError)
        assert issubclass(TTSProviderUnavailableError, TTSError)

    def test_llm_errors(self) -> None:
        assert issubclass(LLMError, CallOperatorError)
        assert issubclass(LLMProviderUnavailableError, LLMError)

    def test_pipeline_errors(self) -> None:
        assert issubclass(PipelineError, CallOperatorError)
        assert issubclass(PipelineShutdownError, PipelineError)

    def test_can_catch_broadly(self) -> None:
        """All specific errors are catchable via CallOperatorError."""
        errors = [
            AdapterDisconnectedError("test"),
            STTProviderUnavailableError("test"),
            TTSProviderUnavailableError("test"),
            LLMProviderUnavailableError("test"),
            PipelineShutdownError("test"),
        ]
        for err in errors:
            assert isinstance(err, CallOperatorError)

    def test_error_message_preserved(self) -> None:
        err = AdapterDisconnectedError("connection lost")
        assert str(err) == "connection lost"
