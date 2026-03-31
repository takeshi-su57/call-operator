"""Retry decorator with exponential backoff and circuit breaker."""

from __future__ import annotations

import asyncio
import functools
import logging
import random
import time
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

_LLM_FALLBACK = "I'm having trouble responding right now."


# ---------------------------------------------------------------------------
# async_retry decorator
# ---------------------------------------------------------------------------


def async_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Any:
    """Decorator that retries an async function with exponential backoff and jitter.

    Args:
        max_retries: Maximum number of attempts (including the first).
        base_delay: Base delay in seconds before first retry.
        max_delay: Cap on the delay between retries.
        retryable_exceptions: Exception types that trigger a retry.
    """

    def decorator(func: Any) -> Any:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exc = exc
                    if attempt < max_retries - 1:
                        delay = min(base_delay * (2**attempt), max_delay)
                        delay *= random.uniform(0.5, 1.5)  # noqa: S311
                        logger.warning(
                            "Retry %d/%d for %s: %s (delay=%.1fs)",
                            attempt + 1,
                            max_retries,
                            func.__qualname__,
                            exc,
                            delay,
                        )
                        await asyncio.sleep(delay)
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# CircuitBreaker
# ---------------------------------------------------------------------------

_STATE_CLOSED = "CLOSED"
_STATE_OPEN = "OPEN"
_STATE_HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Circuit breaker to prevent hammering a failing external API.

    After *failure_threshold* consecutive failures the circuit opens,
    rejecting calls for *cooldown_s* seconds.  After cooldown it enters
    half-open state, allowing one call through.  Success closes it;
    failure re-opens it.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        cooldown_s: float = 60.0,
    ) -> None:
        self._threshold = failure_threshold
        self._cooldown_s = cooldown_s
        self._state = _STATE_CLOSED
        self._consecutive_failures = 0
        self._last_failure_time: float | None = None

    @property
    def is_open(self) -> bool:
        """Return True if calls should be rejected."""
        if self._state == _STATE_CLOSED:
            return False

        if self._state == _STATE_OPEN:
            # Check if cooldown elapsed → transition to half-open
            if (
                self._last_failure_time is not None
                and (time.monotonic() - self._last_failure_time) >= self._cooldown_s
            ):
                self._state = _STATE_HALF_OPEN
                return False
            return True

        # HALF_OPEN: allow one call through
        return False

    def record_success(self) -> None:
        """Record a successful call — reset to closed."""
        self._consecutive_failures = 0
        self._state = _STATE_CLOSED

    def record_failure(self) -> None:
        """Record a failed call — may open the circuit."""
        self._consecutive_failures += 1
        self._last_failure_time = time.monotonic()

        if self._state == _STATE_HALF_OPEN:
            self._state = _STATE_OPEN
        elif self._consecutive_failures >= self._threshold:
            self._state = _STATE_OPEN
            logger.warning(
                "Circuit breaker opened after %d consecutive failures",
                self._consecutive_failures,
            )
