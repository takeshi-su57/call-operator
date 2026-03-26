# [Feature]: LLM provider factory and conversation engine stub

## Description

Implement the conversation engine that connects the LLM provider factory to the async pipeline. The provider factory (`get_llm()`) and prompt templates already exist from issue 001. This issue focuses on building the `ConversationEngine` class that manages conversation history, processes transcripts, and generates responses.

## Motivation

The conversation engine is the brain of the agent — it processes transcribed speech and generates responses. The pipeline stage (`conversation_stage`) needs a stateful engine to maintain conversation history across turns and manage the context window.

## Already Done (from issue 001)

- [x] `llm/provider.py` with `get_llm(settings) -> BaseChatModel`
- [x] OpenAI, Anthropic, Google, OpenRouter providers with lazy imports
- [x] Unknown provider raises `ValueError`
- [x] `llm/conversation.py` with `conversation_stage()` stub (pipeline stage signature)
- [x] `prompts/conversation.py` with `SYSTEM_PROMPT` and `RESPONSE_TEMPLATE`
- [x] `prompts/__init__.py`
- [x] `llm/__init__.py`
- [x] Tests: factory returns correct types, unknown provider raises

## Remaining Tasks

- [ ] Create `ConversationEngine` class in `llm/conversation.py`
  - [ ] `__init__(self, settings: Settings)` — initialize LLM via `get_llm()`, load system prompt
  - [ ] `async def process_transcript(self, text: str) -> str` — add user message, invoke LLM, return response
  - [ ] `def reset(self)` — clear conversation history
  - [ ] Manage conversation history as a list of LangChain messages
  - [ ] Truncate history when it exceeds context window limits
- [ ] Wire `ConversationEngine` into `conversation_stage()` — read from in_queue, call `process_transcript`, push to out_queue
- [ ] Add `{bot_name}` placeholder to `SYSTEM_PROMPT` (use `bot_name` from Settings)
- [ ] Add tests for `ConversationEngine` (mocked LLM):
  - [ ] `process_transcript` returns a string response
  - [ ] Conversation history accumulates messages
  - [ ] `reset()` clears history
  - [ ] System prompt is included in first LLM call

## Acceptance Criteria

- [ ] `ConversationEngine` can be instantiated with mocked settings
- [ ] `process_transcript("hello")` returns a non-empty string (mocked LLM)
- [ ] Conversation history grows with each call
- [ ] `reset()` clears history back to system prompt only
- [ ] `conversation_stage()` reads from in_queue and writes to out_queue
- [ ] `uv run ruff check src/ tests/` exits 0
- [ ] `uv run mypy src/` exits 0 strict
- [ ] All tests pass

## Dependencies

- 001 — Project Setup (done)
- 002 — Config and Environment (needs `bot_name`, `llm_temperature`)

## Files to Modify

- `src/call_operator/llm/conversation.py`
- `src/call_operator/prompts/conversation.py`
- `tests/test_llm.py` (or new `tests/test_conversation.py`)
