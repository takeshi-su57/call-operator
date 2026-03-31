"""Tests for DeepgramSTT cloud speech-to-text provider."""

from __future__ import annotations

import asyncio
import contextlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from call_operator.adapters.base import AudioChunk
from call_operator.stt.base import Transcript
from call_operator.stt.deepgram_cloud import DeepgramSTT


def _make_chunk(duration_ms: float = 30.0, sample_rate: int = 16000) -> AudioChunk:
    """Create a test audio chunk."""
    num_samples = int(sample_rate * duration_ms / 1000)
    return AudioChunk(
        data=b"\x00" * (num_samples * 2),
        sample_rate=sample_rate,
        channels=1,
        timestamp=0.0,
        duration_ms=duration_ms,
    )


def _make_deepgram_result(
    text: str = "hello world",
    confidence: float = 0.95,
    is_final: bool = True,
) -> SimpleNamespace:
    """Create a fake Deepgram ListenV1Results-like object."""
    alternative = SimpleNamespace(transcript=text, confidence=confidence)
    channel = SimpleNamespace(alternatives=[alternative])
    return SimpleNamespace(channel=channel, is_final=is_final)


def _connected_stt() -> DeepgramSTT:
    """Create a DeepgramSTT with mocked connection state."""
    stt = DeepgramSTT(api_key="test-key")
    stt._ws = AsyncMock()
    stt._is_connected = True
    stt._result_queue = asyncio.Queue(maxsize=100)
    return stt


# ------------------------------------------------------------------
# Init
# ------------------------------------------------------------------


class TestDeepgramSTTInit:
    def test_raises_on_empty_api_key(self) -> None:
        with pytest.raises(ValueError, match="DEEPGRAM_API_KEY is required"):
            DeepgramSTT(api_key="")

    def test_raises_on_missing_api_key(self) -> None:
        with pytest.raises(ValueError, match="DEEPGRAM_API_KEY is required"):
            DeepgramSTT()

    def test_stores_config(self) -> None:
        stt = DeepgramSTT(api_key="my-key", model="nova-2", language="fr")
        assert stt.api_key == "my-key"
        assert stt.model == "nova-2"
        assert stt.language == "fr"

    def test_accepts_kwargs(self) -> None:
        stt = DeepgramSTT(api_key="my-key", extra="ignored")
        assert stt.api_key == "my-key"

    def test_default_values(self) -> None:
        stt = DeepgramSTT(api_key="key")
        assert stt.model == "nova-2"
        assert stt.language == "en"
        assert stt._is_connected is False
        assert stt._ws is None


# ------------------------------------------------------------------
# Start
# ------------------------------------------------------------------


class TestDeepgramSTTStart:
    @pytest.mark.asyncio
    async def test_start_is_idempotent(self) -> None:
        stt = _connected_stt()

        # start() should return early since _ws is set and _is_connected is True
        await stt.start()

        assert stt._is_connected is True

    @pytest.mark.asyncio
    async def test_start_opens_websocket(self) -> None:
        stt = DeepgramSTT(api_key="test-key")
        mock_ws = AsyncMock()
        mock_ws_cm = AsyncMock()
        mock_ws_cm.__aenter__ = AsyncMock(return_value=mock_ws)
        mock_ws_cm.__aexit__ = AsyncMock(return_value=False)

        mock_client = MagicMock()
        mock_client.listen.v1.connect.return_value = mock_ws_cm

        with patch(
            "deepgram.AsyncDeepgramClient",
            return_value=mock_client,
        ):
            await stt.start()

        assert stt._is_connected is True
        assert stt._ws is mock_ws
        assert stt._keepalive_task is not None
        assert stt._listener_task is not None

        mock_client.listen.v1.connect.assert_called_once_with(
            model="nova-2",
            language="en",
            smart_format="true",
            interim_results="true",
            endpointing="300",
            encoding="linear16",
            sample_rate="16000",
            channels="1",
        )

        # Cleanup
        stt._keepalive_task.cancel()
        stt._listener_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await stt._keepalive_task
        with contextlib.suppress(asyncio.CancelledError):
            await stt._listener_task


# ------------------------------------------------------------------
# Transcribe
# ------------------------------------------------------------------


class TestDeepgramSTTTranscribe:
    @pytest.mark.asyncio
    async def test_sends_audio_bytes(self) -> None:
        stt = _connected_stt()
        chunk = _make_chunk(duration_ms=30.0)

        await stt.transcribe(chunk)

        stt._ws.send_media.assert_called_once_with(chunk.data)

    @pytest.mark.asyncio
    async def test_returns_none_when_no_results(self) -> None:
        stt = _connected_stt()
        chunk = _make_chunk()

        result = await stt.transcribe(chunk)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_final_result_from_queue(self) -> None:
        stt = _connected_stt()
        transcript = Transcript(text="hello", confidence=0.9, is_final=True)
        stt._result_queue.put_nowait(transcript)

        chunk = _make_chunk()
        result = await stt.transcribe(chunk)

        assert result is not None
        assert result.text == "hello"
        assert result.is_final is True

    @pytest.mark.asyncio
    async def test_prefers_final_over_interim(self) -> None:
        stt = _connected_stt()
        interim = Transcript(text="hel", confidence=0.5, is_final=False)
        final = Transcript(text="hello world", confidence=0.95, is_final=True)
        stt._result_queue.put_nowait(interim)
        stt._result_queue.put_nowait(final)

        chunk = _make_chunk()
        result = await stt.transcribe(chunk)

        assert result is not None
        assert result.text == "hello world"
        assert result.is_final is True

    @pytest.mark.asyncio
    async def test_returns_interim_when_no_final(self) -> None:
        stt = _connected_stt()
        interim = Transcript(text="hel", confidence=0.5, is_final=False)
        stt._result_queue.put_nowait(interim)

        chunk = _make_chunk()
        result = await stt.transcribe(chunk)

        assert result is not None
        assert result.text == "hel"
        assert result.is_final is False

    @pytest.mark.asyncio
    async def test_auto_starts_if_not_started(self) -> None:
        stt = DeepgramSTT(api_key="test-key")

        with patch.object(stt, "start", new_callable=AsyncMock) as mock_start:

            async def fake_start() -> None:
                stt._ws = AsyncMock()
                stt._is_connected = True

            mock_start.side_effect = fake_start

            chunk = _make_chunk()
            await stt.transcribe(chunk)

        mock_start.assert_called_once()
        stt._ws.send_media.assert_called_once_with(chunk.data)

    @pytest.mark.asyncio
    async def test_returns_none_on_send_failure(self) -> None:
        stt = _connected_stt()
        stt._ws.send_media.side_effect = ConnectionError("broken")

        chunk = _make_chunk()
        result = await stt.transcribe(chunk)

        assert result is None
        assert stt._is_connected is False

    @pytest.mark.asyncio
    async def test_triggers_reconnect_when_disconnected(self) -> None:
        stt = _connected_stt()
        stt._is_connected = False

        with patch.object(stt, "_reconnect", new_callable=AsyncMock) as mock_reconnect:
            chunk = _make_chunk()
            await stt.transcribe(chunk)

        mock_reconnect.assert_called_once()


# ------------------------------------------------------------------
# Flush
# ------------------------------------------------------------------


class TestDeepgramSTTFlush:
    @pytest.mark.asyncio
    async def test_flush_calls_finalize(self) -> None:
        stt = _connected_stt()

        await stt.flush()

        stt._ws.send_finalize.assert_called_once()

    @pytest.mark.asyncio
    async def test_flush_returns_pending_result(self) -> None:
        stt = _connected_stt()
        transcript = Transcript(text="final words", is_final=True)
        stt._result_queue.put_nowait(transcript)

        result = await stt.flush()

        assert result is not None
        assert result.text == "final words"

    @pytest.mark.asyncio
    async def test_flush_returns_none_on_timeout(self) -> None:
        stt = _connected_stt()

        with patch("call_operator.stt.deepgram_cloud._FLUSH_TIMEOUT_S", 0.01):
            result = await stt.flush()

        assert result is None

    @pytest.mark.asyncio
    async def test_flush_returns_none_when_not_connected(self) -> None:
        stt = DeepgramSTT(api_key="test-key")

        result = await stt.flush()

        assert result is None


# ------------------------------------------------------------------
# Stop
# ------------------------------------------------------------------


class TestDeepgramSTTStop:
    @pytest.mark.asyncio
    async def test_stop_cancels_keepalive(self) -> None:
        stt = _connected_stt()
        stt._keepalive_task = asyncio.create_task(stt._keepalive_loop())

        await stt.stop()

        assert stt._keepalive_task is None

    @pytest.mark.asyncio
    async def test_stop_clears_state(self) -> None:
        stt = _connected_stt()
        stt._result_queue.put_nowait(Transcript(text="leftover"))

        await stt.stop()

        assert stt._ws is None
        assert stt._is_connected is False
        assert stt._result_queue.empty()

    @pytest.mark.asyncio
    async def test_stop_idempotent(self) -> None:
        stt = DeepgramSTT(api_key="test-key")

        await stt.stop()  # Should not raise


# ------------------------------------------------------------------
# Callbacks
# ------------------------------------------------------------------


class TestDeepgramSTTCallbacks:
    @pytest.mark.asyncio
    async def test_on_message_queues_final_result(self) -> None:
        stt = _connected_stt()
        result = _make_deepgram_result(text="hello world", is_final=True, confidence=0.95)

        await stt._on_message(result)

        assert not stt._result_queue.empty()
        transcript = stt._result_queue.get_nowait()
        assert transcript.text == "hello world"
        assert transcript.is_final is True
        assert transcript.confidence == 0.95

    @pytest.mark.asyncio
    async def test_on_message_queues_interim_result(self) -> None:
        stt = _connected_stt()
        result = _make_deepgram_result(text="hel", is_final=False)

        await stt._on_message(result)

        transcript = stt._result_queue.get_nowait()
        assert transcript.text == "hel"
        assert transcript.is_final is False

    @pytest.mark.asyncio
    async def test_on_message_skips_empty_text(self) -> None:
        stt = _connected_stt()
        result = _make_deepgram_result(text="", is_final=True)

        await stt._on_message(result)

        assert stt._result_queue.empty()

    @pytest.mark.asyncio
    async def test_on_message_skips_whitespace_text(self) -> None:
        stt = _connected_stt()
        result = _make_deepgram_result(text="   ", is_final=True)

        await stt._on_message(result)

        assert stt._result_queue.empty()

    @pytest.mark.asyncio
    async def test_on_message_skips_when_disconnected(self) -> None:
        stt = _connected_stt()
        stt._is_connected = False
        result = _make_deepgram_result(text="hello")

        await stt._on_message(result)

        assert stt._result_queue.empty()

    @pytest.mark.asyncio
    async def test_on_message_skips_non_transcript(self) -> None:
        stt = _connected_stt()
        # A metadata message without .channel
        msg = SimpleNamespace(type="Metadata", request_id="abc")

        await stt._on_message(msg)

        assert stt._result_queue.empty()


# ------------------------------------------------------------------
# Reconnect
# ------------------------------------------------------------------


class TestDeepgramSTTReconnect:
    @pytest.mark.asyncio
    async def test_reconnects_successfully(self) -> None:
        stt = _connected_stt()
        stt._is_connected = False

        with patch.object(stt, "start", new_callable=AsyncMock) as mock_start:
            await stt._reconnect()

        mock_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_gives_up_after_max_attempts(self) -> None:
        stt = _connected_stt()
        stt._is_connected = False

        with (
            patch.object(
                stt,
                "start",
                new_callable=AsyncMock,
                side_effect=ConnectionError("fail"),
            ) as mock_start,
            patch(
                "call_operator.stt.deepgram_cloud.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            await stt._reconnect()

        assert mock_start.call_count == 3

    @pytest.mark.asyncio
    async def test_reconnect_uses_backoff(self) -> None:
        stt = _connected_stt()
        stt._is_connected = False

        delays: list[float] = []

        async def capture_delay(d: float) -> None:
            delays.append(d)

        with (
            patch.object(
                stt,
                "start",
                new_callable=AsyncMock,
                side_effect=ConnectionError("fail"),
            ),
            patch(
                "call_operator.stt.deepgram_cloud.asyncio.sleep",
                side_effect=capture_delay,
            ),
        ):
            await stt._reconnect()

        # Delays use jitter (0.5-1.5x multiplier), so check ranges
        assert len(delays) == 3
        assert 0.25 <= delays[0] <= 0.75  # base 0.5 * jitter
        assert 0.5 <= delays[1] <= 1.5  # base 1.0 * jitter
        assert 1.0 <= delays[2] <= 3.0  # base 2.0 * jitter
