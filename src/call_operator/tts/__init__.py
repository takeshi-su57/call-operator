"""Text-to-Speech providers and pipeline stage."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from call_operator.tts.base import TTSProvider, get_tts

if TYPE_CHECKING:
    import asyncio

    from call_operator.adapters.base import AudioChunk

logger = logging.getLogger(__name__)

__all__ = ["TTSProvider", "get_tts", "tts_stage"]


async def tts_stage(
    in_queue: asyncio.Queue[str | None],
    out_queue: asyncio.Queue[AudioChunk | None],
    provider: TTSProvider,
) -> None:
    """Pipeline stage: synthesize text into audio chunks.

    Reads :class:`str` from *in_queue*, passes each to
    *provider.synthesize()*, and writes :class:`AudioChunk` results to
    *out_queue*.  At end-of-stream (``None`` sentinel) the stage shuts
    down the provider and forwards the sentinel.
    """
    logger.info("tts_stage started")
    await provider.start()

    texts_processed = 0

    try:
        while True:
            text = await in_queue.get()

            if text is None:
                break

            texts_processed += 1
            try:
                chunk = await provider.synthesize(text)
                await out_queue.put(chunk)
            except Exception:  # noqa: BLE001
                logger.exception("tts_stage: synthesis failed, skipping")
    finally:
        await provider.stop()
        await out_queue.put(None)
        logger.info("tts_stage finished — %d texts synthesized", texts_processed)
