# [Feature]: CLI enhancements and live monitoring dashboard

## Description

Enhance the Typer CLI with Rich-based live monitoring: a real-time status panel showing pipeline stage health, audio levels, transcription output, LLM responses, and session statistics. Add structured logging with configurable verbosity and a session summary printed on exit.

## Motivation

During development and production use, operators need visibility into what the agent is doing. Is it hearing audio? Is the STT working? What did the LLM respond? A live dashboard provides this at a glance without digging through log files. Good CLI UX also makes the tool more approachable.

## Tasks

- [x] Update `src/call_operator/main.py` with enhanced CLI:
  - `join` command: `--url` (required), `--headless`, `--log-level`, `--debug` flag
  - `status` command: Rich table showing config, providers, and API key availability
  - `--version` flag: prints `call-operator 0.1.0`
- [x] Implement Rich Live display panel showing:
  - Pipeline status: which stages are running/stopped/errored (green/yellow/red `●` indicators)
  - Latest transcription: last 3 transcribed utterances (from recent 5 tracked)
  - Latest response: last 3 LLM responses
  - Session stats: uptime, audio chunks, speech segments, transcriptions, responses, errors
  - Queue depths: current size of each inter-stage queue (audio, speech, transcript, response, playback)
- [ ] Audio meter: visual representation of input audio level — **deferred**: requires instrumenting capture/VAD stage to report RMS levels
- [x] Create `src/call_operator/monitoring.py` with `PipelineMonitor` class:
  - Thread-safe counters via `threading.Lock`
  - Tracks: audio chunks, speech segments, transcriptions, responses, errors
  - Stores recent transcripts (5), responses (3), errors (10)
  - Tracks response latencies for average calculation
  - Tracks stage status and queue depths
  - `get_status() -> dict` for dashboard display
  - `get_summary() -> dict` for session summary
- [x] Wire `PipelineMonitor` into `Pipeline`:
  - `Pipeline.monitor` attribute — public for CLI access
  - `_monitor_loop` background task: polls queue depths + task states every 500ms
  - `conversation_stage` accepts optional `monitor` parameter, records transcriptions, responses (with latency), and errors
  - Monitor errors recorded when `asyncio.gather` catches stage failures
  - Non-blocking: lock-based counters, separate async task
- [x] Implement session summary on exit:
  - Total runtime (Xm Ys)
  - Transcriptions and responses count
  - Errors encountered
  - Average response latency (ms)
- [ ] Audio statistics in session summary (speech time, silence ratio) — **deferred**: requires duration tracking in VAD stage
- [x] Configure Python `logging`:
  - Format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
  - File handler: writes to `data/session.log` (creates `data/` dir)
  - Console handler: only active in `--debug` mode (suppressed when Rich Live panel is active)
- [x] Add `--debug` flag that shows full log output instead of the Rich panel

## Acceptance Criteria

- [x] `python -m call_operator join --url <url>` starts with a live status panel
- [x] Status panel updates in real-time showing all pipeline stages
- [x] Transcriptions and responses are visible in the panel
- [x] Session summary prints on clean exit and on Ctrl+C
- [x] `--debug` flag switches to verbose log output
- [x] `--log-level` controls logging verbosity
- [x] Queue depths are visible for diagnosing backpressure
- [x] Monitor does not impact pipeline performance
- [x] All files pass `ruff check` and `mypy --strict`

## Implementation Notes

### PipelineMonitor architecture

```
Pipeline._monitor_loop (async, 500ms)     conversation_stage
  │                                          │
  ├─ update_queue_depths(5 queues)           ├─ record_transcription(text)
  ├─ set_stage_status(6 tasks)               ├─ record_response(text, latency)
  └─ (non-blocking, separate task)           └─ record_error(stage, msg)
                    │
                    ▼
              PipelineMonitor (thread-safe)
                    │
          ┌─────────┼──────────┐
          ▼         ▼          ▼
    get_status()  get_summary()  (CLI reads)
    (dashboard)   (exit print)
```

### Rich Live dashboard

Refreshes 2x/second via `rich.live.Live`. Shows a Rich `Table` with sections:
- **Uptime**: Xm Ys
- **Stages**: colored `●` per stage (green=running, yellow=stopped, red=error)
- **Queues**: depth of each inter-stage queue
- **Stats**: audio/speech/transcript/response/error counts
- **Transcripts**: last 3 utterances (80 char truncated)
- **Responses**: last 3 LLM responses (80 char truncated)

Disabled in `--debug` mode (verbose logs flow to console instead).

### Structured logging

- File handler always active: `data/session.log`
- Console handler only in `--debug` mode
- When Live panel is active, console is suppressed to avoid interleaving

### CLI commands

| Command | Description |
|---------|-------------|
| `join --url <url>` | Join meeting with Live dashboard |
| `join --url <url> --debug` | Join with verbose console logs |
| `join --url <url> --headless false` | Override headless mode |
| `join --url <url> --log-level DEBUG` | Override log level |
| `status` | Show config + API key availability |
| `--version` | Print version and exit |

### Deferred items

- **Audio meter** — needs RMS level reporting from capture/VAD stage
- **Audio stats in summary** (speech time, silence ratio) — needs duration tracking in VAD
- **`--provider` CLI overrides** — trivial to add but not specified precisely in the issue

### Testing

- **`tests/test_monitoring.py`** (NEW): 13 tests
  - Init state, all record methods, recent list limits, stage status, queue depths
  - Summary calculation, zero-latency edge case
  - Thread safety with 4 concurrent threads (2 writers, 2 readers)

## Dependencies

- 010 — Async Pipeline (pipeline must be running to monitor)

## Files Created/Modified

- `src/call_operator/monitoring.py` — NEW: `PipelineMonitor` class
- `src/call_operator/main.py` — enhanced CLI with `status`, `--version`, `--debug`, Rich Live dashboard, session summary, structured logging
- `src/call_operator/pipeline.py` — `Pipeline.monitor`, `_monitor_loop` background task, error recording
- `src/call_operator/llm/conversation.py` — `conversation_stage` accepts optional `monitor`, records transcripts/responses/errors
- `tests/test_monitoring.py` — NEW: 13 tests
