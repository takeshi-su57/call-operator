# Security Rules

## API Keys

- LLM provider keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`) must come from environment variables
- STT/TTS provider keys (`DEEPGRAM_API_KEY`, `ELEVENLABS_API_KEY`) same rule — env vars only
- Use `config.py` (Pydantic Settings) to access all configuration — never read `os.environ` directly
- `.env` is in `.gitignore` — never commit it
- `.env.example` documents all variables without real values — keep it updated

## Audio Data Handling

- Meeting audio is processed in-memory and not persisted by default
- If audio recording is enabled (`RECORD_AUDIO=true`), recordings are saved to `data/` (git-ignored)
- Never commit audio recordings, conversation logs, or session data to git
- Never log transcript content at INFO level — use DEBUG only
- The `data/` directory must be in `.gitignore`

## Meeting Privacy

- The agent joins meetings as a visible participant — no hidden recording
- Conversation transcripts are local only — never sent to external services beyond the configured STT/LLM/TTS providers
- Meeting URLs may contain sensitive access tokens — never log full meeting URLs at INFO level

## Browser Automation Safety

- Playwright runs headless by default (`BROWSER_HEADLESS=true`)
- Google account credentials (if needed for Meet) come from env vars, never hardcoded
- Screenshots taken during automation should be saved to `data/` (git-ignored)

## Logging

- Use Python `logging` module with the standard library
- Never log API keys, passwords, or tokens at any level
- Never log full transcript text or meeting audio at INFO level
- Safe to log: meeting join/leave events, pipeline stage status, error messages, latency metrics

## What AI Must Never Generate

- Hardcoded API keys, tokens, passwords, or personal data
- `eval()`, `exec()`, or any dynamic code execution
- Code that records meetings without visible participant presence
- Disabled security checks or type checking (`# type: ignore` without justification)
- `subprocess.run` with `shell=True` and user-provided input
- Logging of sensitive data (API keys, transcript PII at INFO level)
- Code that exfiltrates meeting audio or transcripts to unauthorized endpoints
