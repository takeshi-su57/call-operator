"""Manual integration test for DeepgramSTT with real audio.

Usage:
    uv run python scripts/test_deepgram_live.py

Requires:
    DEEPGRAM_API_KEY set in .env or environment.

What it does:
    1. Generates synthetic speech-like audio (a tone burst)
    2. Streams it through DeepgramSTT
    3. Prints any transcription results
    4. Tests the full lifecycle: start → transcribe → flush → stop

If Deepgram returns empty transcripts for synthetic audio (expected — it's not
real speech), the test still validates that:
    - WebSocket connects successfully
    - Audio is sent without errors
    - flush() and stop() complete cleanly
    - No crashes or hangs

For a real speech test, replace the synthetic audio with a WAV file read.
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
import struct
import sys

# Add src to path so we can import call_operator
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from call_operator.adapters.base import AudioChunk  # noqa: E402
from call_operator.config import get_settings  # noqa: E402
from call_operator.stt.deepgram_cloud import DeepgramSTT  # noqa: E402

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-7s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def generate_tone_chunk(
    frequency: float = 440.0,
    duration_ms: float = 100.0,
    sample_rate: int = 16000,
    amplitude: float = 0.5,
) -> AudioChunk:
    """Generate a PCM16 mono tone as an AudioChunk."""
    num_samples = int(sample_rate * duration_ms / 1000)
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        value = int(amplitude * 32767 * math.sin(2 * math.pi * frequency * t))
        samples.append(value)
    data = struct.pack(f"<{len(samples)}h", *samples)
    return AudioChunk(
        data=data,
        sample_rate=sample_rate,
        channels=1,
        timestamp=0.0,
        duration_ms=duration_ms,
    )


def load_wav_chunks(
    path: str, chunk_duration_ms: float = 100.0, sample_rate: int = 16000
) -> list[AudioChunk]:
    """Load a WAV file and split into AudioChunk objects.

    Expects 16-bit PCM mono WAV at the given sample_rate.
    If the WAV has a different sample rate, results may be incorrect.
    """
    import wave

    chunks: list[AudioChunk] = []
    with wave.open(path, "rb") as wf:
        assert wf.getnchannels() == 1, f"Expected mono, got {wf.getnchannels()} channels"
        assert wf.getsampwidth() == 2, f"Expected 16-bit, got {wf.getsampwidth() * 8}-bit"
        actual_rate = wf.getframerate()
        if actual_rate != sample_rate:
            logger.warning("WAV sample rate %d != expected %d", actual_rate, sample_rate)

        chunk_samples = int(actual_rate * chunk_duration_ms / 1000)
        while True:
            data = wf.readframes(chunk_samples)
            if not data:
                break
            chunks.append(
                AudioChunk(
                    data=data,
                    sample_rate=actual_rate,
                    channels=1,
                    timestamp=0.0,
                    duration_ms=chunk_duration_ms,
                )
            )
    return chunks


async def test_with_synthetic_audio(stt: DeepgramSTT) -> None:
    """Send synthetic tone bursts — validates connectivity, not transcription."""
    logger.info("=== Test 1: Synthetic audio (tone burst) ===")

    await stt.start()
    logger.info("WebSocket connected successfully")

    results: list[str] = []
    for _i in range(30):  # 30 x 100ms = 3 seconds of audio
        chunk = generate_tone_chunk(frequency=440.0, duration_ms=100.0)
        transcript = await stt.transcribe(chunk)
        if transcript is not None:
            logger.info("Got transcript: [final=%s] %r", transcript.is_final, transcript.text)
            results.append(transcript.text)
        # Small delay to simulate real-time streaming
        await asyncio.sleep(0.05)

    # Flush remaining
    final = await stt.flush()
    if final is not None:
        logger.info("Flush result: [final=%s] %r", final.is_final, final.text)
        results.append(final.text)

    if results:
        logger.info("Transcriptions received: %d", len(results))
    else:
        logger.info("No transcriptions (expected for synthetic audio — tone is not speech)")

    logger.info("Test 1 PASSED — no errors during streaming")


async def test_with_wav_file(stt: DeepgramSTT, wav_path: str) -> None:
    """Send real speech audio from a WAV file."""
    logger.info("=== Test 2: WAV file (%s) ===", wav_path)

    chunks = load_wav_chunks(wav_path)
    logger.info("Loaded %d chunks from %s", len(chunks), wav_path)

    await stt.start()

    results: list[str] = []
    for chunk in chunks:
        transcript = await stt.transcribe(chunk)
        if transcript is not None:
            logger.info("Got transcript: [final=%s] %r", transcript.is_final, transcript.text)
            results.append(transcript.text)
        await asyncio.sleep(0.05)

    final = await stt.flush()
    if final is not None:
        logger.info("Flush result: [final=%s] %r", final.is_final, final.text)
        results.append(final.text)

    if results:
        logger.info("Full transcription: %s", " ".join(results))
    else:
        logger.warning("No transcriptions received from WAV file")

    logger.info("Test 2 complete")


async def test_stop_and_restart(stt: DeepgramSTT) -> None:
    """Test stop → restart cycle."""
    logger.info("=== Test 3: Stop and restart ===")

    await stt.start()
    chunk = generate_tone_chunk(duration_ms=100.0)
    await stt.transcribe(chunk)
    await stt.stop()
    logger.info("Stopped successfully")

    # Restart
    await stt.start()
    await stt.transcribe(chunk)
    await stt.stop()
    logger.info("Restarted and stopped successfully")
    logger.info("Test 3 PASSED")


async def main() -> None:
    settings = get_settings()

    if not settings.deepgram_api_key:
        logger.error("DEEPGRAM_API_KEY not set. Add it to .env or environment.")
        sys.exit(1)

    key = settings.deepgram_api_key
    logger.info("Using Deepgram API key: %s...%s", key[:4], key[-4:])
    logger.info("STT model: %s, language: %s", settings.stt_model, settings.stt_language)

    stt = DeepgramSTT(
        api_key=settings.deepgram_api_key,
        model=settings.stt_model,
        language=settings.stt_language,
    )

    try:
        # Test 1: Basic connectivity with synthetic audio
        await test_with_synthetic_audio(stt)
        await stt.stop()

        # Test 2: WAV file (optional — skip if no file provided)
        wav_path = sys.argv[1] if len(sys.argv) > 1 else None
        if wav_path and os.path.exists(wav_path):
            await test_with_wav_file(stt, wav_path)
            await stt.stop()
        elif wav_path:
            logger.warning("WAV file not found: %s — skipping test 2", wav_path)
        else:
            logger.info("No WAV file provided — skipping test 2 (pass path as arg)")

        # Test 3: Stop and restart cycle
        await test_stop_and_restart(stt)

    except Exception:
        logger.exception("Test failed with error")
        sys.exit(1)
    finally:
        await stt.stop()

    logger.info("All tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
