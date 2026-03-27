"""Audio stream capture from meeting adapter."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from call_operator.adapters.base import AudioChunk, MeetingAdapter

if TYPE_CHECKING:
    import asyncio

logger = logging.getLogger(__name__)


async def capture_stage(
    adapter: MeetingAdapter,
    output_queue: asyncio.Queue[AudioChunk | None],
) -> None:
    """Pipeline stage: capture audio from the meeting adapter and push to queue.

    Reads raw PCM audio from the adapter in a loop, wraps each read into an
    :class:`AudioChunk`, and places it on *output_queue*.  When the adapter
    signals end-of-stream (returns ``None``), a ``None`` sentinel is placed on
    the queue and the stage exits.

    Args:
        adapter: The meeting adapter to read audio from.
        output_queue: Bounded async queue for downstream stages.
    """
    logger.info("capture_stage started")
    try:
        while True:
            try:
                raw = await adapter.read_audio()
            except Exception:
                logger.exception("Error reading audio from adapter")
                if not adapter.is_connected():
                    logger.warning("Adapter disconnected — ending capture")
                    break
                continue

            if raw is None:
                logger.info("Adapter signalled end-of-stream")
                break

            timestamp = time.monotonic()
            # duration = num_samples / sample_rate * 1000
            # num_samples = len(data) / (channels * bytes_per_sample)
            bytes_per_sample = 2  # 16-bit PCM
            num_samples = len(raw) / (adapter_channels(adapter) * bytes_per_sample)
            duration_ms = (num_samples / adapter_sample_rate(adapter)) * 1000

            chunk = AudioChunk(
                data=raw,
                sample_rate=adapter_sample_rate(adapter),
                channels=adapter_channels(adapter),
                timestamp=timestamp,
                duration_ms=duration_ms,
            )

            await output_queue.put(chunk)
            logger.debug(
                "Captured chunk: %d bytes, %.1f ms",
                len(raw),
                duration_ms,
            )
    finally:
        await output_queue.put(None)
        logger.info("capture_stage finished — sentinel sent")


def adapter_sample_rate(adapter: MeetingAdapter) -> int:
    """Return the sample rate for the adapter, defaulting to 16000."""
    return getattr(adapter, "sample_rate", 16000)


def adapter_channels(adapter: MeetingAdapter) -> int:
    """Return the channel count for the adapter, defaulting to 1."""
    return getattr(adapter, "channels", 1)
