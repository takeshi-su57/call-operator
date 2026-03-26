# [Feature]: CLI enhancements and live monitoring dashboard

## Description

Enhance the Typer CLI with Rich-based live monitoring: a real-time status panel showing pipeline stage health, audio levels, transcription output, LLM responses, and session statistics. Add structured logging with configurable verbosity and a session summary printed on exit.

## Motivation

During development and production use, operators need visibility into what the agent is doing. Is it hearing audio? Is the STT working? What did the LLM respond? A live dashboard provides this at a glance without digging through log files. Good CLI UX also makes the tool more approachable.

## Tasks

- [ ] Update `src/call_operator/main.py` with enhanced CLI:
  - `run` command: `--meeting-url` (required), `--headless/--no-headless`, `--log-level`, `--provider` overrides
  - `status` command: show current config and provider availability
  - `--version` flag
- [ ] Implement Rich Live display panel showing:
  - Pipeline status: which stages are running/stopped/errored (green/yellow/red indicators)
  - Audio meter: visual representation of input audio level
  - Latest transcription: last 5 transcribed utterances
  - Latest response: last 3 LLM responses
  - Session stats: uptime, messages processed, errors count
  - Queue depths: current size of each inter-stage queue
- [ ] Create `src/call_operator/monitoring.py` with `PipelineMonitor` class:
  - Collects metrics from all pipeline stages via callbacks
  - Tracks: audio chunks processed, speech segments detected, transcriptions, responses, errors
  - Provides `get_status() -> dict` for the display panel
  - Thread-safe counters
- [ ] Wire `PipelineMonitor` into `Pipeline`:
  - Each stage reports metrics to the monitor
  - Monitor updates are non-blocking (never slow down the pipeline)
- [ ] Implement session summary on exit:
  - Total runtime
  - Messages exchanged (user utterances and agent responses)
  - Errors encountered
  - Average response latency
  - Audio statistics (total speech time, silence ratio)
- [ ] Configure Python `logging`:
  - Default level: INFO
  - Format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
  - File handler: write to `data/session.log`
  - Console handler: suppressed when Rich Live panel is active
- [ ] Add `--debug` flag that shows full log output instead of the Rich panel

## Acceptance Criteria

- [ ] `python -m call_operator run --meeting-url <url>` starts with a live status panel
- [ ] Status panel updates in real-time showing all pipeline stages
- [ ] Transcriptions and responses are visible in the panel
- [ ] Session summary prints on clean exit and on Ctrl+C
- [ ] `--debug` flag switches to verbose log output
- [ ] `--log-level` controls logging verbosity
- [ ] Queue depths are visible for diagnosing backpressure
- [ ] Monitor does not impact pipeline performance
- [ ] All files pass `ruff check` and `mypy --strict`

## Dependencies

- 010 — Async Pipeline (pipeline must be running to monitor)

## Files to Create/Modify

- `src/call_operator/main.py`
- `src/call_operator/monitoring.py`
- `src/call_operator/pipeline.py` (wire monitor callbacks)
