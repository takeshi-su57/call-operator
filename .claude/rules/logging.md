# Logging Rules

Standards for logging across the call-operator pipeline, with specific guidance for LLM calls and provider interactions.

## General

- Use Python `logging` module — `logger = logging.getLogger(__name__)` in every module
- Log level is configured via `LOG_LEVEL` env var (default `INFO`)
- Never log API keys, tokens, or passwords at any level
- Never log full transcript text or meeting audio at INFO level — use DEBUG
- Safe to log at INFO: stage lifecycle (started/finished), latency metrics, error summaries

## Pipeline Stage Logging

Every pipeline stage must log:

| Event | Level | What to include |
|-------|-------|-----------------|
| Stage started | INFO | Stage name, key config (e.g. threshold, model name) |
| Stage finished | INFO | Chunks/items processed count, summary stats |
| Item processed | DEBUG | Truncated content (first 80 chars max) |
| Error (recoverable) | WARNING | Error type, context, stage continues |
| Error (fatal) | ERROR | Full exception via `logger.exception()` |

Example from `vad_stage`:
```python
logger.info("vad_stage started (threshold=%.2f)", threshold)
logger.info("vad_stage finished — %d chunks, %d speech (%.1f%%)", ...)
```

## LLM Call Logging

Every LLM invocation must log:

### Before the call (DEBUG)
- History size (number of messages)
- Input text (truncated to 80 chars)

### After the call (INFO)
- **Latency** — wall-clock time in milliseconds
- **Token usage** — input tokens, output tokens, total (from response metadata when available)
- **Model name** — which model handled the request

### After the call (DEBUG)
- Response text (truncated to 80 chars)

### On error (ERROR)
- Full exception via `logger.exception()`
- Provider name and model for debugging

### Implementation pattern
```python
import time

logger.debug("LLM call: history=%d messages, input=%s", len(history), text[:80])

start = time.perf_counter()
response = await self._llm.ainvoke(messages)
latency_ms = (time.perf_counter() - start) * 1000

# Extract token usage from response metadata (LangChain standard)
usage = getattr(response, "usage_metadata", None)
if usage:
    logger.info(
        "LLM response: %.0fms, tokens=%d/%d/%d (in/out/total), model=%s",
        latency_ms, usage["input_tokens"], usage["output_tokens"],
        usage["total_tokens"], self._model_name,
    )
else:
    logger.info("LLM response: %.0fms, model=%s", latency_ms, self._model_name)

logger.debug("LLM output: %s", str(response.content)[:80])
```

## STT / TTS Provider Logging

- Log model loading time at INFO (e.g. "WhisperLocalSTT model loaded in 1200ms")
- Log transcription latency at INFO (time spent in `asyncio.to_thread`)
- Log audio buffer duration at DEBUG before each transcription
- Log TTS synthesis latency at INFO
- Never log raw audio bytes

## LangChain Callbacks (Optional)

For deeper observability, LangChain's callback system can be used:

- Use `LangChainTracer` or a custom `BaseCallbackHandler` for structured traces
- Callbacks are set per-call or globally — do NOT hardcode a tracing service
- If LangGraph is adopted in the future, use its built-in step logging via callbacks

## Anti-Patterns (Do NOT)

- Log full conversation history at INFO — use DEBUG, and truncate
- Log raw audio data or PCM bytes at any level
- Use `print()` instead of `logging`
- Log inside tight loops without rate-limiting (e.g. every audio chunk at INFO)
- Embed provider-specific logging in the pipeline stages — keep it in the provider
- Skip latency logging on LLM calls — this is critical for performance monitoring
