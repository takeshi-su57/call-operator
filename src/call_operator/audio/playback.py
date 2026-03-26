"""Audio playback — sends synthesized speech back into the meeting."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncio

    from call_operator.adapters.base import AudioChunk, MeetingAdapter

logger = logging.getLogger(__name__)


async def playback_stage(
    in_queue: asyncio.Queue[AudioChunk],
    adapter: MeetingAdapter,
) -> None:
    """Pipeline stage: play audio chunks back into the meeting.

    Reads synthesized speech audio from the queue and sends it
    to the meeting adapter for playback.
    """
    # TODO: Read AudioChunk from in_queue
    # TODO: Send to adapter.play_audio()
    # TODO: Handle timing/pacing of audio playback
    logger.warning("playback_stage() is not yet implemented.")
