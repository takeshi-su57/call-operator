# [Feature]: Full conversation engine with LLM integration

## Description

Implement the complete `ConversationEngine` that serves as the agent's brain. It maintains conversation history, loads the system prompt, sends transcribed text to the LLM, manages the context window, and returns generated responses. Implement `conversation_stage()` that bridges the STT output queue to the TTS input queue through the LLM.

## Motivation

The conversation engine is the central intelligence of the meeting agent. It transforms raw transcriptions into contextual, useful responses. Proper conversation history management ensures the agent maintains context across a meeting. Context window management prevents token overflow in long meetings.

## Tasks

- [ ] Flesh out `src/call_operator/llm/conversation.py` — replace stub with full implementation
- [ ] Implement `ConversationEngine.__init__()`: initialize LLM via `get_llm()`, load system prompt, create empty message history
- [ ] Implement `async process_transcript(text: str) -> str`:
  - Add user message (transcribed speech) to history
  - Build messages list: system prompt + conversation history
  - Call LLM via `llm.ainvoke(messages)`
  - Add assistant response to history
  - Return response text
- [ ] Implement context window management:
  - Track token count (approximate via character count / 4)
  - When history exceeds `MAX_CONTEXT_TOKENS` (configurable, default 8000), summarize older messages and replace them
  - Always keep the system prompt and last N messages intact
- [ ] Implement `reset()`: clear conversation history
- [ ] Implement `get_history() -> list[dict]`: return conversation history for debugging
- [ ] Update `src/call_operator/prompts/conversation.py`:
  - `SYSTEM_PROMPT`: template for meeting assistant behavior with `{bot_name}` placeholder
  - `SUMMARIZE_PROMPT`: template for summarizing older conversation history
- [ ] Implement `conversation_stage(input_queue: asyncio.Queue[Transcript], output_queue: asyncio.Queue[str], engine: ConversationEngine) -> None`
  - Read `Transcript` from input queue (only process `is_final=True`)
  - Skip empty or noise-only transcripts
  - Pass text to `engine.process_transcript()`
  - Put response text on output queue
  - Handle end-of-stream sentinel
- [ ] Add debouncing: wait briefly for additional transcript chunks before responding (avoid responding to partial sentences)

## Acceptance Criteria

- [ ] `ConversationEngine` initializes with the configured LLM provider
- [ ] `process_transcript()` sends messages to LLM and returns response text
- [ ] Conversation history accumulates across multiple calls
- [ ] Context window management prevents token overflow
- [ ] `conversation_stage()` correctly bridges transcript queue to text output queue
- [ ] Only final transcripts are processed (interim results are skipped)
- [ ] System prompt includes `{bot_name}` and meeting-relevant instructions
- [ ] `reset()` clears all history
- [ ] All files pass `ruff check` and `mypy --strict`

## Dependencies

- 003 — LLM Provider Setup (`get_llm()` factory and provider configuration)
- 006 — STT Local (`Transcript` dataclass for input type)

## Files to Create/Modify

- `src/call_operator/llm/conversation.py`
- `src/call_operator/prompts/conversation.py`
