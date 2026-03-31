"""Custom exception hierarchy for call-operator."""

from __future__ import annotations


class CallOperatorError(Exception):
    """Base exception for all call-operator errors."""


# -- Adapter errors -----------------------------------------------------------


class AdapterError(CallOperatorError):
    """Error originating from a meeting adapter."""


class AdapterDisconnectedError(AdapterError):
    """The adapter lost its connection to the meeting."""


class AdapterTimeoutError(AdapterError):
    """An adapter operation timed out."""


# -- STT errors ---------------------------------------------------------------


class STTError(CallOperatorError):
    """Error originating from a speech-to-text provider."""


class STTProviderUnavailableError(STTError):
    """The STT provider is unreachable after retries."""


# -- TTS errors ---------------------------------------------------------------


class TTSError(CallOperatorError):
    """Error originating from a text-to-speech provider."""


class TTSProviderUnavailableError(TTSError):
    """The TTS provider is unreachable after retries."""


# -- LLM errors ---------------------------------------------------------------


class LLMError(CallOperatorError):
    """Error originating from an LLM provider."""


class LLMProviderUnavailableError(LLMError):
    """The LLM provider is unreachable after retries."""


# -- Pipeline errors ----------------------------------------------------------


class PipelineError(CallOperatorError):
    """Error in pipeline orchestration."""


class PipelineShutdownError(PipelineError):
    """The pipeline is shutting down."""
