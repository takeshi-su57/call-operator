# Testing Rules

## Current State

Tests are minimal stubs. This document establishes standards as tests are added.

## Testing Strategy

| Layer | Target | Tool | Priority |
|-------|--------|------|----------|
| Unit | Config (`config.py`) | pytest | High |
| Unit | Audio models + data types | pytest | High |
| Unit | STT providers (`stt/*.py`) | pytest (mocked APIs) | High |
| Unit | TTS providers (`tts/*.py`) | pytest (mocked APIs) | High |
| Unit | LLM provider (`llm/provider.py`) | pytest (mocked) | Medium |
| Unit | Conversation engine (`llm/conversation.py`) | pytest (mocked LLM) | Medium |
| Integration | Pipeline stages (`pipeline.py`) | pytest-asyncio | Medium |
| Integration | Adapter (Google Meet) | pytest-asyncio (mocked browser) | Medium |
| E2E | Full pipeline with real audio | pytest-asyncio | Low |

## File Conventions

- Tests live in `tests/` directory
- Naming: `test_<module>.py` (e.g., `test_vad.py`, `test_whisper_local.py`)
- Shared fixtures in `tests/conftest.py`
- Test naming:
  ```python
  class TestWhisperLocal:
      async def test_transcribes_speech_audio(self) -> None: ...
      async def test_returns_empty_for_silence(self) -> None: ...
  ```

## What to Test First (Priority Order)

1. **`config.py`** — Settings load from env vars correctly
2. **`stt/base.py`, `tts/base.py`** — Provider interfaces and factory functions
3. **`llm/provider.py`** — Factory returns correct LangChain model type
4. **`audio/vad.py`** — VAD detects speech vs. silence
5. **`llm/conversation.py`** — Conversation history management
6. **`pipeline.py`** — Pipeline assembly, stage wiring, graceful shutdown

## Mocking Patterns

### Mock LLM calls
```python
from unittest.mock import patch, MagicMock

@patch("call_operator.llm.provider.get_llm")
def test_conversation_response(mock_get_llm):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value.content = "I understand, let me help with that."
    mock_get_llm.return_value = mock_llm
    # ... call conversation engine
```

### Mock STT provider
```python
from unittest.mock import AsyncMock, patch

@patch("call_operator.stt.whisper_local.WhisperLocalSTT")
async def test_stt_transcription(mock_stt_class):
    mock_stt = AsyncMock()
    mock_stt.transcribe_stream.return_value = async_iter([
        Transcript(text="Hello everyone", speaker=None)
    ])
    mock_stt_class.return_value = mock_stt
    # ... test pipeline stage
```

### Mock Playwright browser (adapter tests)
```python
from unittest.mock import AsyncMock, patch

@patch("call_operator.adapters.google_meet.async_playwright")
async def test_google_meet_join(mock_playwright):
    mock_page = AsyncMock()
    mock_browser = AsyncMock()
    mock_browser.new_page.return_value = mock_page
    mock_playwright.return_value.__aenter__.return_value.chromium.launch.return_value = mock_browser
    # ... test adapter join logic
```

### Mock audio stream
```python
import numpy as np
from call_operator.audio.capture import AudioChunk

def make_audio_chunk(duration_ms: int = 30, sample_rate: int = 16000) -> AudioChunk:
    samples = int(sample_rate * duration_ms / 1000)
    data = np.random.randint(-32768, 32767, size=samples, dtype=np.int16).tobytes()
    return AudioChunk(data=data, sample_rate=sample_rate)
```

### Mock environment variables
```python
@patch.dict("os.environ", {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"})
def test_config_loads():
    settings = Settings()
    assert settings.llm_provider == "openai"
```

## Fixtures (in conftest.py)

- `sample_audio_chunk` — PCM audio data for testing
- `sample_transcript` — `Transcript` object with test text
- `mock_settings` — `Settings` with test configuration

## Coverage Targets

- **Config + models:** 100% (constructors, defaults, validation)
- **Providers (STT/TTS/LLM):** 90%+ (with mocked external APIs)
- **Audio processing (VAD):** 80%+ (with sample audio data)
- **Pipeline:** 80%+ (stage wiring, queue flow, shutdown)
- **Adapters:** 70%+ (mocked browser interactions)

## Rules

- Test the public interface, not implementation details
- Each test should have a single assertion focus
- Use descriptive test names that explain expected behavior
- Always mock external I/O (LLM calls, browser, STT/TTS APIs, audio devices)
- Do not test LLM output quality — test that the conversation engine correctly processes responses
- Do not snapshot test LLM responses — they are non-deterministic
- Use `pytest-asyncio` for all async tests
- Use `pytest.mark.asyncio` decorator on async test functions
