"""Tests for GoogleMeetAdapter — Playwright interactions are fully mocked."""

from __future__ import annotations

import struct
from unittest.mock import AsyncMock, MagicMock, patch

from call_operator.adapters.google_meet import GoogleMeetAdapter


def _make_settings() -> MagicMock:
    """Create a minimal mock Settings for the adapter."""
    s = MagicMock()
    s.browser_headless = True
    s.browser_timeout = 10000
    s.audio_sample_rate = 16000
    s.bot_name = "TestBot"
    return s


def _make_playwright_mocks() -> tuple[AsyncMock, AsyncMock, AsyncMock, AsyncMock]:
    """Create mock Playwright → browser → context → page chain."""
    page = AsyncMock()
    page.set_default_timeout = MagicMock()

    # locator().count() and locator().first.click() chain
    leave_locator = AsyncMock()
    leave_locator.count = AsyncMock(return_value=0)
    leave_locator.first = AsyncMock()
    leave_locator.wait_for = AsyncMock()

    join_locator = AsyncMock()
    join_locator.first = AsyncMock()

    def locator_side_effect(sel: str) -> AsyncMock:
        from call_operator.adapters.google_meet import _SEL_JOIN_BUTTON, _SEL_LEAVE_BUTTON

        if sel == _SEL_LEAVE_BUTTON:
            return leave_locator
        if sel == _SEL_JOIN_BUTTON:
            return join_locator
        # Default: return a locator that reports 0 elements
        mock_loc = AsyncMock()
        mock_loc.count = AsyncMock(return_value=0)
        mock_loc.first = AsyncMock()
        return mock_loc

    page.locator = MagicMock(side_effect=locator_side_effect)
    page.goto = AsyncMock()
    page.evaluate = AsyncMock()

    context = AsyncMock()
    context.new_page = AsyncMock(return_value=page)

    browser = AsyncMock()
    browser.new_context = AsyncMock(return_value=context)

    pw = AsyncMock()
    pw.chromium = AsyncMock()
    pw.chromium.launch = AsyncMock(return_value=browser)

    return pw, browser, context, page


class TestGoogleMeetAdapterInit:
    def test_initial_state(self) -> None:
        adapter = GoogleMeetAdapter(_make_settings())
        assert adapter.is_connected() is False
        assert adapter.sample_rate == 16000
        assert adapter.channels == 1


class TestGoogleMeetAdapterConnect:
    async def test_launches_browser_and_connects(self) -> None:
        pw, browser, context, page = _make_playwright_mocks()
        settings = _make_settings()
        adapter = GoogleMeetAdapter(settings)

        mock_entry = AsyncMock()
        mock_entry.start = AsyncMock(return_value=pw)
        with patch(
            "playwright.async_api.async_playwright",
            return_value=mock_entry,
        ):
            await adapter.connect("https://meet.google.com/abc-defg-hij")

        assert adapter.is_connected() is True
        pw.chromium.launch.assert_called_once()
        page.goto.assert_called_once()

    async def test_navigates_to_url(self) -> None:
        pw, browser, context, page = _make_playwright_mocks()
        settings = _make_settings()
        adapter = GoogleMeetAdapter(settings)

        mock_entry = AsyncMock()
        mock_entry.start = AsyncMock(return_value=pw)
        with patch(
            "playwright.async_api.async_playwright",
            return_value=mock_entry,
        ):
            await adapter.connect("https://meet.google.com/test-url")

        page.goto.assert_called_once_with(
            "https://meet.google.com/test-url", wait_until="networkidle"
        )


class TestGoogleMeetAdapterReadAudio:
    async def test_returns_pcm_bytes(self) -> None:
        settings = _make_settings()
        adapter = GoogleMeetAdapter(settings)
        adapter._connected = True

        page = AsyncMock()
        # First evaluate call: audio setup (from connect path not needed here)
        # read_audio calls evaluate with _AUDIO_READ_JS
        samples = [100, -200, 300, -400]
        page.evaluate = AsyncMock(return_value=samples)

        # Mock locator for _check_meeting_ended
        ended_locator = AsyncMock()
        ended_locator.count = AsyncMock(return_value=0)
        page.locator = MagicMock(return_value=ended_locator)

        adapter._page = page

        result = await adapter.read_audio()

        assert result is not None
        expected = struct.pack(f"<{len(samples)}h", *samples)
        assert result == expected

    async def test_returns_none_when_disconnected(self) -> None:
        settings = _make_settings()
        adapter = GoogleMeetAdapter(settings)
        adapter._connected = False

        result = await adapter.read_audio()
        assert result is None

    async def test_returns_none_when_meeting_ended(self) -> None:
        settings = _make_settings()
        adapter = GoogleMeetAdapter(settings)
        adapter._connected = True

        page = AsyncMock()
        # _check_meeting_ended finds an ended indicator
        ended_locator = AsyncMock()
        ended_locator.count = AsyncMock(return_value=1)
        page.locator = MagicMock(return_value=ended_locator)
        adapter._page = page

        result = await adapter.read_audio()
        assert result is None
        assert adapter.is_connected() is False


class TestGoogleMeetAdapterPlayAudio:
    async def test_play_audio_calls_evaluate(self) -> None:
        from call_operator.adapters.base import AudioChunk

        settings = _make_settings()
        adapter = GoogleMeetAdapter(settings)
        adapter._connected = True

        page = AsyncMock()
        page.evaluate = AsyncMock(return_value=100.0)  # duration_ms
        adapter._page = page

        chunk = AudioChunk(data=struct.pack("<4h", 100, -200, 300, -400), sample_rate=16000)
        await adapter.play_audio(chunk)

        page.evaluate.assert_called_once()
        call_args = page.evaluate.call_args
        samples_arg = call_args[0][1]
        assert samples_arg == [100, -200, 300, -400]

    async def test_play_audio_skips_when_disconnected(self) -> None:
        from call_operator.adapters.base import AudioChunk

        settings = _make_settings()
        adapter = GoogleMeetAdapter(settings)
        adapter._connected = False

        chunk = AudioChunk(data=b"\x00\x01" * 10, sample_rate=16000)
        # Should not raise
        await adapter.play_audio(chunk)

    async def test_play_audio_handles_evaluate_error(self) -> None:
        from call_operator.adapters.base import AudioChunk

        settings = _make_settings()
        adapter = GoogleMeetAdapter(settings)
        adapter._connected = True

        page = AsyncMock()
        page.evaluate = AsyncMock(side_effect=RuntimeError("page crashed"))
        adapter._page = page

        chunk = AudioChunk(data=struct.pack("<2h", 100, -100), sample_rate=16000)
        # Should not raise — error is caught and logged
        await adapter.play_audio(chunk)


class TestGoogleMeetAdapterDisconnect:
    async def test_closes_browser(self) -> None:
        settings = _make_settings()
        adapter = GoogleMeetAdapter(settings)

        page = AsyncMock()
        leave_loc = AsyncMock()
        leave_loc.count = AsyncMock(return_value=1)
        leave_loc.first = AsyncMock()
        page.locator = MagicMock(return_value=leave_loc)

        context = AsyncMock()
        browser = AsyncMock()
        pw = AsyncMock()

        adapter._page = page
        adapter._context = context
        adapter._browser = browser
        adapter._pw = pw
        adapter._connected = True

        await adapter.disconnect()

        context.close.assert_called_once()
        browser.close.assert_called_once()
        pw.stop.assert_called_once()
        assert adapter.is_connected() is False
        assert adapter._page is None

    async def test_sets_not_connected(self) -> None:
        settings = _make_settings()
        adapter = GoogleMeetAdapter(settings)
        adapter._connected = True

        await adapter.disconnect()

        assert adapter.is_connected() is False

    async def test_disconnect_is_safe_when_not_connected(self) -> None:
        settings = _make_settings()
        adapter = GoogleMeetAdapter(settings)
        # Should not raise
        await adapter.disconnect()
        assert adapter.is_connected() is False


class TestGoogleMeetAdapterReconnect:
    async def test_reconnect_succeeds(self) -> None:
        settings = _make_settings()
        adapter = GoogleMeetAdapter(settings)
        adapter._url = "https://meet.google.com/test"
        adapter._connected = False

        with (
            patch.object(adapter, "disconnect", new_callable=AsyncMock),
            patch.object(adapter, "connect", new_callable=AsyncMock),
            patch(
                "call_operator.adapters.google_meet.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            result = await adapter._reconnect()

        assert result is True

    async def test_reconnect_fails_after_max_attempts(self) -> None:
        settings = _make_settings()
        adapter = GoogleMeetAdapter(settings)
        adapter._url = "https://meet.google.com/test"
        adapter._connected = False

        with (
            patch.object(adapter, "disconnect", new_callable=AsyncMock),
            patch.object(
                adapter, "connect", new_callable=AsyncMock, side_effect=RuntimeError("fail")
            ),
            patch(
                "call_operator.adapters.google_meet.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            result = await adapter._reconnect()

        assert result is False

    async def test_reconnect_returns_false_without_url(self) -> None:
        settings = _make_settings()
        adapter = GoogleMeetAdapter(settings)
        adapter._url = None

        result = await adapter._reconnect()
        assert result is False
