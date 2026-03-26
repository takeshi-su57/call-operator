"""CLI entry point for call-operator."""

from __future__ import annotations

import asyncio
import logging

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
    from call_operator.pipeline import run_pipeline

    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level))

    console.print(f"[bold green]Joining meeting:[/] {url}")
    asyncio.run(run_pipeline(url=url, settings=settings))


if __name__ == "__main__":
    app()
