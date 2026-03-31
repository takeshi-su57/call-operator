"""CLI entry point for call-operator."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from call_operator.pipeline import Pipeline

app = typer.Typer(name="call-operator", help="Real-time AI meeting agent.")
console = Console()
logger = logging.getLogger(__name__)

_VERSION = "0.1.0"


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"call-operator {_VERSION}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Real-time AI meeting agent — joins calls, listens, and responds."""


@app.command()
def join(
    url: str = typer.Option(..., help="Meeting URL to join (e.g., Google Meet link)"),
    debug: bool = typer.Option(False, "--debug", help="Verbose log output instead of dashboard"),
    headless: bool | None = typer.Option(None, help="Override BROWSER_HEADLESS"),
    log_level: str | None = typer.Option(None, "--log-level", help="Override LOG_LEVEL"),
) -> None:
    """Join a meeting and start the AI agent."""
    from call_operator.config import get_settings
    from call_operator.pipeline import Pipeline

    settings = get_settings()

    # Apply CLI overrides
    if headless is not None:
        object.__setattr__(settings, "browser_headless", headless)
    if log_level is not None:
        object.__setattr__(settings, "log_level", log_level.upper())

    effective_level = "DEBUG" if debug else settings.log_level

    # Configure logging
    handlers: list[logging.Handler] = []

    # File handler — always write to data/session.log
    os.makedirs("data", exist_ok=True)
    file_handler = logging.FileHandler("data/session.log", mode="w")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    handlers.append(file_handler)

    # Console handler — only in debug mode (Rich Live panel replaces console)
    if debug:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        handlers.append(console_handler)

    logging.basicConfig(level=getattr(logging, effective_level), handlers=handlers)

    console.print(f"[bold green]Joining meeting:[/] {url}")

    pipeline = Pipeline(settings)

    async def _run() -> None:
        import sys

        if sys.platform != "win32":
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, lambda: asyncio.create_task(pipeline.stop()))

        await pipeline.start(url)
        try:
            if debug:
                await pipeline.run()
            else:
                await _run_with_dashboard(pipeline)
        finally:
            await pipeline.stop()

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        pass
    finally:
        _print_session_summary(pipeline)


@app.command()
def status() -> None:
    """Show current configuration and provider availability."""
    from call_operator.config import get_settings

    settings = get_settings()

    table = Table(title="call-operator Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("LLM Provider", settings.llm_provider)
    table.add_row("LLM Model", settings.llm_model)
    table.add_row("STT Provider", settings.stt_provider)
    table.add_row("STT Model", settings.stt_model)
    table.add_row("TTS Provider", settings.tts_provider)
    table.add_row("TTS Voice", settings.tts_voice)
    table.add_row("Browser Headless", str(settings.browser_headless))
    table.add_row("Audio Sample Rate", f"{settings.audio_sample_rate} Hz")
    table.add_row("VAD Threshold", str(settings.vad_threshold))
    table.add_row("Bot Name", settings.bot_name)
    table.add_row("Log Level", settings.log_level)
    table.add_row("Queue Size", str(settings.pipeline_queue_size))

    # API key status
    keys = {
        "OpenAI": bool(settings.openai_api_key),
        "Anthropic": bool(settings.anthropic_api_key),
        "Google": bool(settings.google_api_key),
        "Deepgram": bool(settings.deepgram_api_key),
        "ElevenLabs": bool(settings.elevenlabs_api_key),
    }
    for name, available in keys.items():
        table.add_row(
            f"{name} API Key",
            "[green]configured[/]" if available else "[dim]not set[/]",
        )

    console.print(table)


# ---------------------------------------------------------------------------
# Rich Live dashboard
# ---------------------------------------------------------------------------


async def _run_with_dashboard(pipeline: Pipeline) -> None:
    """Run the pipeline with a Rich Live dashboard overlay."""
    from rich.live import Live

    run_task = asyncio.create_task(pipeline.run())

    with Live(_build_dashboard(pipeline), console=console, refresh_per_second=2) as live:
        while not run_task.done():
            live.update(_build_dashboard(pipeline))
            await asyncio.sleep(0.5)

    # Re-raise if pipeline.run() raised
    exc = run_task.exception()
    if exc is not None:
        raise exc


def _build_dashboard(pipeline: Pipeline) -> Table:
    """Build the Rich dashboard table from pipeline monitor state."""
    status = pipeline.monitor.get_status()

    # Main table
    table = Table(title="call-operator Dashboard", show_lines=True)
    table.add_column("Section", style="cyan", width=20)
    table.add_column("Details", style="white")

    # Uptime
    uptime_s = status["uptime_s"]
    mins, secs = divmod(int(uptime_s), 60)
    table.add_row("Uptime", f"{mins}m {secs}s")

    # Stage status
    stages = status.get("stage_status", {})
    stage_lines: list[str] = []
    for name, st in stages.items():
        if st == "running":
            icon = "[green]●[/]"
        elif st == "error":
            icon = "[red]●[/]"
        else:
            icon = "[yellow]●[/]"
        stage_lines.append(f"{icon} {name}")
    table.add_row("Stages", "\n".join(stage_lines) if stage_lines else "[dim]waiting...[/]")

    # Queue depths
    depths = status.get("queue_depths", {})
    depth_parts = [f"{k}: {v}" for k, v in depths.items()]
    table.add_row("Queues", "  ".join(depth_parts) if depth_parts else "[dim]—[/]")

    # Stats
    stats = (
        f"Audio: {status['audio_chunks']}  "
        f"Speech: {status['speech_segments']}  "
        f"Transcripts: {status['transcriptions']}  "
        f"Responses: {status['responses']}  "
        f"Errors: {status['errors']}"
    )
    table.add_row("Stats", stats)

    # Recent transcripts
    transcripts = status.get("recent_transcripts", [])
    table.add_row(
        "Transcripts",
        "\n".join(f"» {t[:80]}" for t in transcripts[-3:]) if transcripts else "[dim]—[/]",
    )

    # Recent responses
    responses = status.get("recent_responses", [])
    table.add_row(
        "Responses",
        "\n".join(f"» {r[:80]}" for r in responses[-3:]) if responses else "[dim]—[/]",
    )

    return table


def _print_session_summary(pipeline: Pipeline) -> None:
    """Print a session summary table on exit."""
    summary = pipeline.monitor.get_summary()

    uptime_s = summary["uptime_s"]
    mins, secs = divmod(int(uptime_s), 60)

    table = Table(title="Session Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Runtime", f"{mins}m {secs}s")
    table.add_row("Audio Chunks", str(summary["audio_chunks"]))
    table.add_row("Speech Segments", str(summary["speech_segments"]))
    table.add_row("Transcriptions", str(summary["transcriptions"]))
    table.add_row("Responses", str(summary["responses"]))
    table.add_row("Errors", str(summary["errors"]))
    table.add_row("Avg Response Latency", f"{summary['avg_response_latency_ms']:.0f}ms")

    console.print()
    console.print(table)


if __name__ == "__main__":
    app()
