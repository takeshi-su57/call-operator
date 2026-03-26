# [Feature]: LLM provider factory and conversation engine stub

## Description

Implement a LangChain-based LLM provider factory in `llm/provider.py` that returns a `BaseChatModel` based on the configured `LLM_PROVIDER` env var. Support OpenAI, Anthropic, and Google with lazy imports so only the selected provider's package is required. Create a stub conversation engine in `llm/conversation.py` and a system prompt template in `prompts/conversation.py`.

## Motivation

The conversation engine is the brain of the agent — it processes transcribed speech and generates responses. The provider factory abstracts away LLM vendor differences, making it trivial to switch providers. Lazy imports avoid requiring all three SDK packages when only one is used.

## Tasks

- [ ] Create `src/call_operator/llm/__init__.py`
- [ ] Create `src/call_operator/llm/provider.py` with `get_llm() -> BaseChatModel`
- [ ] Implement OpenAI provider: lazy import `langchain_openai.ChatOpenAI`, configure with `OPENAI_API_KEY` and `LLM_MODEL`
- [ ] Implement Anthropic provider: lazy import `langchain_anthropic.ChatAnthropic`, configure with `ANTHROPIC_API_KEY` and `LLM_MODEL`
- [ ] Implement Google provider: lazy import `langchain_google_genai.ChatGoogleGenerativeAI`, configure with `GOOGLE_API_KEY` and `LLM_MODEL`
- [ ] Raise clear error if provider is unknown or API key is missing
- [ ] Set default model names per provider (gpt-4o, claude-sonnet-4-20250514, gemini-2.0-flash) when `LLM_MODEL` is not set
- [ ] Create `src/call_operator/llm/conversation.py` with stub `ConversationEngine` class
- [ ] Stub methods: `__init__(self)`, `async process_transcript(self, text: str) -> str`, `reset(self)`
- [ ] Create `src/call_operator/prompts/__init__.py`
- [ ] Create `src/call_operator/prompts/conversation.py` with `SYSTEM_PROMPT` constant — template for meeting assistant behavior
- [ ] Add unit test in `tests/test_llm_provider.py` verifying factory returns correct types (mocked)

## Acceptance Criteria

- [ ] `get_llm()` returns a `ChatOpenAI` when `LLM_PROVIDER=openai`
- [ ] `get_llm()` returns a `ChatAnthropic` when `LLM_PROVIDER=anthropic`
- [ ] `get_llm()` returns a `ChatGoogleGenerativeAI` when `LLM_PROVIDER=google`
- [ ] Missing API key raises `ValueError` with a helpful message
- [ ] Unknown provider raises `ValueError`
- [ ] `ConversationEngine` can be instantiated and `process_transcript` returns a string
- [ ] `SYSTEM_PROMPT` contains `{bot_name}` placeholder
- [ ] All files pass `ruff check` and `mypy --strict`

## Dependencies

- 002 — Config and Environment (needs `get_settings()` for API keys and provider selection)

## Files to Create/Modify

- `src/call_operator/llm/__init__.py`
- `src/call_operator/llm/provider.py`
- `src/call_operator/llm/conversation.py`
- `src/call_operator/prompts/__init__.py`
- `src/call_operator/prompts/conversation.py`
- `tests/test_llm_provider.py`
