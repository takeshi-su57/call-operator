"""Cloud STT using Deepgram streaming WebSocket API (SDK v6)."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from typing import TYPE_CHECKING, Any

from call_operator.stt.base import STTProvider, Transcript

if TYPE_CHECKING:
    from call_operator.adapters.base import AudioChunk

logger = logging.getLogger(__name__)

_MAX_RECONNECT_ATTEMPTS = 3
_KEEPALIVE_INTERVAL_S = 8.0
_FLUSH_TIMEOUT_S = 2.0


class DeepgramSTT(STTProvider):
    """Deepgram streaming STT — low latency cloud transcription.

    Audio chunks are streamed to Deepgram over a persistent WebSocket
    connection. Transcription results arrive asynchronously via a
    background listener task and are bridged to the synchronous-per-chunk
    :meth:`transcribe` interface through an :class:`asyncio.Queue`.
    """

    def __init__(
        self,
        api_key: str = "",
        model: str = "nova-2",
        language: str = "en",
        **kwargs: str,
    ) -> None:
        if not api_key:
            msg = "DEEPGRAM_API_KEY is required when STT_PROVIDER=deepgram"
            raise ValueError(msg)

        self.api_key = api_key
        self.model = model
        self.language = language
        self._ws: Any = None
        self._ws_cm: Any = None
        self._result_queue: asyncio.Queue[Transcript] = asyncio.Queue(maxsize=100)
        self._is_connected: bool = False
        self._keepalive_task: asyncio.Task[None] | None = None
        self._listener_task: asyncio.Task[None] | None = None
        self._sample_rate: int = 16000

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Open WebSocket connection to Deepgram."""
        if self._ws is not None and self._is_connected:
            return

        from deepgram import AsyncDeepgramClient

        start_t = time.perf_counter()

        client = AsyncDeepgramClient(api_key=self.api_key)
        self._ws_cm = client.listen.v1.connect(
            model=self.model,
            language=self.language,
            smart_format="true",
            interim_results="true",
            endpointing="300",
            encoding="linear16",
            sample_rate=str(self._sample_rate),
            channels="1",
        )
        self._ws = await self._ws_cm.__aenter__()
        self._is_connected = True

        # Register message handler and start background listener.
        self._ws.on(self._get_event_type("MESSAGE"), self._on_message)
        self._listener_task = asyncio.create_task(self._listen_loop())
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())

        latency_ms = (time.perf_counter() - start_t) * 1000
        logger.info(
            "DeepgramSTT started (model=%s, language=%s, %.0fms)",
            self.model,
            self.language,
            latency_ms,
        )

    async def stop(self) -> None:
        """Close WebSocket connection and release resources."""
        if self._keepalive_task is not None:
            self._keepalive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._keepalive_task
            self._keepalive_task = None

        if self._listener_task is not None:
            self._listener_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listener_task
            self._listener_task = None

        if self._ws_cm is not None:
            try:
                await self._ws_cm.__aexit__(None, None, None)
            except Exception:  # noqa: BLE001
                logger.debug("Error closing Deepgram connection during stop", exc_info=True)

        self._ws = None
        self._ws_cm = None
        self._is_connected = False

        # Drain the result queue.
        while not self._result_queue.empty():
            with contextlib.suppress(asyncio.QueueEmpty):
                self._result_queue.get_nowait()

        logger.info("DeepgramSTT stopped")

    # ------------------------------------------------------------------
    # Transcription
    # ------------------------------------------------------------------

    async def transcribe(self, chunk: AudioChunk) -> Transcript | None:
        """Stream an audio chunk to Deepgram and return any available result."""
        if self._ws is None:
            await self.start()

        if not self._is_connected:
            await self._reconnect()
            if not self._is_connected:
                return None

        try:
            await self._ws.send_media(chunk.data)
        except Exception:  # noqa: BLE001
            logger.warning("Deepgram send failed, marking disconnected", exc_info=True)
            self._is_connected = False
            return None

        return self._drain_results()

    async def flush(self) -> Transcript | None:
        """Signal end-of-audio and wait for any pending final result."""
        if self._ws is None or not self._is_connected:
            return None

        try:
            await self._ws.send_finalize()
        except Exception:  # noqa: BLE001
            logger.debug("Error sending finalize to Deepgram", exc_info=True)
            return None

        try:
            result = await asyncio.wait_for(self._result_queue.get(), timeout=_FLUSH_TIMEOUT_S)
            # Also drain any additional results that arrived.
            while not self._result_queue.empty():
                candidate = self._result_queue.get_nowait()
                if candidate.is_final:
                    result = candidate
            return result
        except (TimeoutError, asyncio.QueueEmpty):
            return None

    # ------------------------------------------------------------------
    # Message handler
    # ------------------------------------------------------------------

    async def _on_message(self, message: Any) -> None:
        """Handle a parsed message from Deepgram's WebSocket."""
        if not self._is_connected:
            return

        # Only process transcript results (ListenV1Results).
        if not hasattr(message, "channel"):
            return

        try:
            alternative = message.channel.alternatives[0]
        except (AttributeError, IndexError):
            return

        text = alternative.transcript
        if not text or not text.strip():
            return

        is_final: bool = getattr(message, "is_final", True) or False
        confidence: float = getattr(alternative, "confidence", 0.0)

        transcript = Transcript(
            text=text.strip(),
            confidence=confidence,
            language=self.language,
            is_final=is_final,
            timestamp=time.time(),
        )

        logger.debug(
            "Deepgram transcript: final=%s, text=%.80s",
            is_final,
            transcript.text,
        )

        try:
            self._result_queue.put_nowait(transcript)
        except asyncio.QueueFull:
            logger.warning("Deepgram result queue full, dropping oldest result")
            with contextlib.suppress(asyncio.QueueEmpty):
                self._result_queue.get_nowait()
            self._result_queue.put_nowait(transcript)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_event_type(name: str) -> Any:
        """Get an EventType member by name (lazy import)."""
        from deepgram.core.events import EventType

        return getattr(EventType, name)

    def _drain_results(self) -> Transcript | None:
        """Drain the result queue, preferring final results over interim."""
        result: Transcript | None = None
        while not self._result_queue.empty():
            try:
                candidate = self._result_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            if candidate.is_final or result is None:
                result = candidate
        return result

    async def _listen_loop(self) -> None:
        """Run the WebSocket listener in the background."""
        try:
            if self._ws is not None:
                await self._ws.start_listening()
        except asyncio.CancelledError:
            return
        except Exception:  # noqa: BLE001
            logger.warning("Deepgram listener loop ended unexpectedly", exc_info=True)
        finally:
            self._is_connected = False

    async def _reconnect(self) -> None:
        """Attempt to reconnect with exponential backoff and jitter."""
        import random

        for attempt in range(_MAX_RECONNECT_ATTEMPTS):
            delay = min(2**attempt * 0.5, 5.0)
            delay *= random.uniform(0.5, 1.5)  # noqa: S311
            logger.warning(
                "Deepgram reconnecting (attempt %d/%d, delay=%.1fs)",
                attempt + 1,
                _MAX_RECONNECT_ATTEMPTS,
                delay,
            )
            await asyncio.sleep(delay)

            # Reset connection state before retrying.
            self._ws = None
            self._ws_cm = None

            try:
                await self.start()
                return
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Deepgram reconnect attempt %d failed",
                    attempt + 1,
                    exc_info=True,
                )

        logger.error("Deepgram reconnection failed after %d attempts", _MAX_RECONNECT_ATTEMPTS)

    async def _keepalive_loop(self) -> None:
        """Send periodic keepalive messages to prevent WebSocket timeout."""
        try:
            while True:
                await asyncio.sleep(_KEEPALIVE_INTERVAL_S)
                if self._is_connected and self._ws is not None:
                    try:
                        await self._ws.send_keep_alive()
                        logger.debug("Deepgram keepalive sent")
                    except Exception:  # noqa: BLE001
                        logger.warning("Deepgram keepalive failed", exc_info=True)
        except asyncio.CancelledError:
            return
