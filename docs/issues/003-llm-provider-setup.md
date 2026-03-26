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

- [x] Create `ConversationEngine` class in `llm/conversation.py`
  - [x] `__init__(self, settings: Settings)` — initialize LLM via `get_llm()`, load system prompt
  - [x] `async def process_transcript(self, text: str) -> str` — add user message, invoke LLM, return response
  - [x] `def reset(self)` — clear conversation history
  - [x] Manage conversation history as a list of LangChain messages (`SystemMessage`, `HumanMessage`, `AIMessage`)
  - [x] Truncate history when it exceeds `llm_max_history_messages` (keeps system message + last N)
- [x] Wire `ConversationEngine` into `conversation_stage()` — read from in_queue, call `process_transcript`, push to out_queue
- [x] Add `{bot_name}` placeholder to `SYSTEM_PROMPT` (use `bot_name` from Settings)
- [x] Pass `llm_temperature` through `get_llm()` to all provider constructors
- [x] Add `llm_max_history_messages` field to Settings (default: 20)
- [x] Add tests for `ConversationEngine` (mocked LLM):
  - [x] `process_transcript` returns a string response
  - [x] Conversation history accumulates messages
  - [x] `reset()` clears history
  - [x] System prompt includes bot_name
  - [x] History truncation respects max limit
  - [x] `conversation_stage()` reads from in_queue and writes to out_queue
  - [x] Stage continues processing after LLM errors

## Acceptance Criteria

- [x] `ConversationEngine` can be instantiated with mocked settings
- [x] `process_transcript("hello")` returns a non-empty string (mocked LLM)
- [x] Conversation history grows with each call
- [x] `reset()` clears history back to system prompt only
- [x] `conversation_stage()` reads from in_queue and writes to out_queue
- [x] `uv run ruff check src/ tests/` exits 0
- [x] `uv run mypy src/` exits 0 strict
- [x] All 29 tests pass

## Dependencies

- 001 — Project Setup (done)
- 002 — Config and Environment (done — `bot_name`, `llm_temperature`, `llm_max_history_messages`)

## Files Modified

- `src/call_operator/config.py` — added `llm_max_history_messages` field
- `src/call_operator/llm/conversation.py` — implemented `ConversationEngine` class + wired `conversation_stage()`
- `src/call_operator/llm/provider.py` — pass `temperature` to all provider constructors
- `src/call_operator/prompts/conversation.py` — added `{bot_name}` placeholder to `SYSTEM_PROMPT`
- `tests/test_conversation.py` — new file with 8 tests (engine + stage)
