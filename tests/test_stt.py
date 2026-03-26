"""Tests for STT provider factory."""

from __future__ import annotations

import pytest

from call_operator.stt.base import Transcript, get_stt
from call_operator.stt.deepgram_cloud import DeepgramSTT
from call_operator.stt.whisper_local import WhisperLocalSTT


class TestSTTFactory:
    def test_returns_whisper_local(self) -> None:
        provider = get_stt("whisper_local", model="tiny")
        assert isinstance(provider, WhisperLocalSTT)

    def test_returns_deepgram(self) -> None:
        provider = get_stt("deepgram", api_key="test-key")
        assert isinstance(provider, DeepgramSTT)

    def test_raises_on_unknown_provider(self) -> None:
        with pytest.raises(ValueError, match="Unknown STT provider"):
            get_stt("unknown_provider")


class TestTranscript:
    def test_default_values(self) -> None:
        t = Transcript(text="hello")
        assert t.text == "hello"
        assert t.speaker is None
        assert t.confidence == 0.0
        assert t.is_final is True
