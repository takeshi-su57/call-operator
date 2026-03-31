"""Tests for async_retry decorator and CircuitBreaker."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest

from call_operator.retry import CircuitBreaker, async_retry

# ------------------------------------------------------------------
# async_retry tests
# ------------------------------------------------------------------


class TestAsyncRetry:
    async def test_succeeds_first_try(self) -> None:
        @async_retry(max_retries=3)
        async def succeed() -> str:
            return "ok"

        assert await succeed() == "ok"

    async def test_retries_then_succeeds(self) -> None:
        call_count = 0

        @async_retry(max_retries=3, base_delay=0.01)
        async def flaky() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                msg = "transient"
                raise RuntimeError(msg)
            return "ok"

        result = await flaky()
        assert result == "ok"
        assert call_count == 3

    async def test_exhausts_retries(self) -> None:
        @async_retry(max_retries=3, base_delay=0.01)
        async def always_fail() -> str:
            msg = "permanent"
            raise RuntimeError(msg)

        with pytest.raises(RuntimeError, match="permanent"):
            await always_fail()

    async def test_only_retries_specified_exceptions(self) -> None:
        call_count = 0

        @async_retry(max_retries=3, base_delay=0.01, retryable_exceptions=(ValueError,))
        async def wrong_error() -> str:
            nonlocal call_count
            call_count += 1
            msg = "not retryable"
            raise TypeError(msg)

        with pytest.raises(TypeError, match="not retryable"):
            await wrong_error()
        assert call_count == 1  # no retry

    async def test_backoff_calls_sleep(self) -> None:
        call_count = 0

        @async_retry(max_retries=3, base_delay=1.0)
        async def fail_twice() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                msg = "transient"
                raise RuntimeError(msg)
            return "ok"

        sleep_mock = AsyncMock()
        with patch("call_operator.retry.asyncio.sleep", sleep_mock):
            await fail_twice()

        assert sleep_mock.call_count == 2  # slept before retry 2 and 3


# ------------------------------------------------------------------
# CircuitBreaker tests
# ------------------------------------------------------------------


class TestCircuitBreaker:
    def test_starts_closed(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, cooldown_s=60.0)
        assert cb.is_open is False

    def test_opens_after_threshold(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, cooldown_s=60.0)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is False
        cb.record_failure()  # 3rd failure
        assert cb.is_open is True

    def test_half_open_after_cooldown(self) -> None:
        cb = CircuitBreaker(failure_threshold=2, cooldown_s=10.0)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is True

        # Simulate cooldown elapsed
        with patch("call_operator.retry.time.monotonic", return_value=time.monotonic() + 15.0):
            assert cb.is_open is False  # transitioned to half-open

    def test_success_closes_circuit(self) -> None:
        cb = CircuitBreaker(failure_threshold=2, cooldown_s=10.0)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is True

        # Simulate cooldown elapsed → half-open
        with patch("call_operator.retry.time.monotonic", return_value=time.monotonic() + 15.0):
            assert cb.is_open is False  # half-open allows one call
            cb.record_success()
        assert cb.is_open is False  # now closed

    def test_failure_in_half_open_reopens(self) -> None:
        cb = CircuitBreaker(failure_threshold=2, cooldown_s=10.0)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is True

        # Simulate cooldown elapsed → half-open
        with patch("call_operator.retry.time.monotonic", return_value=time.monotonic() + 15.0):
            assert cb.is_open is False  # half-open
            cb.record_failure()
        assert cb.is_open is True  # re-opened
