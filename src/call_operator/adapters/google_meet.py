"""Google Meet adapter — joins meetings via Playwright browser automation."""

from __future__ import annotations

import asyncio
import logging
import struct
from typing import TYPE_CHECKING, Any

from call_operator.adapters.base import MeetingAdapter

if TYPE_CHECKING:
    from call_operator.adapters.base import AudioChunk
    from call_operator.config import Settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Google Meet UI selectors — update when Meet UI changes
# ---------------------------------------------------------------------------

_SEL_NAME_INPUT = 'input[aria-label="Your name"]'
_SEL_MIC_BUTTON = '[aria-label*="microphone" i]'
_SEL_CAM_BUTTON = '[aria-label*="camera" i]'
_SEL_JOIN_BUTTON = (
    'button[jsname="Qx7uuf"], '  # "Ask to join" / "Join now"
    'button:has-text("Join now"), '
    'button:has-text("Ask to join")'
)
_SEL_LEAVE_BUTTON = '[aria-label="Leave call"]'
_SEL_DISMISS_BUTTON = 'button:has-text("Got it"), button:has-text("Dismiss")'

# Presence of these indicates the meeting has ended or user was removed.
_SEL_ENDED_INDICATORS = (
    "div[data-call-ended]",
    ':text("You\'ve been removed")',
    ':text("The meeting has ended")',
    ':text("You left the meeting")',
    ':text("Return to home screen")',
)

_POLL_INTERVAL_S = 0.05  # 50ms between audio polls

# ---------------------------------------------------------------------------
# Injected JavaScript for Web Audio capture
# ---------------------------------------------------------------------------

_AUDIO_SETUP_JS = """() => {
    if (window.__audioCtx) return;

    window.__audioCtx = new AudioContext({ sampleRate: 16000 });
    window.__audioBuffer = [];

    const processor = window.__audioCtx.createScriptProcessor(4096, 1, 1);
    processor.onaudioprocess = (e) => {
        const data = e.inputBuffer.getChannelData(0);
        const pcm16 = new Int16Array(data.length);
        for (let i = 0; i < data.length; i++) {
            const s = Math.max(-1, Math.min(1, data[i]));
            pcm16[i] = s < 0 ? s * 32768 : s * 32767;
        }
        window.__audioBuffer.push(Array.from(pcm16));
    };

    const connectElement = (el) => {
        if (el.__audioConnected) return;
        try {
            const source = window.__audioCtx.createMediaElementSource(el);
            source.connect(processor);
            source.connect(window.__audioCtx.destination);
            el.__audioConnected = true;
        } catch(e) {}
    };

    document.querySelectorAll('audio, video').forEach(connectElement);

    const observer = new MutationObserver((mutations) => {
        for (const m of mutations) {
            for (const node of m.addedNodes) {
                if (node.tagName === 'AUDIO' || node.tagName === 'VIDEO') {
                    connectElement(node);
                } else if (node.querySelectorAll) {
                    node.querySelectorAll('audio, video').forEach(connectElement);
                }
            }
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });

    processor.connect(window.__audioCtx.destination);
}"""

_AUDIO_READ_JS = """() => {
    if (!window.__audioBuffer || window.__audioBuffer.length === 0) return null;
    const chunks = window.__audioBuffer.splice(0);
    let totalLen = 0;
    for (const c of chunks) totalLen += c.length;
    const merged = new Int16Array(totalLen);
    let offset = 0;
    for (const c of chunks) {
        merged.set(c, offset);
        offset += c.length;
    }
    return Array.from(merged);
}"""


class GoogleMeetAdapter(MeetingAdapter):
    """Playwright-based Google Meet adapter.

    Joins a Google Meet session as a browser participant,
    captures audio from the meeting via the Web Audio API,
    and plays audio back into the meeting.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.sample_rate: int = settings.audio_sample_rate
        self.channels: int = 1
        self._pw: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None
        self._connected = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self, url: str) -> None:
        """Join a Google Meet session via Playwright."""
        from playwright.async_api import async_playwright

        logger.info("Launching browser (headless=%s)", self.settings.browser_headless)

        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=self.settings.browser_headless,
            args=[
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                "--autoplay-policy=no-user-gesture-required",
                "--disable-features=WebRtcHideLocalIpsWithMdns",
            ],
        )

        self._context = await self._browser.new_context(
            permissions=["microphone", "camera"],
        )
        self._page = await self._context.new_page()
        self._page.set_default_timeout(self.settings.browser_timeout)

        logger.info("Navigating to %s", url)
        await self._page.goto(url, wait_until="networkidle")

        await self._handle_prejoin_ui()
        await self._setup_audio_capture()

        self._connected = True
        logger.info("Connected to meeting")

    async def disconnect(self) -> None:
        """Leave the meeting and close the browser."""
        if self._page is not None:
            try:
                leave = self._page.locator(_SEL_LEAVE_BUTTON)
                if await leave.count() > 0:
                    await leave.first.click(timeout=3000)
                    logger.info("Clicked leave button")
            except Exception:  # noqa: BLE001
                logger.debug("Could not click leave button", exc_info=True)

        if self._context is not None:
            try:
                await self._context.close()
            except Exception:  # noqa: BLE001
                logger.debug("Error closing browser context", exc_info=True)

        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception:  # noqa: BLE001
                logger.debug("Error closing browser", exc_info=True)

        if self._pw is not None:
            try:
                await self._pw.stop()
            except Exception:  # noqa: BLE001
                logger.debug("Error stopping Playwright", exc_info=True)

        self._page = None
        self._context = None
        self._browser = None
        self._pw = None
        self._connected = False
        logger.info("Disconnected from meeting")

    def is_connected(self) -> bool:
        """Return whether the adapter is connected to a meeting."""
        return self._connected

    # ------------------------------------------------------------------
    # Audio I/O
    # ------------------------------------------------------------------

    async def read_audio(self) -> bytes | None:
        """Read the next chunk of PCM audio captured from the meeting.

        Polls the browser-side audio buffer. Returns raw PCM bytes when
        audio is available, or ``None`` when the meeting has ended.
        """
        while self._connected and self._page is not None:
            if await self._check_meeting_ended():
                self._connected = False
                logger.info("Meeting ended — stopping audio capture")
                return None

            try:
                result: list[int] | None = await self._page.evaluate(_AUDIO_READ_JS)
            except Exception:  # noqa: BLE001
                logger.warning("Error reading audio from browser", exc_info=True)
                self._connected = False
                return None

            if result and len(result) > 0:
                return struct.pack(f"<{len(result)}h", *result)

            await asyncio.sleep(_POLL_INTERVAL_S)

        return None

    async def play_audio(self, audio: AudioChunk) -> None:
        """Play audio into the meeting (stub — full implementation in issue 012)."""
        logger.debug("play_audio called (%d bytes) — not yet implemented", len(audio.data))

    # ------------------------------------------------------------------
    # Pre-join UI handling
    # ------------------------------------------------------------------

    async def _handle_prejoin_ui(self) -> None:
        """Handle the Google Meet pre-join screen."""
        assert self._page is not None  # noqa: S101

        # Dismiss any info dialogs
        await self._try_click(_SEL_DISMISS_BUTTON, timeout=3000)

        # Set display name if the input is present
        await self._try_fill(_SEL_NAME_INPUT, self.settings.bot_name, timeout=3000)

        # Turn off camera
        await self._try_click(_SEL_CAM_BUTTON, timeout=3000)

        # Turn off microphone
        await self._try_click(_SEL_MIC_BUTTON, timeout=3000)

        # Click "Join now" / "Ask to join"
        logger.info("Clicking join button")
        join = self._page.locator(_SEL_JOIN_BUTTON).first
        await join.click(timeout=self.settings.browser_timeout)

        # Wait until we're in the meeting (leave button appears)
        logger.info("Waiting for admission to meeting")
        await self._page.locator(_SEL_LEAVE_BUTTON).wait_for(
            state="visible", timeout=self.settings.browser_timeout
        )

    # ------------------------------------------------------------------
    # Audio capture setup
    # ------------------------------------------------------------------

    async def _setup_audio_capture(self) -> None:
        """Inject JavaScript to capture meeting audio via Web Audio API."""
        assert self._page is not None  # noqa: S101
        await self._page.evaluate(_AUDIO_SETUP_JS)
        logger.info("Audio capture initialized (sample_rate=%d)", self.sample_rate)

    # ------------------------------------------------------------------
    # Meeting state detection
    # ------------------------------------------------------------------

    async def _check_meeting_ended(self) -> bool:
        """Check if the meeting has ended or user was removed."""
        if self._page is None:
            return True
        try:
            for sel in _SEL_ENDED_INDICATORS:
                if await self._page.locator(sel).count() > 0:
                    return True
        except Exception:  # noqa: BLE001
            return True
        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _try_click(self, selector: str, *, timeout: int = 5000) -> bool:
        """Try to click an element. Returns True if clicked, False otherwise."""
        assert self._page is not None  # noqa: S101
        try:
            loc = self._page.locator(selector).first
            if await loc.count() > 0:
                await loc.click(timeout=timeout)
                return True
        except Exception:  # noqa: BLE001
            logger.debug("Could not click %s", selector)
        return False

    async def _try_fill(self, selector: str, value: str, *, timeout: int = 5000) -> bool:
        """Try to fill an input. Returns True if filled, False otherwise."""
        assert self._page is not None  # noqa: S101
        try:
            loc = self._page.locator(selector).first
            if await loc.count() > 0:
                await loc.fill(value, timeout=timeout)
                return True
        except Exception:  # noqa: BLE001
            logger.debug("Could not fill %s", selector)
        return False
