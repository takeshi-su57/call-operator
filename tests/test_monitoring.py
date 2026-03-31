"""Tests for PipelineMonitor."""

from __future__ import annotations

import threading

from call_operator.monitoring import PipelineMonitor


class TestPipelineMonitorInit:
    def test_initial_state(self) -> None:
        mon = PipelineMonitor()
        status = mon.get_status()
        assert status["audio_chunks"] == 0
        assert status["speech_segments"] == 0
        assert status["transcriptions"] == 0
        assert status["responses"] == 0
        assert status["errors"] == 0
        assert status["recent_transcripts"] == []
        assert status["recent_responses"] == []
        assert status["uptime_s"] >= 0


class TestPipelineMonitorRecording:
    def test_record_audio_chunk(self) -> None:
        mon = PipelineMonitor()
        mon.record_audio_chunk()
        mon.record_audio_chunk()
        assert mon.get_status()["audio_chunks"] == 2

    def test_record_speech_segment(self) -> None:
        mon = PipelineMonitor()
        mon.record_speech_segment()
        assert mon.get_status()["speech_segments"] == 1

    def test_record_transcription(self) -> None:
        mon = PipelineMonitor()
        mon.record_transcription("Hello")
        mon.record_transcription("World")
        status = mon.get_status()
        assert status["transcriptions"] == 2
        assert status["recent_transcripts"] == ["Hello", "World"]

    def test_recent_transcripts_limited_to_five(self) -> None:
        mon = PipelineMonitor()
        for i in range(8):
            mon.record_transcription(f"msg-{i}")
        recent = mon.get_status()["recent_transcripts"]
        assert len(recent) == 5
        assert recent[0] == "msg-3"
        assert recent[-1] == "msg-7"

    def test_record_response(self) -> None:
        mon = PipelineMonitor()
        mon.record_response("I can help.", 150.0)
        status = mon.get_status()
        assert status["responses"] == 1
        assert status["recent_responses"] == ["I can help."]

    def test_recent_responses_limited_to_three(self) -> None:
        mon = PipelineMonitor()
        for i in range(5):
            mon.record_response(f"resp-{i}", 100.0)
        recent = mon.get_status()["recent_responses"]
        assert len(recent) == 3
        assert recent[0] == "resp-2"

    def test_record_error(self) -> None:
        mon = PipelineMonitor()
        mon.record_error("tts", "API timeout")
        status = mon.get_status()
        assert status["errors"] == 1
        assert "[tts] API timeout" in status["recent_errors"][0]

    def test_set_stage_status(self) -> None:
        mon = PipelineMonitor()
        mon.set_stage_status("capture", "running")
        mon.set_stage_status("stt", "error")
        status = mon.get_status()
        assert status["stage_status"]["capture"] == "running"
        assert status["stage_status"]["stt"] == "error"

    def test_update_queue_depths(self) -> None:
        mon = PipelineMonitor()
        mon.update_queue_depths({"audio": 5, "speech": 2})
        status = mon.get_status()
        assert status["queue_depths"]["audio"] == 5
        assert status["queue_depths"]["speech"] == 2


class TestPipelineMonitorSummary:
    def test_get_summary(self) -> None:
        mon = PipelineMonitor()
        mon.record_audio_chunk()
        mon.record_transcription("test")
        mon.record_response("reply", 200.0)
        mon.record_response("reply2", 100.0)
        mon.record_error("stt", "oops")

        summary = mon.get_summary()
        assert summary["audio_chunks"] == 1
        assert summary["transcriptions"] == 1
        assert summary["responses"] == 2
        assert summary["errors"] == 1
        assert summary["avg_response_latency_ms"] == 150.0
        assert summary["uptime_s"] >= 0

    def test_summary_zero_latency_when_no_responses(self) -> None:
        mon = PipelineMonitor()
        assert mon.get_summary()["avg_response_latency_ms"] == 0.0


class TestPipelineMonitorThreadSafety:
    def test_concurrent_access(self) -> None:
        mon = PipelineMonitor()
        errors: list[Exception] = []

        def writer() -> None:
            try:
                for _ in range(100):
                    mon.record_audio_chunk()
                    mon.record_transcription("test")
                    mon.record_response("reply", 50.0)
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        def reader() -> None:
            try:
                for _ in range(100):
                    mon.get_status()
                    mon.get_summary()
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=reader),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert mon.get_status()["audio_chunks"] == 200
