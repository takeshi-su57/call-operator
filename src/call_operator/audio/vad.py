"""Voice Activity Detection (VAD) using Silero VAD."""

from __future__ import annotations

import asyncio
import logging

from call_operator.adapters.base import AudioChunk

logger = logging.getLogger(__name__)


async def vad_stage(
    in_queue: asyncio.Queue[AudioChunk],
    out_queue: asyncio.Queue[AudioChunk],
    threshold: float = 0.5,
) -> None:
    """Pipeline stage: filter audio chunks, passing only speech segments.

    Uses Silero VAD to detect speech vs. silence. Only speech chunks
    are forwarded to the STT stage.
    """
    # TODO: Load Silero VAD model (torch.hub or silero_vad package)
    # TODO: Process audio chunks from in_queue
    # TODO: Run VAD inference on each chunk
    # TODO: Forward speech chunks (probability > threshold) to out_queue
    # TODO: Handle speech segment boundaries (start/end of utterance)
    logger.warning("vad_stage() is not yet implemented.")
