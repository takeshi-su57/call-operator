"""Audio stream capture from browser."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncio

    from call_operator.adapters.base import AudioChunk, MeetingAdapter

logger = logging.getLogger(__name__)


async def capture_stage(
    adapter: MeetingAdapter,
    out_queue: asyncio.Queue[AudioChunk],
) -> None:
    """Pipeline stage: capture audio from the meeting adapter and push to queue.

    Runs continuously until the adapter stops yielding audio or is cancelled.
    """
    # TODO: Stream audio from adapter.capture_audio()
    # TODO: Push AudioChunk objects to out_queue
    # TODO: Handle backpressure (bounded queue)
    logger.warning("capture_stage() is not yet implemented.")
