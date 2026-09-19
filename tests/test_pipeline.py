import unittest
import threading
import time
import uuid
import numpy as np
from unittest.mock import MagicMock, patch

from voice_filtering.contracts import AudioFrame, TranscriptEvent
from voice_filtering.asr.whisper import ASRScheduler, INGRESS_CAP
from voice_filtering.pipeline.controller import PipelineControllerImpl
from voice_filtering.audio.capture import CaptureSource
from voice_filtering.audio.resample import StreamingResampler


class FakeTranscriber:
    def __init__(self, texts=None):
        self._texts = texts or ["hello world"]
        self._call_count = 0
        self._loaded = True
        self._load_error = None

    @property
    def is_loaded(self):
        return self._loaded

    @property
    def load_error(self):
        return self._load_error

    def decode(self, pcm16k):
        time.sleep(0.005)
        idx = self._call_count % len(self._texts)
        self._call_count += 1
        return self._texts[idx]


class FakeSource:
    def __init__(self):
        self._running = False
        self._frames = []
        self._idx = 0

    def start(self, *, device_id, session_id):
        self._running = True
        self._idx = 0

    def read_frame(self, timeout_s):
        if not self._running or self._idx >= len(self._frames):
            return None
        f = self._frames[self._idx]
        self._idx += 1
        return f

    def stop(self):
        self._running = False

    def inject(self, frame):
        self._frames.append(frame)


def make_frame(session_id="test", seq=0, amplitude=0.5, valid_samples=160):
    pcm = np.ones(valid_samples, dtype=np.float32) * amplitude
    return AudioFrame(
        session_id=session_id, epoch=0, seq=seq, sample_start=seq * valid_samples,
        captured_ns=time.monotonic_ns(), sample_rate=16000, pcm=pcm,
        valid_samples=valid_samples, discontinuity=False,
    )


class TestPipelineControllerStartStop(unittest.TestCase):
    def setUp(self):
        self.source = FakeSource()
        self.resampler = StreamingResampler()
        self.transcriber = FakeTranscriber(["hello"])
        self.scheduler = ASRScheduler(self.transcriber, lambda e: None)
        self.controller = PipelineControllerImpl(
            source=self.source, resampler=self.resampler,
            transcriber=self.transcriber, scheduler=self.scheduler,
            on_event=lambda e: None,
        )

    def test_start_sets_listening_state(self):
        result = self.controller.start("0", "raw", False)
        self.assertEqual(result["state"], "listening")
        self.controller.stop()

    def test_stop_sets_idle_state(self):
        self.controller.start("0", "raw", False)
        result = self.controller.stop()
        self.assertEqual(result["state"], "idle")

    def test_stop_releases_device(self):
        self.controller.start("0", "raw", False)
        self.controller.stop()
        snap = self.controller.snapshot()
        self.assertEqual(snap["state"], "idle")

    def test_stop_when_idle(self):
        result = self.controller.stop()
        self.assertEqual(result["state"], "idle")


class TestPipelineControllerModes(unittest.TestCase):
    def setUp(self):
        self.source = FakeSource()
        self.resampler = StreamingResampler()
        self.transcriber = FakeTranscriber()
        self.scheduler = ASRScheduler(self.transcriber, lambda e: None)
        self.controller = PipelineControllerImpl(
            source=self.source, resampler=self.resampler,
            transcriber=self.transcriber, scheduler=self.scheduler,
            on_event=lambda e: None,
        )

    def test_switch_to_rnnoise_rejected(self):
        result = self.controller.switch_mode("rnnoise")
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], "STAGE_UNAVAILABLE")

    def test_switch_to_hush_rejected(self):
        result = self.controller.switch_mode("hush")
        self.assertIn("error", result)

    def test_switch_to_combined_rejected(self):
        result = self.controller.switch_mode("combined")
        self.assertIn("error", result)
        self.assertEqual(result["error"]["stage"], "rnnoise")

    def test_raw_mode_accepted(self):
        result = self.controller.switch_mode("raw")
        self.assertNotIn("error", result)

    def test_switch_to_hush_accepted(self):
        class FakeHush:
            is_loaded = True
            load_error = None
            metrics = type("Metrics", (), {"avg_ms": 1, "p95_ms": 1, "total_frames": 1})()
            def reset(self): pass
        self.controller._hush = FakeHush()
        result = self.controller.switch_mode("hush")
        self.assertNotIn("error", result)


class TestCombinedPipeline(unittest.TestCase):
    def setUp(self):
        self.calls = []

        class Stage:
            is_loaded = True
            load_error = None
            metrics = type("Metrics", (), {"avg_ms": 1.0, "p95_ms": 1.0, "total_frames": 1})()

            def __init__(self, name, calls):
                self.name = name
                self.calls = calls
                self.fail = False
                self.fail_reset = False
                self.reset_count = 0

            def reset(self):
                if self.fail_reset:
                    raise RuntimeError(f"{self.name} reset failed")
                self.reset_count += 1

            def process(self, frame):
                if self.fail:
                    raise RuntimeError(f"{self.name} failed")
                self.calls.append((self.name, frame.sample_rate, frame.epoch, frame.session_id))
                return frame

        class Resampler:
            def __init__(self, calls):
                self.calls = calls
                self.reset_count = 0

            def reset(self):
                self.reset_count += 1

            def push(self, frame):
                self.calls.append(("resample", frame.sample_rate, frame.epoch, frame.session_id))
                return [AudioFrame(**{**frame.__dict__, "sample_rate": 16000,
                                      "pcm": frame.pcm[:160].copy(), "valid_samples": 160})]

            def finish(self):
                return []

        class Scheduler:
            def __init__(self, calls):
                self.calls = calls
                self.frames = []
                self.mode = None

            def start(self, session, epoch, mode):
                self.mode = mode

            def reset(self, session, epoch, mode):
                self.mode = mode

            def push_audio(self, frame):
                self.calls.append(("asr", frame.sample_rate, frame.epoch, frame.session_id))
                self.frames.append(frame)

            def run_step(self):
                pass

            def finish(self, timeout_s):
                return True

        self.rnnoise = Stage("rnnoise", self.calls)
        self.hush = Stage("hush", self.calls)
        self.resampler = Resampler(self.calls)
        self.scheduler = Scheduler(self.calls)
        self.controller = PipelineControllerImpl(
            source=FakeSource(), resampler=self.resampler,
            transcriber=FakeTranscriber(), scheduler=self.scheduler,
            on_event=lambda event: None, rnnoise=self.rnnoise, hush=self.hush,
        )

    def make_capture_frame(self):
        frame = make_frame(valid_samples=480)
        return AudioFrame(**{**frame.__dict__, "sample_rate": 48000})

    def test_combined_order_one_resampling_boundary_and_provenance(self):
        self.controller.start("0", "combined", False)
        self.assertTrue(self.controller._capture_loop_body(self.make_capture_frame()))
        self.assertEqual([(name, rate) for name, rate, _, _ in self.calls], [
            ("rnnoise", 48000), ("resample", 48000), ("hush", 16000), ("asr", 16000)
        ])
        self.assertEqual(self.scheduler.mode, "combined")
        self.assertEqual(self.scheduler.frames[0].session_id, self.controller.snapshot()["session_id"])
        self.assertEqual(self.scheduler.frames[0].epoch, 0)
        self.assertEqual(self.controller.snapshot()["stages"]["rnnoise"]["status"], "active")
        self.assertEqual(self.controller.snapshot()["stages"]["hush"]["status"], "active")
        self.controller.stop()

    def test_combined_rejects_missing_hush_without_starting_capture(self):
        self.hush.is_loaded = False
        self.hush.load_error = "model missing"
        result = self.controller.start("0", "combined", False)
        self.assertEqual(result["error"]["stage"], "hush")
        self.assertEqual(self.controller.snapshot()["state"], "idle")

    def test_combined_hush_failure_stops_without_raw_fallback(self):
        self.controller.start("0", "combined", False)
        self.hush.fail = True
        self.assertFalse(self.controller._capture_loop_body(self.make_capture_frame()))
        snap = self.controller.snapshot()
        self.assertEqual(snap["state"], "error")
        self.assertEqual(snap["mode"], "combined")
        self.assertEqual(snap["last_error"]["stage"], "hush")
        self.assertEqual(self.scheduler.frames, [])
        self.controller.stop()

    def test_mode_switch_resets_both_stages_and_preserves_epoch(self):
        self.controller.start("0", "raw", False)
        self.controller.switch_mode("combined")
        self.assertTrue(self.controller._capture_loop_body(self.make_capture_frame()))
        self.assertEqual(self.scheduler.frames[-1].epoch, 1)
        self.assertEqual(self.scheduler.mode, "combined")
        self.assertGreaterEqual(self.rnnoise.reset_count, 2)
        self.assertGreaterEqual(self.hush.reset_count, 2)
        self.assertEqual(self.controller.snapshot()["pending_mode"], None)
        self.controller.stop()

    def test_combined_switch_reset_failure_surfaces_stage_error(self):
        self.controller.start("0", "raw", False)
        self.controller.switch_mode("combined")
        self.hush.fail_reset = True
        self.assertFalse(self.controller._capture_loop_body(self.make_capture_frame()))
        snap = self.controller.snapshot()
        self.assertEqual(snap["state"], "error")
        self.assertEqual(snap["last_error"]["stage"], "hush")
        self.assertEqual(self.scheduler.frames, [])
        self.controller.stop()

    def test_combined_start_reset_failure_names_hush(self):
        self.hush.fail_reset = True
        snap = self.controller.start("0", "combined", False)
        self.assertEqual(snap["state"], "error")
        self.assertEqual(snap["last_error"]["stage"], "hush")
        self.assertEqual(self.scheduler.frames, [])
        self.controller.stop()

class TestPipelineControllerTranscript(unittest.TestCase):
    def setUp(self):
        self.source = FakeSource()
        self.resampler = StreamingResampler()
        self.transcriber = FakeTranscriber()
        self.events = []
        self.scheduler = ASRScheduler(self.transcriber, lambda e: self.events.append(e))
        self.controller = PipelineControllerImpl(
            source=self.source, resampler=self.resampler,
            transcriber=self.transcriber, scheduler=self.scheduler,
            on_event=lambda e: self.events.append(e),
        )

    def test_clear_while_idle(self):
        result = self.controller.clear_transcript()
        self.assertNotIn("error", result)

    def test_clear_while_running_rejected(self):
        self.controller.start("0", "raw", False)
        result = self.controller.clear_transcript()
        self.assertIn("error", result)
        self.controller.stop()

    def test_snapshot_transcript_includes_finals(self):
        event = TranscriptEvent(
            session_id="s1", segment_id=str(uuid.uuid4()), revision=1,
            kind="final", text="test", start_ms=0, end_ms=100, mode="raw",
            epoch=0, final_reason="silence",
        )
        self.controller.add_transcript_event(event)
        snap = self.controller.snapshot()
        self.assertEqual(len(snap["transcript"]), 1)
        self.assertEqual(snap["transcript"][0]["text"], "test")

    def test_stale_partial_replaced(self):
        p1 = TranscriptEvent(
            session_id="s1", segment_id="seg1", revision=1, kind="partial",
            text="he", start_ms=0, end_ms=50, mode="raw", epoch=0,
        )
        p2 = TranscriptEvent(
            session_id="s1", segment_id="seg1", revision=2, kind="partial",
            text="hello", start_ms=0, end_ms=100, mode="raw", epoch=0,
        )
        self.controller.add_transcript_event(p1)
        self.controller.add_transcript_event(p2)
        snap = self.controller.snapshot()
        partials = [t for t in snap["transcript"] if t["kind"] == "partial"]
        self.assertEqual(len(partials), 1)
        self.assertEqual(partials[0]["text"], "hello")

    def test_final_supersedes_partial(self):
        partial = TranscriptEvent(
            session_id="s1", segment_id="seg1", revision=1, kind="partial",
            text="hel", start_ms=0, end_ms=50, mode="raw", epoch=0,
        )
        final = TranscriptEvent(
            session_id="s1", segment_id="seg1", revision=2, kind="final",
            text="hello world", start_ms=0, end_ms=100, mode="raw", epoch=0,
            final_reason="silence",
        )
        self.controller.add_transcript_event(partial)
        self.controller.add_transcript_event(final)
        snap = self.controller.snapshot()
        finals = [t for t in snap["transcript"] if t["kind"] == "final"]
        self.assertEqual(len(finals), 1)

    def test_transcript_limit(self):
        for i in range(1100):
            event = TranscriptEvent(
                session_id="s1", segment_id=str(uuid.uuid4()), revision=1,
                kind="final", text=f"word{i}", start_ms=i * 100,
                end_ms=(i + 1) * 100, mode="raw", epoch=0, final_reason="silence",
            )
            self.controller.add_transcript_event(event)
        snap = self.controller.snapshot()
        self.assertLessEqual(len(snap["transcript"]), 1000)

    def test_snapshot_stages(self):
        snap = self.controller.snapshot()
        self.assertIn("capture", snap["stages"])
        self.assertIn("rnnoise", snap["stages"])
        self.assertIn("hush", snap["stages"])
        self.assertIn("asr", snap["stages"])
        self.assertEqual(snap["stages"]["rnnoise"]["status"], "unavailable")
        self.assertEqual(snap["stages"]["hush"]["status"], "unavailable")

    def test_foreign_origin_rejection(self):
        result = self.controller.switch_mode("raw")
        self.assertNotIn("error", result)


class TestPipelineControllerLifecycle(unittest.TestCase):
    def test_start_stop_start_cycle(self):
        source = FakeSource()
        resampler = StreamingResampler()
        transcriber = FakeTranscriber(["hello"])
        scheduler = ASRScheduler(transcriber, lambda e: None)
        controller = PipelineControllerImpl(
            source=source, resampler=resampler, transcriber=transcriber,
            scheduler=scheduler, on_event=lambda e: None,
        )
        controller.start("0", "raw", False)
        controller.stop()
        controller.start("0", "raw", False)
        controller.stop()
        snap = controller.snapshot()
        self.assertEqual(snap["state"], "idle")

    def test_snapshot_reconnect(self):
        source = FakeSource()
        resampler = StreamingResampler()
        transcriber = FakeTranscriber()
        scheduler = ASRScheduler(transcriber, lambda e: None)
        controller = PipelineControllerImpl(
            source=source, resampler=resampler, transcriber=transcriber,
            scheduler=scheduler, on_event=lambda e: None,
        )
        snap1 = controller.snapshot()
        snap2 = controller.snapshot()
        self.assertEqual(snap1["state"], snap2["state"])

    def test_missing_model_rejected(self):
        source = FakeSource()
        resampler = StreamingResampler()
        transcriber = FakeTranscriber()
        transcriber._loaded = False
        transcriber._load_error = "Model not found"
        scheduler = ASRScheduler(transcriber, lambda e: None)
        controller = PipelineControllerImpl(
            source=source, resampler=resampler, transcriber=transcriber,
            scheduler=scheduler, on_event=lambda e: None,
        )
        result = controller.start("0", "raw", False)
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], "MODEL_MISSING")

    def test_duplicate_start_rejected(self):
        source = FakeSource()
        resampler = StreamingResampler()
        transcriber = FakeTranscriber()
        scheduler = ASRScheduler(transcriber, lambda e: None)
        controller = PipelineControllerImpl(
            source=source, resampler=resampler, transcriber=transcriber,
            scheduler=scheduler, on_event=lambda e: None,
        )
        controller.start("0", "raw", False)
        result = controller.start("0", "raw", False)
        self.assertIn("error", result)
        controller.stop()


if __name__ == "__main__":
    unittest.main()
