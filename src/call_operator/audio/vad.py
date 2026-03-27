"""Voice Activity Detection (VAD) using Silero VAD."""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import torch

    from call_operator.adapters.base import AudioChunk

logger = logging.getLogger(__name__)

# Padding constants (number of chunks before/after speech)
_PRE_PADDING_CHUNKS = 3
_POST_PADDING_CHUNKS = 3
_STATS_LOG_INTERVAL = 100  # Log stats every N chunks

# Silero VAD requires exactly this many samples per chunk
_SILERO_SAMPLES_16K = 512  # 32ms at 16kHz
_SILERO_SAMPLES_8K = 256   # 32ms at 8kHz


class VoiceActivityDetector:
    """Detects speech in audio chunks using the Silero VAD model.

    The model is loaded once on initialization and reused for all
    subsequent calls to :meth:`detect`.
    """

    def __init__(self) -> None:
        import torch as _torch

        self._torch = _torch

        model, utils = _torch.hub.load(  # type: ignore[no-untyped-call]
            "snakers4/silero-vad",
            "silero_vad",
            trust_repo=True,
        )
        self._model = model
        # utils is (get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks)
        self._utils = utils
        self.reset()

    def _audio_to_tensor(self, chunk: AudioChunk) -> torch.Tensor:
        """Convert raw PCM 16-bit audio bytes to a float32 tensor in [-1.0, 1.0]."""
        import numpy as np

        samples = np.frombuffer(chunk.data, dtype=np.int16).astype(np.float32) / 32768.0
        return self._torch.from_numpy(samples)

    def detect(self, chunk: AudioChunk) -> float:
        """Return speech probability (0.0–1.0) for the given audio chunk.

        Silero VAD requires exactly 512 samples at 16kHz (or 256 at 8kHz).
        If the chunk has a different number of samples, it is resampled by
        zero-padding or truncation to the required length.
        """
        tensor = self._audio_to_tensor(chunk)
        expected = _SILERO_SAMPLES_16K if chunk.sample_rate == 16000 else _SILERO_SAMPLES_8K
        if tensor.shape[0] != expected:
            padded = self._torch.zeros(expected)
            length = min(tensor.shape[0], expected)
            padded[:length] = tensor[:length]
            tensor = padded
        confidence: float = self._model(tensor, chunk.sample_rate).item()
        return confidence

    def reset(self) -> None:
        """Reset the model's internal hidden state."""
        self._model.reset_states()


async def vad_stage(
    in_queue: asyncio.Queue[AudioChunk | None],
    out_queue: asyncio.Queue[AudioChunk | None],
    threshold: float = 0.5,
) -> None:
    """Pipeline stage: filter audio chunks, passing only speech segments.

    Uses Silero VAD to detect speech vs. silence.  Only speech chunks
    (with pre/post padding) are forwarded to the STT stage.

    Args:
        in_queue: Incoming audio chunks from the capture stage.
        out_queue: Outgoing speech-only chunks for the STT stage.
        threshold: Minimum speech probability to classify a chunk as speech.
    """
    logger.info("vad_stage started (threshold=%.2f)", threshold)

    detector = VoiceActivityDetector()

    # Ring buffer for pre-padding (keeps last N silence chunks)
    pre_buffer: deque[AudioChunk] = deque(maxlen=_PRE_PADDING_CHUNKS)

    in_speech = False
    post_padding_remaining = 0

    # Statistics
    chunks_processed = 0
    speech_chunks = 0

    try:
        while True:
            chunk = await in_queue.get()

            # Sentinel — propagate and exit
            if chunk is None:
                break

            probability = await asyncio.to_thread(detector.detect, chunk)
            chunks_processed += 1
            is_speech = probability >= threshold

            if is_speech:
                speech_chunks += 1

            if not in_speech:
                # Currently in SILENCE state
                if is_speech:
                    # Transition SILENCE → SPEECH: flush pre-padding buffer
                    in_speech = True
                    post_padding_remaining = _POST_PADDING_CHUNKS
                    for buffered in pre_buffer:
                        await out_queue.put(buffered)
                    pre_buffer.clear()
                    await out_queue.put(chunk)
                else:
                    # Still silence — just buffer for potential pre-padding
                    pre_buffer.append(chunk)
            else:
                # Currently in SPEECH state
                if is_speech:
                    # Still speech — forward directly
                    post_padding_remaining = _POST_PADDING_CHUNKS
                    await out_queue.put(chunk)
                else:
                    # Potential transition SPEECH → SILENCE
                    if post_padding_remaining > 0:
                        # Post-padding: forward a few more silence chunks
                        post_padding_remaining -= 1
                        await out_queue.put(chunk)
                    else:
                        # Post-padding exhausted — switch to silence
                        in_speech = False
                        detector.reset()
                        pre_buffer.append(chunk)

            # Periodic stats logging
            if chunks_processed % _STATS_LOG_INTERVAL == 0:
                ratio = speech_chunks / chunks_processed if chunks_processed else 0.0
                logger.info(
                    "VAD stats: %d chunks processed, %d speech, %.1f%% speech ratio",
                    chunks_processed,
                    speech_chunks,
                    ratio * 100,
                )
    finally:
        await out_queue.put(None)
        if chunks_processed:
            ratio = speech_chunks / chunks_processed
            logger.info(
                "vad_stage finished — %d chunks, %d speech (%.1f%%)",
                chunks_processed,
                speech_chunks,
                ratio * 100,
            )
        else:
            logger.info("vad_stage finished — no chunks processed")
