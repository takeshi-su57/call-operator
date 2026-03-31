# [Feature]: Full conversation engine with LLM integration

## Description

Implement the complete `ConversationEngine` that serves as the agent's brain. It maintains conversation history, loads the system prompt, sends transcribed text to the LLM, manages the context window, and returns generated responses. Implement `conversation_stage()` that bridges the STT output queue to the TTS input queue through the LLM.

## Motivation

The conversation engine is the central intelligence of the meeting agent. It transforms raw transcriptions into contextual, useful responses. Proper conversation history management ensures the agent maintains context across a meeting. Context window management prevents token overflow in long meetings.

## Tasks

- [x] Flesh out `src/call_operator/llm/conversation.py` — replace stub with full implementation
- [x] Implement `ConversationEngine.__init__()`: initialize LLM via `get_llm()`, load system prompt, create empty message history
- [x] Implement `async process_transcript(text: str) -> str`:
  - Add user message (transcribed speech) to history
  - Build messages list: system prompt + conversation history
  - Call LLM via `llm.ainvoke(messages)`
  - Add assistant response to history
  - Return response text
- [x] Implement context window management:
  - Track token count (approximate via character count / 4)
  - When history exceeds `MAX_CONTEXT_TOKENS` (configurable, default 8000), summarize older messages and replace them
  - Always keep the system prompt and last N messages intact
- [x] Implement `reset()`: clear conversation history
- [x] Implement `get_history() -> list[dict]`: return conversation history for debugging
- [x] Update `src/call_operator/prompts/conversation.py`:
  - `SYSTEM_PROMPT`: template for meeting assistant behavior with `{bot_name}` placeholder
  - `SUMMARIZE_PROMPT`: template for summarizing older conversation history
- [x] Implement `conversation_stage(input_queue: asyncio.Queue[Transcript | None], output_queue: asyncio.Queue[str | None], settings: Settings) -> None`
  - Read `Transcript` from input queue (only process `is_final=True`)
  - Skip empty or noise-only transcripts
  - Pass text to `engine.process_transcript()`
  - Put response text on output queue
  - Handle end-of-stream sentinel (`None` propagation)
- [x] Add debouncing: wait briefly for additional transcript chunks before responding (avoid responding to partial sentences)

## Acceptance Criteria

- [x] `ConversationEngine` initializes with the configured LLM provider
- [x] `process_transcript()` sends messages to LLM and returns response text
- [x] Conversation history accumulates across multiple calls
- [x] Context window management prevents token overflow
- [x] `conversation_stage()` correctly bridges transcript queue to text output queue
- [x] Only final transcripts are processed (interim results are skipped)
- [x] System prompt includes `{bot_name}` and meeting-relevant instructions
- [x] `reset()` clears all history
- [x] All files pass `ruff check` and `mypy --strict`

## Implementation Notes

### Context window summarization

When `_estimate_tokens()` (char count / 4) exceeds `LLM_MAX_CONTEXT_TOKENS` (default 8000):
1. Non-system messages are split at the midpoint
2. Older half is serialized as "Role: content" lines
3. A separate LLM call with `SUMMARIZE_PROMPT` produces a concise summary
4. Older messages are replaced with a single `SystemMessage("Summary of earlier conversation:\n...")`
5. Result: `[system_prompt, summary_msg, *newer_messages]`

Simple truncation (`_truncate_history`, keeps system + last N messages) runs first as a fast guard.

### Debouncing

After receiving a final transcript, `conversation_stage` uses `asyncio.wait_for(in_queue.get(), timeout=debounce_s)` to collect additional transcripts within the debounce window (`CONVERSATION_DEBOUNCE_MS`, default 500ms). Collected texts are concatenated with spaces. If a sentinel arrives during debounce, accumulated text is processed before shutdown.

### LLM call logging

Per project logging rules: latency (ms), token usage (input/output/total from `response.usage_metadata`), and model name logged at INFO. Input/output text logged at DEBUG (truncated to 80 chars).

### New config settings

| Setting | Default | Description |
|---------|---------|-------------|
| `LLM_MAX_CONTEXT_TOKENS` | 8000 | Approx token limit before summarization triggers |
| `CONVERSATION_DEBOUNCE_MS` | 500 | Wait time (ms) to collect more speech before responding |

### Testing

- **Unit tests** (`tests/test_conversation.py`): 14 tests covering engine + stage behavior
- Engine: process_transcript, history accumulation, reset, bot_name, truncation, ainvoke, get_history, summarization
- Stage: queue bridging, error recovery, sentinel propagation, is_final filtering, empty filtering, debounce combining

## Dependencies

- 003 — LLM Provider Setup (`get_llm()` factory and provider configuration)
- 006 — STT Local (`Transcript` dataclass for input type)

## Files Created/Modified

- `src/call_operator/llm/conversation.py` — full engine rewrite with summarization, logging, debounce
- `src/call_operator/llm/__init__.py` — added exports
- `src/call_operator/prompts/conversation.py` — added `SUMMARIZE_PROMPT`
- `src/call_operator/config.py` — added `llm_max_context_tokens`, `conversation_debounce_ms`
- `.env.example` — added new env vars
- `tests/conftest.py` — added new settings to `mock_settings`
- `tests/test_conversation.py` — expanded from 8 to 14 tests
