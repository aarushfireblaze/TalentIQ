import unittest
import threading
import time
import uuid
import numpy as np
from unittest.mock import MagicMock, patch

from voice_filtering.contracts import AudioFrame, StageStatus
from voice_filtering.audio.rnnoise import (
    RNNoiseProcessor, RNNoiseLoadError, FRAME_SIZE, SOURCE_RATE,
    _SCALE_UP, _SCALE_DOWN, RNNoiseMetrics,
)
from voice_filtering.audio.resample import StreamingResampler
from voice_filtering.asr.whisper import ASRScheduler
from voice_filtering.pipeline.controller import PipelineControllerImpl
from tests.fakes import make_frames, make_frame


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
        time.sleep(0.001)
        idx = self._call_count % len(self._texts)
        self._call_count += 1
        return self._texts[idx]


class FakeSource:
    def __init__(self, frames=None):
        self._frames = frames or []
        self._idx = 0
        self._running = False

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


class FakeRNNoise:
    def __init__(self, loaded=True, error=None):
        self._loaded = loaded
        self._error = error
        self._process_count = 0
        self._reset_count = 0
        self._metrics = RNNoiseMetrics()

    @property
    def is_loaded(self):
        return self._loaded

    @property
    def load_error(self):
        return self._error

    @property
    def metrics(self):
        return self._metrics

    def reset(self):
        self._reset_count += 1
        self._metrics.reset()

    def process(self, frame):
        self._process_count += 1
        t0 = time.monotonic()
        pcm = frame.pcm[:frame.valid_samples].copy()
        out = np.zeros(FRAME_SIZE, dtype=np.float32)
        out[:len(pcm)] = pcm
        elapsed = time.monotonic() - t0
        self._metrics.record(elapsed)
        return AudioFrame(
            session_id=frame.session_id,
            epoch=frame.epoch,
            seq=frame.seq,
            sample_start=frame.sample_start,
            captured_ns=frame.captured_ns,
            sample_rate=frame.sample_rate,
            pcm=out,
            valid_samples=frame.valid_samples,
            discontinuity=frame.discontinuity,
        )

    def close(self):
        pass


def make_48k_frame(session_id="test", seq=0, amplitude=0.5, valid=480):
    pcm = np.ones(valid, dtype=np.float32) * amplitude
    return AudioFrame(
        session_id=session_id, epoch=0, seq=seq, sample_start=seq * 480,
        captured_ns=time.monotonic_ns(), sample_rate=48000, pcm=pcm,
        valid_samples=valid, discontinuity=(seq == 0),
    )


class TestRNNoiseProcessorLoadFailure(unittest.TestCase):
    @patch("voice_filtering.audio.rnnoise._load_native_library", side_effect=RNNoiseLoadError("not found"))
    def test_unavailable_when_library_missing(self, mock_load):
        proc = RNNoiseProcessor()
        self.assertFalse(proc.is_loaded)
        self.assertIn("not found", proc.load_error)

    @patch("voice_filtering.audio.rnnoise._load_native_library")
    def test_unavailable_when_create_returns_null(self, mock_load):
        mock_lib = MagicMock()
        mock_lib.rnnoise_get_frame_size.return_value = 480
        mock_lib.rnnoise_create.return_value = None
        mock_load.return_value = mock_lib
        proc = RNNoiseProcessor()
        self.assertFalse(proc.is_loaded)
        self.assertIn("NULL", proc.load_error)

    def test_process_raises_when_not_loaded(self):
        proc = RNNoiseProcessor()
        proc._loaded = False
        proc._state = None
        proc._load_error = "simulated"
        frame = make_48k_frame()
        with self.assertRaises(RuntimeError):
            proc.process(frame)


class TestRNNoiseProcessorFrameValidation(unittest.TestCase):
    def test_wrong_frame_size_rejected(self):
        proc = RNNoiseProcessor()
        proc._loaded = True
        proc._state = MagicMock()
        proc._state._lib = MagicMock()
        pcm = np.ones(100, dtype=np.float32)
        frame = AudioFrame(
            session_id="test", epoch=0, seq=0, sample_start=0,
            captured_ns=0, sample_rate=48000, pcm=pcm,
            valid_samples=100, discontinuity=False,
        )
        with self.assertRaises(ValueError):
            proc.process(frame)

    def test_non_finite_pcm_rejected(self):
        proc = RNNoiseProcessor()
        proc._loaded = True
        proc._state = MagicMock()
        pcm = np.array([float("nan")] * 480, dtype=np.float32)
        frame = AudioFrame(
            session_id="test", epoch=0, seq=0, sample_start=0,
            captured_ns=0, sample_rate=48000, pcm=pcm,
            valid_samples=480, discontinuity=False,
        )
        with self.assertRaises(ValueError):
            proc.process(frame)

    def test_empty_frame_returns_unchanged(self):
        proc = RNNoiseProcessor()
        proc._loaded = True
        proc._state = MagicMock()
        frame = AudioFrame(
            session_id="test", epoch=0, seq=0, sample_start=0,
            captured_ns=0, sample_rate=48000, pcm=np.zeros(480, dtype=np.float32),
            valid_samples=0, discontinuity=False,
        )
        result = proc.process(frame)
        self.assertEqual(result.valid_samples, 0)


class TestRNNoiseMetrics(unittest.TestCase):
    def test_avg_p95_empty(self):
        m = RNNoiseMetrics()
        self.assertIsNone(m.avg_ms)
        self.assertIsNone(m.p95_ms)
        self.assertEqual(m.total_frames, 0)

    def test_avg_p95_populated(self):
        m = RNNoiseMetrics()
        for i in range(100):
            m.record(0.001 * (i + 1))
        self.assertIsNotNone(m.avg_ms)
        self.assertIsNotNone(m.p95_ms)
        self.assertEqual(m.total_frames, 100)

    def test_reset_clears_window(self):
        m = RNNoiseMetrics()
        m.record(0.001)
        m.reset()
        self.assertIsNone(m.avg_ms)
        self.assertEqual(m.total_frames, 1)


class TestPipelineRNNoiseMode(unittest.TestCase):
    def setUp(self):
        self.source = FakeSource()
        self.resampler = StreamingResampler()
        self.transcriber = FakeTranscriber(["hello"])
        from voice_filtering.asr.whisper import ASRScheduler
        self.scheduler = ASRScheduler(self.transcriber, lambda e: None)
        self.rnnoise = FakeRNNoise(loaded=True)

    _SENTINEL = object()

    def _make_controller(self, rnnoise=_SENTINEL):
        rn = self.rnnoise if rnnoise is self._SENTINEL else rnnoise
        return PipelineControllerImpl(
            source=self.source, resampler=self.resampler,
            transcriber=self.transcriber, scheduler=self.scheduler,
            on_event=lambda e: None, rnnoise=rn,
        )

    def test_start_rnnoise_mode(self):
        ctrl = self._make_controller(self.rnnoise)
        result = ctrl.start("0", "rnnoise", False)
        self.assertEqual(result["state"], "listening")
        self.assertEqual(result["mode"], "rnnoise")
        ctrl.stop()

    def test_start_raw_mode(self):
        ctrl = self._make_controller(self.rnnoise)
        result = ctrl.start("0", "raw", False)
        self.assertEqual(result["state"], "listening")
        self.assertEqual(result["mode"], "raw")
        ctrl.stop()

    def test_switch_raw_to_rnnoise_while_listening(self):
        ctrl = self._make_controller(self.rnnoise)
        ctrl.start("0", "raw", False)
        time.sleep(0.05)
        result = ctrl.switch_mode("rnnoise")
        self.assertNotIn("error", result)
        ctrl._apply_mode_switch()
        snap = ctrl.snapshot()
        self.assertEqual(snap["mode"], "rnnoise")
        ctrl.stop()

    def test_switch_rnnoise_to_raw_while_listening(self):
        ctrl = self._make_controller(self.rnnoise)
        ctrl.start("0", "rnnoise", False)
        time.sleep(0.05)
        result = ctrl.switch_mode("raw")
        self.assertNotIn("error", result)
        ctrl._apply_mode_switch()
        snap = ctrl.snapshot()
        self.assertEqual(snap["mode"], "raw")
        ctrl.stop()

    def test_mode_switch_increments_epoch(self):
        ctrl = self._make_controller(self.rnnoise)
        ctrl.start("0", "raw", False)
        snap1 = ctrl.snapshot()
        ctrl.switch_mode("rnnoise")
        ctrl._apply_mode_switch()
        snap2 = ctrl.snapshot()
        self.assertGreater(snap2["epoch"], snap1["epoch"])
        ctrl.stop()

    def test_mode_switch_resets_rnnoise(self):
        ctrl = self._make_controller(self.rnnoise)
        ctrl.start("0", "raw", False)
        ctrl.switch_mode("rnnoise")
        ctrl._apply_mode_switch()
        self.assertEqual(self.rnnoise._reset_count, 2)
        ctrl.stop()

    def test_rnnoise_unavailable_rejects_mode(self):
        bad_rnnoise = FakeRNNoise(loaded=False, error="lib not found")
        ctrl = self._make_controller(rnnoise=bad_rnnoise)
        result = ctrl.switch_mode("rnnoise")
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], "STAGE_UNAVAILABLE")

    def test_rnnoise_not_injected_rejects_mode(self):
        ctrl = self._make_controller(rnnoise=None)
        result = ctrl.switch_mode("rnnoise")
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], "STAGE_UNAVAILABLE")

    def test_snapshot_rnnoise_ready(self):
        ctrl = self._make_controller(self.rnnoise)
        snap = ctrl.snapshot()
        self.assertEqual(snap["stages"]["rnnoise"]["status"], "ready")
        self.assertIn("70f1d25", snap["stages"]["rnnoise"]["model_revision"])

    def test_snapshot_rnnoise_unavailable(self):
        bad = FakeRNNoise(loaded=False, error="load fail")
        ctrl = self._make_controller(rnnoise=bad)
        snap = ctrl.snapshot()
        self.assertEqual(snap["stages"]["rnnoise"]["status"], "failed")
        self.assertEqual(snap["stages"]["rnnoise"]["reason"], "load fail")

    def test_snapshot_rnnoise_not_injected(self):
        ctrl = self._make_controller(rnnoise=None)
        snap = ctrl.snapshot()
        self.assertEqual(snap["stages"]["rnnoise"]["status"], "unavailable")

    def test_hush_still_unavailable(self):
        ctrl = self._make_controller(self.rnnoise)
        snap = ctrl.snapshot()
        self.assertEqual(snap["stages"]["hush"]["status"], "unavailable")

    def test_metrics_include_rnnoise_timing(self):
        ctrl = self._make_controller(self.rnnoise)
        ctrl.start("0", "rnnoise", False)
        frames = [make_48k_frame(seq=i) for i in range(5)]
        for f in frames:
            ctrl._capture_loop_body(f)
        snap = ctrl.snapshot()
        self.assertIn("rnnoise_avg_ms", snap["metrics"])
        self.assertIn("rnnoise_p95_ms", snap["metrics"])
        ctrl.stop()

    def test_invalid_mode_rejected(self):
        ctrl = self._make_controller(self.rnnoise)
        result = ctrl.switch_mode("unknown_mode")
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], "INVALID_MODE")

    def test_start_invalid_mode_rejected(self):
        ctrl = self._make_controller(self.rnnoise)
        result = ctrl.start("0", "combined", False)
        self.assertIn("error", result)

    def test_rnnoise_failure_stops_capture(self):
        class FailRNNoise(FakeRNNoise):
            def process(self, frame):
                raise RuntimeError("native crash")
        ctrl = self._make_controller(FailRNNoise(loaded=True))
        ctrl.start("0", "rnnoise", False)
        frame = make_48k_frame()
        ctrl._capture_loop_body(frame)
        snap = ctrl.snapshot()
        self.assertEqual(snap["state"], "error")
        self.assertEqual(snap["last_error"]["code"], "STAGE_FAILED")

    def test_reselect_same_mode_clears_pending(self):
        ctrl = self._make_controller(self.rnnoise)
        ctrl.start("0", "raw", False)
        time.sleep(0.05)
        ctrl.switch_mode("raw")
        snap = ctrl.snapshot()
        self.assertEqual(snap["pending_mode"], "raw")
        ctrl._apply_mode_switch()
        snap2 = ctrl.snapshot()
        self.assertIsNone(snap2["pending_mode"])
        self.assertEqual(snap2["mode"], "raw")
        self.assertEqual(snap2["epoch"], 0)
        ctrl.stop()

    def test_cancel_queued_switch_selects_current(self):
        ctrl = self._make_controller(self.rnnoise)
        ctrl.start("0", "raw", False)
        time.sleep(0.05)
        ctrl.switch_mode("rnnoise")
        snap1 = ctrl.snapshot()
        self.assertEqual(snap1["pending_mode"], "rnnoise")
        ctrl.switch_mode("raw")
        snap2 = ctrl.snapshot()
        self.assertEqual(snap2["pending_mode"], "raw")
        ctrl._apply_mode_switch()
        snap3 = ctrl.snapshot()
        self.assertEqual(snap3["mode"], "raw")
        self.assertEqual(snap3["epoch"], 0)
        ctrl.stop()

    def test_clear_rejected_while_listening(self):
        ctrl = self._make_controller(self.rnnoise)
        ctrl.start("0", "raw", False)
        result = ctrl.clear_transcript()
        self.assertIn("error", result)
        ctrl.stop()

    def test_stop_start_cycle_preserves_mode(self):
        ctrl = self._make_controller(self.rnnoise)
        ctrl.start("0", "rnnoise", False)
        ctrl.stop()
        ctrl.start("0", "raw", False)
        snap = ctrl.snapshot()
        self.assertEqual(snap["mode"], "raw")
        ctrl.stop()


class TestPipelineRNNoiseBypass(unittest.TestCase):
    def test_raw_mode_bypasses_rnnoise(self):
        rnnoise = FakeRNNoise(loaded=True)
        source = FakeSource()
        resampler = StreamingResampler()
        transcriber = FakeTranscriber(["hello"])
        from voice_filtering.asr.whisper import ASRScheduler
        scheduler = ASRScheduler(transcriber, lambda e: None)
        ctrl = PipelineControllerImpl(
            source=source, resampler=resampler, transcriber=transcriber,
            scheduler=scheduler, on_event=lambda e: None, rnnoise=rnnoise,
        )
        ctrl.start("0", "raw", False)
        frame = make_48k_frame()
        ctrl._capture_loop_body(frame)
        self.assertEqual(rnnoise._process_count, 0)
        ctrl.stop()


class TestPipelineControllerModes(unittest.TestCase):
    def test_switch_to_hush_rejected(self):
        source = FakeSource()
        resampler = StreamingResampler()
        transcriber = FakeTranscriber()
        from voice_filtering.asr.whisper import ASRScheduler
        scheduler = ASRScheduler(transcriber, lambda e: None)
        rnnoise = FakeRNNoise(loaded=True)
        ctrl = PipelineControllerImpl(
            source=source, resampler=resampler, transcriber=transcriber,
            scheduler=scheduler, on_event=lambda e: None, rnnoise=rnnoise,
        )
        result = ctrl.switch_mode("hush")
        self.assertIn("error", result)

    def test_switch_to_combined_rejected(self):
        source = FakeSource()
        resampler = StreamingResampler()
        transcriber = FakeTranscriber()
        from voice_filtering.asr.whisper import ASRScheduler
        scheduler = ASRScheduler(transcriber, lambda e: None)
        rnnoise = FakeRNNoise(loaded=True)
        ctrl = PipelineControllerImpl(
            source=source, resampler=resampler, transcriber=transcriber,
            scheduler=scheduler, on_event=lambda e: None, rnnoise=rnnoise,
        )
        result = ctrl.switch_mode("combined")
        self.assertIn("error", result)


class ControllableTranscriber:
    """Fake transcriber that blocks decode until released, for testing
    reset-during-in-flight-decode."""
    def __init__(self):
        self.decode_started = threading.Event()
        self.decode_release = threading.Event()
        self._loaded = True
        self._load_error = None

    @property
    def is_loaded(self):
        return self._loaded

    @property
    def load_error(self):
        return self._load_error

    def decode(self, pcm16k):
        self.decode_started.set()
        self.decode_release.wait(timeout=5.0)
        return "hello"


class TestModeProvenance(unittest.TestCase):
    """Regression: TranscriptEvent.mode must reflect the actual pipeline mode,
    not be hardcoded to 'raw'. Tests exercise run_step with valid 16kHz audio."""

    def _make_16k_frame(self, session_id="s1", epoch=0, seq=0,
                        amplitude=0.5, samples=160):
        pcm = np.full(samples, amplitude, dtype=np.float32)
        return AudioFrame(
            session_id=session_id, epoch=epoch, seq=seq,
            sample_start=seq * 160, captured_ns=0, sample_rate=16000,
            pcm=pcm, valid_samples=samples, discontinuity=False,
        )

    def _make_scheduler(self, transcriber=None):
        self.events = []
        if transcriber is None:
            transcriber = FakeTranscriber(["hello"])
        self.transcriber = transcriber
        return ASRScheduler(self.transcriber, lambda e: self.events.append(e))

    def _speech_frames(self, count, session_id="s1", epoch=0, start_seq=0):
        """Generate count frames above -45 dBFS threshold (amplitude 0.5)."""
        return [
            self._make_16k_frame(session_id=session_id, epoch=epoch,
                                 seq=start_seq + i, amplitude=0.5)
            for i in range(count)
        ]

    def _silence_frames(self, count, session_id="s1", epoch=0, start_seq=100):
        """Generate count frames below threshold (amplitude 0.0)."""
        return [
            self._make_16k_frame(session_id=session_id, epoch=0,
                                 seq=start_seq + i, amplitude=0.0)
            for i in range(count)
        ]

    def _feed_and_step(self, sched, frames):
        for f in frames:
            sched.push_audio(f)
        sched.run_step()

    def test_scheduler_start_accepts_mode(self):
        sched = self._make_scheduler()
        sched.start("s1", 0, mode="rnnoise")
        with sched._lock:
            self.assertEqual(sched._mode, "rnnoise")

    def test_scheduler_reset_accepts_mode(self):
        sched = self._make_scheduler()
        sched.start("s1", 0, mode="raw")
        sched.reset("s1", 1, mode="rnnoise")
        with sched._lock:
            self.assertEqual(sched._mode, "rnnoise")
            self.assertEqual(sched._epoch, 1)

    def test_transcript_event_carries_rnnoise_mode(self):
        sched = self._make_scheduler()
        sched.start("s1", 0, mode="rnnoise")
        self._feed_and_step(sched, self._speech_frames(5))
        self._feed_and_step(sched, self._silence_frames(60))
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0].mode, "rnnoise")
        self.assertEqual(self.events[0].epoch, 0)

    def test_transcript_event_carries_raw_mode(self):
        sched = self._make_scheduler()
        sched.start("s1", 0, mode="raw")
        self._feed_and_step(sched, self._speech_frames(5))
        self._feed_and_step(sched, self._silence_frames(60))
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0].mode, "raw")

    def test_mode_switch_updates_event_provenance(self):
        sched = self._make_scheduler()
        sched.start("s1", 0, mode="raw")
        self._feed_and_step(sched, self._speech_frames(5))
        self._feed_and_step(sched, self._silence_frames(60))
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0].mode, "raw")

        sched.reset("s1", 1, mode="rnnoise")
        self._feed_and_step(sched, self._speech_frames(5, epoch=1, start_seq=10))
        self._feed_and_step(sched, self._silence_frames(60, start_seq=110))
        self.assertEqual(len(self.events), 2)
        self.assertEqual(self.events[1].mode, "rnnoise")
        self.assertEqual(self.events[1].epoch, 1)

    def test_stale_decode_rejected_on_reset_during_inflight(self):
        blocker = ControllableTranscriber()
        sched = self._make_scheduler(blocker)
        sched.start("s1", 0, mode="raw")
        for f in self._speech_frames(5):
            sched.push_audio(f)
        for f in self._silence_frames(60):
            sched.push_audio(f)

        decode_thread = threading.Thread(target=sched.run_step)
        decode_thread.start()
        try:
            blocker.decode_started.wait(timeout=2.0)
            self.assertTrue(blocker.decode_started.is_set())

            sched.reset("s1", 1, mode="rnnoise")
        finally:
            blocker.decode_release.set()
        decode_thread.join(timeout=2.0)

        self.assertEqual(len(self.events), 0)

        self._feed_and_step(sched, self._speech_frames(5, epoch=1, start_seq=10))
        self._feed_and_step(sched, self._silence_frames(60, start_seq=110))
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0].mode, "rnnoise")
        self.assertEqual(self.events[0].epoch, 1)

    def test_ingress_cleared_on_reset(self):
        sched = self._make_scheduler()
        sched.start("s1", 0, mode="raw")
        for i in range(5):
            sched.push_audio(self._make_16k_frame(seq=i))
        self.assertEqual(len(sched._ingress), 5)
        sched.reset("s1", 1, mode="rnnoise")
        self.assertEqual(len(sched._ingress), 0)

    def test_stale_frames_in_run_step_batch_rejected(self):
        sched = self._make_scheduler()
        sched.start("s1", 0, mode="raw")
        for f in self._speech_frames(3):
            sched.push_audio(f)
        frames = []
        with sched._lock:
            while sched._ingress:
                frames.append(sched._ingress.popleft())
        sched.reset("s1", 1, mode="rnnoise")
        for f in frames:
            sched.push_audio(f)
        sched.run_step()
        self.assertEqual(len(self.events), 0)


if __name__ == "__main__":
    unittest.main()
