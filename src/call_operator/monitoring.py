"""Pipeline monitoring — collects metrics from all stages."""

from __future__ import annotations

import threading
import time
from typing import Any


class PipelineMonitor:
    """Thread-safe metrics collector for the async pipeline.

    All ``record_*`` methods are non-blocking — they acquire a lock,
    update counters, and release.  The monitor never slows down the
    pipeline.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._start_time = time.monotonic()

        # Counters
        self._audio_chunks = 0
        self._speech_segments = 0
        self._transcriptions = 0
        self._responses = 0
        self._errors = 0

        # Recent items
        self._recent_transcripts: list[str] = []
        self._recent_responses: list[str] = []
        self._response_latencies: list[float] = []
        self._recent_errors: list[str] = []

        # Stage status
        self._stage_status: dict[str, str] = {}
        self._queue_depths: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Recording methods
    # ------------------------------------------------------------------

    def record_audio_chunk(self) -> None:
        """Record that an audio chunk was captured."""
        with self._lock:
            self._audio_chunks += 1

    def record_speech_segment(self) -> None:
        """Record that a speech segment was detected by VAD."""
        with self._lock:
            self._speech_segments += 1

    def record_transcription(self, text: str) -> None:
        """Record a transcription from STT."""
        with self._lock:
            self._transcriptions += 1
            self._recent_transcripts.append(text)
            if len(self._recent_transcripts) > 5:
                self._recent_transcripts.pop(0)

    def record_response(self, text: str, latency_ms: float) -> None:
        """Record an LLM response with its latency."""
        with self._lock:
            self._responses += 1
            self._response_latencies.append(latency_ms)
            self._recent_responses.append(text)
            if len(self._recent_responses) > 3:
                self._recent_responses.pop(0)

    def record_error(self, stage: str, error: str) -> None:
        """Record an error from any stage."""
        with self._lock:
            self._errors += 1
            entry = f"[{stage}] {error}"
            self._recent_errors.append(entry)
            if len(self._recent_errors) > 10:
                self._recent_errors.pop(0)

    def set_stage_status(self, stage: str, status: str) -> None:
        """Update the status of a pipeline stage."""
        with self._lock:
            self._stage_status[stage] = status

    def update_queue_depths(self, depths: dict[str, int]) -> None:
        """Update current queue depths for all inter-stage queues."""
        with self._lock:
            self._queue_depths = dict(depths)

    # ------------------------------------------------------------------
    # Status / summary
    # ------------------------------------------------------------------

    def get_status(self) -> dict[str, Any]:
        """Return a snapshot of current pipeline status for the dashboard."""
        with self._lock:
            uptime_s = time.monotonic() - self._start_time
            return {
                "uptime_s": uptime_s,
                "audio_chunks": self._audio_chunks,
                "speech_segments": self._speech_segments,
                "transcriptions": self._transcriptions,
                "responses": self._responses,
                "errors": self._errors,
                "recent_transcripts": list(self._recent_transcripts),
                "recent_responses": list(self._recent_responses),
                "recent_errors": list(self._recent_errors),
                "stage_status": dict(self._stage_status),
                "queue_depths": dict(self._queue_depths),
            }

    def get_summary(self) -> dict[str, Any]:
        """Return session summary for display on exit."""
        with self._lock:
            uptime_s = time.monotonic() - self._start_time
            avg_latency = (
                sum(self._response_latencies) / len(self._response_latencies)
                if self._response_latencies
                else 0.0
            )
            return {
                "uptime_s": uptime_s,
                "audio_chunks": self._audio_chunks,
                "speech_segments": self._speech_segments,
                "transcriptions": self._transcriptions,
                "responses": self._responses,
                "errors": self._errors,
                "avg_response_latency_ms": avg_latency,
            }
