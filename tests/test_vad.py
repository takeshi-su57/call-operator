"""Tests for Voice Activity Detection."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

from call_operator.adapters.base import AudioChunk
from call_operator.audio.vad import (
    _POST_PADDING_CHUNKS,
    _PRE_PADDING_CHUNKS,
    _STATS_LOG_INTERVAL,
    VoiceActivityDetector,
    vad_stage,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def _make_chunk(size: int = 960, sample_rate: int = 16000) -> AudioChunk:
    """Create a dummy AudioChunk with *size* bytes of silence."""
    return AudioChunk(data=b"\x00" * size, sample_rate=sample_rate, channels=1)


def _fake_model_factory(probabilities: list[float]) -> Callable[..., Any]:
    """Return a fake Silero model that yields *probabilities* in order."""
    call_count = 0

    class _FakeTensor:
        def __init__(self, value: float) -> None:
            self._value = value

        def item(self) -> float:
            return self._value

    def model(tensor: Any, sr: int) -> _FakeTensor:  # noqa: ARG001
        nonlocal call_count
        prob = probabilities[call_count % len(probabilities)]
        call_count += 1
        return _FakeTensor(prob)

    model.reset_states = MagicMock()  # type: ignore[attr-defined]
    return model


def _patch_torch_hub(probabilities: list[float]) -> Any:
    """Patch torch.hub.load to return a fake model with given probabilities."""
    fake_model = _fake_model_factory(probabilities)
    fake_utils = (None, None, None, None, None)

    mock_torch = MagicMock()
    mock_torch.hub.load.return_value = (fake_model, fake_utils)
    mock_torch.from_numpy = MagicMock(side_effect=lambda x: x)

    return patch.dict("sys.modules", {"torch": mock_torch, "numpy": _numpy_module()})


def _numpy_module() -> Any:
    """Return real numpy — no need to mock it."""
    import numpy as np

    return np


async def _collect_queue(queue: asyncio.Queue[AudioChunk | None]) -> list[AudioChunk]:
    """Drain all non-None items from the queue."""
    items: list[AudioChunk] = []
    while True:
        item = await asyncio.wait_for(queue.get(), timeout=2.0)
        if item is None:
            break
        items.append(item)
    return items


# ---------------------------------------------------------------------------
# VoiceActivityDetector unit tests
# ---------------------------------------------------------------------------


class TestVoiceActivityDetector:
    def test_loads_model(self) -> None:
        """torch.hub.load is called with the correct arguments."""
        with _patch_torch_hub([0.5]):
            import torch

            detector = VoiceActivityDetector()
            torch.hub.load.assert_called_once_with(
                "snakers4/silero-vad",
                "silero_vad",
                trust_repo=True,
            )
            assert detector is not None

    def test_detect_returns_float(self) -> None:
        with _patch_torch_hub([0.73]):
            detector = VoiceActivityDetector()
            chunk = _make_chunk()
            result = detector.detect(chunk)
            assert isinstance(result, float)
            assert 0.0 <= result <= 1.0
            assert result == pytest.approx(0.73)

    def test_detect_returns_low_for_silence(self) -> None:
        with _patch_torch_hub([0.02]):
            detector = VoiceActivityDetector()
            result = detector.detect(_make_chunk())
            assert result < 0.5

    def test_detect_returns_high_for_speech(self) -> None:
        with _patch_torch_hub([0.95]):
            detector = VoiceActivityDetector()
            result = detector.detect(_make_chunk())
            assert result >= 0.5

    def test_reset_calls_model_reset(self) -> None:
        with _patch_torch_hub([0.5]):
            detector = VoiceActivityDetector()
            # reset() is called in __init__; call it again explicitly
            detector.reset()
            # reset_states should have been called at least twice (init + explicit)
            assert detector._model.reset_states.call_count >= 2  # noqa: SLF001

    def test_audio_to_tensor_shape(self) -> None:
        """Tensor has correct length matching the number of PCM samples."""
        with _patch_torch_hub([0.5]):
            detector = VoiceActivityDetector()
            chunk = _make_chunk(size=960)  # 480 samples (960 bytes / 2 bytes per sample)
            tensor = detector._audio_to_tensor(chunk)  # noqa: SLF001
            assert len(tensor) == 480


# ---------------------------------------------------------------------------
# vad_stage integration tests
# ---------------------------------------------------------------------------


class TestVadStage:
    @pytest.mark.asyncio
    async def test_forwards_speech_chunks(self) -> None:
        """Chunks above the threshold are forwarded to the output queue."""
        with _patch_torch_hub([0.9]):
            in_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
            out_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()

            speech_chunk = _make_chunk()
            await in_q.put(speech_chunk)
            await in_q.put(None)

            await vad_stage(in_q, out_q, threshold=0.5)

            items = await _collect_queue(out_q)
            assert len(items) >= 1
            assert speech_chunk in items

    @pytest.mark.asyncio
    async def test_drops_silence_chunks(self) -> None:
        """Chunks below the threshold are not forwarded."""
        with _patch_torch_hub([0.1]):
            in_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
            out_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()

            for _ in range(5):
                await in_q.put(_make_chunk())
            await in_q.put(None)

            await vad_stage(in_q, out_q, threshold=0.5)

            items = await _collect_queue(out_q)
            assert len(items) == 0

    @pytest.mark.asyncio
    async def test_propagates_sentinel(self) -> None:
        """A None sentinel is always forwarded to the output queue."""
        with _patch_torch_hub([0.1]):
            in_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
            out_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()

            await in_q.put(None)
            await vad_stage(in_q, out_q, threshold=0.5)

            sentinel = await asyncio.wait_for(out_q.get(), timeout=2.0)
            assert sentinel is None

    @pytest.mark.asyncio
    async def test_pre_padding(self) -> None:
        """Silence chunks before speech onset are included as pre-padding."""
        # Pattern: silence, silence, silence, SPEECH, sentinel
        probs = [0.1, 0.1, 0.1, 0.9]
        with _patch_torch_hub(probs):
            in_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
            out_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()

            chunks = [_make_chunk() for _ in range(4)]
            for c in chunks:
                await in_q.put(c)
            await in_q.put(None)

            await vad_stage(in_q, out_q, threshold=0.5)

            items = await _collect_queue(out_q)
            # Should include up to PRE_PADDING silence chunks + the speech chunk
            assert len(items) == min(_PRE_PADDING_CHUNKS, 3) + 1

    @pytest.mark.asyncio
    async def test_post_padding(self) -> None:
        """Silence chunks after speech offset are included as post-padding."""
        # Pattern: SPEECH, silence, silence, silence, silence, silence, sentinel
        probs = [0.9, 0.1, 0.1, 0.1, 0.1, 0.1]
        with _patch_torch_hub(probs):
            in_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
            out_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()

            chunks = [_make_chunk() for _ in range(6)]
            for c in chunks:
                await in_q.put(c)
            await in_q.put(None)

            await vad_stage(in_q, out_q, threshold=0.5)

            items = await _collect_queue(out_q)
            # 1 speech + POST_PADDING silence chunks
            assert len(items) == 1 + _POST_PADDING_CHUNKS

    @pytest.mark.asyncio
    async def test_all_silence_only_sentinel(self) -> None:
        """If all chunks are silence, only the sentinel comes through."""
        with _patch_torch_hub([0.05]):
            in_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
            out_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()

            for _ in range(10):
                await in_q.put(_make_chunk())
            await in_q.put(None)

            await vad_stage(in_q, out_q, threshold=0.5)

            items = await _collect_queue(out_q)
            assert len(items) == 0

    @pytest.mark.asyncio
    async def test_continuous_speech(self) -> None:
        """All consecutive speech chunks are forwarded."""
        with _patch_torch_hub([0.9]):
            in_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
            out_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()

            for _ in range(5):
                await in_q.put(_make_chunk())
            await in_q.put(None)

            await vad_stage(in_q, out_q, threshold=0.5)

            items = await _collect_queue(out_q)
            assert len(items) == 5

    @pytest.mark.asyncio
    async def test_stats_logging(self) -> None:
        """VAD statistics are logged at the configured interval."""
        n = _STATS_LOG_INTERVAL + 1
        with _patch_torch_hub([0.9]):
            in_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
            out_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()

            for _ in range(n):
                await in_q.put(_make_chunk())
            await in_q.put(None)

            with patch("call_operator.audio.vad.logger") as mock_logger:
                await vad_stage(in_q, out_q, threshold=0.5)

                # Should have at least one stats log call containing "VAD stats"
                info_calls = [
                    str(c) for c in mock_logger.info.call_args_list if "VAD stats" in str(c)
                ]
                assert len(info_calls) >= 1

            # Drain output
            await _collect_queue(out_q)
