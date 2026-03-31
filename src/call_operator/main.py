"""CLI entry point for call-operator."""

from __future__ import annotations

import asyncio
import logging
import signal

import typer
from rich.console import Console

app = typer.Typer(name="call-operator", help="Real-time AI meeting agent.")
console = Console()
logger = logging.getLogger(__name__)


@app.command()
def join(
    url: str = typer.Option(..., help="Meeting URL to join (e.g., Google Meet link)"),
) -> None:
    """Join a meeting and start the AI agent."""
    from call_operator.config import get_settings
    from call_operator.pipeline import Pipeline

    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level))

    console.print(f"[bold green]Joining meeting:[/] {url}")

    pipeline = Pipeline(settings)

    async def _run() -> None:
        # Register signal handlers for graceful shutdown (Unix only)
        import sys

        if sys.platform != "win32":
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, lambda: asyncio.create_task(pipeline.stop()))

        await pipeline.start(url)
        try:
            await pipeline.run()
        finally:
            await pipeline.stop()

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        console.print("[yellow]Interrupted — shutting down[/]")


if __name__ == "__main__":
    app()
