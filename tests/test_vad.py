"""Tests for Voice Activity Detection."""

from __future__ import annotations

from call_operator.adapters.base import AudioChunk


class TestAudioChunk:
    def test_default_values(self) -> None:
        chunk = AudioChunk(data=b"\x00" * 100)
        assert chunk.sample_rate == 16000
        assert chunk.channels == 1

    def test_custom_sample_rate(self) -> None:
        chunk = AudioChunk(data=b"\x00" * 100, sample_rate=44100)
        assert chunk.sample_rate == 44100
