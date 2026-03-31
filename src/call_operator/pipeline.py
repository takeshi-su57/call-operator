"""Async pipeline orchestration — wires all stages together."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Any

from call_operator.monitoring import PipelineMonitor

if TYPE_CHECKING:
    from call_operator.adapters.base import AudioChunk, MeetingAdapter
    from call_operator.config import Settings
    from call_operator.stt.base import STTProvider, Transcript
    from call_operator.tts.base import TTSProvider

logger = logging.getLogger(__name__)

_SHUTDOWN_TIMEOUT_S = 5.0
_MONITOR_INTERVAL_S = 0.5


class Pipeline:
    """End-to-end async pipeline: capture → VAD → STT → LLM → TTS → playback.

    Each stage runs as an independent :class:`asyncio.Task`, connected by
    bounded queues that provide backpressure.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        qs = settings.pipeline_queue_size

        # Inter-stage queues
        self._audio_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue(maxsize=qs)
        self._speech_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue(maxsize=qs)
        self._transcript_q: asyncio.Queue[Transcript | None] = asyncio.Queue(maxsize=qs)
        self._response_q: asyncio.Queue[str | None] = asyncio.Queue(maxsize=qs)
        self._playback_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue(maxsize=qs)

        self._tasks: list[asyncio.Task[None]] = []
        self._running = False
        self._adapter: MeetingAdapter | None = None
        self._stt: STTProvider | None = None
        self._tts: TTSProvider | None = None
        self.monitor = PipelineMonitor()

    @property
    def is_running(self) -> bool:
        """Return whether the pipeline is currently running."""
        return self._running

    async def start(self, url: str) -> None:
        """Initialize providers and connect to the meeting."""
        s = self._settings

        # Adapter
        from call_operator.adapters.google_meet import GoogleMeetAdapter

        self._adapter = GoogleMeetAdapter(s)
        await self._adapter.connect(url)

        # STT provider
        from call_operator.stt.base import get_stt

        stt_kwargs: dict[str, str] = {
            "model": s.stt_model,
            "language": s.stt_language,
        }
        if s.stt_provider == "deepgram":
            stt_kwargs["api_key"] = s.deepgram_api_key
        self._stt = get_stt(s.stt_provider, **stt_kwargs)

        # TTS provider
        from call_operator.tts.base import get_tts

        tts_kwargs: dict[str, str] = {
            "voice": s.tts_voice,
            "speed": str(s.tts_speed),
        }
        if s.tts_provider == "openai":
            tts_kwargs["api_key"] = s.openai_api_key
        elif s.tts_provider == "elevenlabs":
            tts_kwargs["api_key"] = s.elevenlabs_api_key
        self._tts = get_tts(s.tts_provider, **tts_kwargs)

        logger.info(
            "Pipeline initialized (stt=%s, tts=%s, queue_size=%d)",
            s.stt_provider,
            s.tts_provider,
            s.pipeline_queue_size,
        )

    async def run(self) -> None:
        """Launch all pipeline stages and wait for completion."""
        if self._adapter is None or self._stt is None or self._tts is None:
            msg = "Pipeline.start() must be called before run()"
            raise RuntimeError(msg)

        self._running = True
        logger.info("Pipeline running")

        from call_operator.audio.capture import capture_stage
        from call_operator.audio.playback import playback_stage
        from call_operator.audio.vad import vad_stage
        from call_operator.llm.conversation import conversation_stage
        from call_operator.stt import stt_stage
        from call_operator.tts import tts_stage

        self._tasks = [
            asyncio.create_task(
                capture_stage(self._adapter, self._audio_q),
                name="capture",
            ),
            asyncio.create_task(
                vad_stage(self._audio_q, self._speech_q, self._settings.vad_threshold),
                name="vad",
            ),
            asyncio.create_task(
                stt_stage(self._speech_q, self._transcript_q, self._stt),
                name="stt",
            ),
            asyncio.create_task(
                conversation_stage(
                    self._transcript_q,
                    self._response_q,
                    self._settings,
                    monitor=self.monitor,
                ),
                name="conversation",
            ),
            asyncio.create_task(
                tts_stage(self._response_q, self._playback_q, self._tts),
                name="tts",
            ),
            asyncio.create_task(
                playback_stage(self._playback_q, self._adapter),
                name="playback",
            ),
        ]

        # Background monitor task
        monitor_task = asyncio.create_task(self._monitor_loop(), name="monitor")

        try:
            results: list[Any] = await asyncio.gather(*self._tasks, return_exceptions=True)
            for task, result in zip(self._tasks, results, strict=True):
                if isinstance(result, BaseException):
                    from call_operator.exceptions import AdapterError, CallOperatorError

                    self.monitor.record_error(task.get_name(), str(result))
                    if isinstance(result, AdapterError):
                        logger.error(
                            "Stage %s: adapter error — %s: %s",
                            task.get_name(),
                            type(result).__name__,
                            result,
                        )
                    elif isinstance(result, CallOperatorError):
                        logger.error(
                            "Stage %s: %s — %s",
                            task.get_name(),
                            type(result).__name__,
                            result,
                        )
                    else:
                        logger.error("Stage %s failed: %s", task.get_name(), result)
        finally:
            monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await monitor_task
            await self.stop()

    async def stop(self) -> None:
        """Gracefully shut down the pipeline."""
        if not self._running:
            return

        self._running = False
        logger.info("Pipeline shutting down")

        # Inject sentinel to start the cascade
        with contextlib.suppress(asyncio.QueueFull):
            self._audio_q.put_nowait(None)

        # Wait for tasks to finish gracefully
        if self._tasks:
            _, pending = await asyncio.wait(self._tasks, timeout=_SHUTDOWN_TIMEOUT_S)
            for task in pending:
                logger.warning("Cancelling task %s (did not stop in time)", task.get_name())
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)

        self._tasks.clear()

        # Disconnect adapter
        if self._adapter is not None:
            try:
                await self._adapter.disconnect()
            except Exception:  # noqa: BLE001
                logger.exception("Error disconnecting adapter")

        logger.info("Pipeline stopped")

    async def _monitor_loop(self) -> None:
        """Background task that periodically samples queue depths and task states."""
        try:
            while self._running:
                self.monitor.update_queue_depths(
                    {
                        "audio": self._audio_q.qsize(),
                        "speech": self._speech_q.qsize(),
                        "transcript": self._transcript_q.qsize(),
                        "response": self._response_q.qsize(),
                        "playback": self._playback_q.qsize(),
                    }
                )
                for task in self._tasks:
                    name = task.get_name()
                    if task.done():
                        exc = task.exception() if not task.cancelled() else None
                        status = "error" if exc else "stopped"
                    else:
                        status = "running"
                    self.monitor.set_stage_status(name, status)
                await asyncio.sleep(_MONITOR_INTERVAL_S)
        except asyncio.CancelledError:
            return
