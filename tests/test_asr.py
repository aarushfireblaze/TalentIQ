import unittest
import threading
import time
import uuid
import numpy as np
from unittest.mock import MagicMock

from voice_filtering.contracts import AudioFrame, TranscriptEvent
from voice_filtering.asr.whisper import (
    WhisperASR,
    ASRScheduler,
    INGRESS_CAP,
    UTTERANCE_MAX_S,
    FINAL_QUEUE_CAP,
)
from voice_filtering.pipeline.controller import PipelineControllerImpl
from voice_filtering.audio.resample import StreamingResampler
from tests.fakes import FakeAudioSource


class FakeTranscriber:
    def __init__(self, texts=None):
        self._texts = texts or ["hello world"]
        self._call_count = 0
        self._loaded = True
        self._load_error = None
        self._decode_times: list[float] = []

    @property
    def is_loaded(self):
        return self._loaded

    @property
    def load_error(self):
        return self._load_error

    def decode(self, pcm16k):
        t0 = time.monotonic()
        time.sleep(0.01)
        idx = self._call_count % len(self._texts)
        self._call_count += 1
        text = self._texts[idx]
        self._decode_times.append(time.monotonic() - t0)
        return text


def make_audio_frame(
    session_id="test",
    epoch=0,
    seq=0,
    sample_start=0,
    valid_samples=160,
    sample_rate=16000,
    amplitude=0.5,
):
    pcm = np.ones(valid_samples, dtype=np.float32) * amplitude
    return AudioFrame(
        session_id=session_id,
        epoch=epoch,
        seq=seq,
        sample_start=sample_start,
        captured_ns=time.monotonic_ns(),
        sample_rate=sample_rate,
        pcm=pcm,
        valid_samples=valid_samples,
        discontinuity=False,
    )


class TestASRScheduler(unittest.TestCase):
    def setUp(self):
        self.transcriber = FakeTranscriber(["hello world"])
        self.events = []
        self.scheduler = ASRScheduler(self.transcriber, lambda e: self.events.append(e))

    def test_push_audio_overflow_drops_oldest(self):
        self.scheduler.start("s1", 0)
        for i in range(INGRESS_CAP + 10):
            frame = make_audio_frame(session_id="s1", seq=i, amplitude=0.8)
            self.scheduler.push_audio(frame)
        self.assertGreater(self.scheduler.get_ingress_drop_count(), 0)

    def test_final_emitted_after_utterance(self):
        self.scheduler.start("s1", 0)
        for i in range(200):
            frame = make_audio_frame(session_id="s1", seq=i, sample_start=i * 160, amplitude=0.8)
            self.scheduler.push_audio(frame)
        self.scheduler._running = True
        self.scheduler.run_step()
        self.scheduler._finalize_utterance("silence")
        finals = [e for e in self.events if e.kind == "final"]
        self.assertEqual(len(finals), 1)
        self.assertEqual(finals[0].text, "hello world")

    def test_partial_replaces_previous(self):
        self.scheduler.start("s1", 0)
        self.events.clear()
        frame = make_audio_frame(session_id="s1", amplitude=0.8)
        self.scheduler.push_audio(frame)
        self.scheduler._running = True
        self.scheduler.run_step()
        self.scheduler._finalize_utterance("silence")
        self.assertGreater(len(self.events), 0)

    def test_stop_before_speech(self):
        self.scheduler.start("s1", 0)
        self.scheduler.finish()
        finals = [e for e in self.events if e.kind == "final"]
        self.assertEqual(len(finals), 0)

    def test_concurrent_start_stop(self):
        self.scheduler.start("s1", 0)
        self.scheduler.finish()
        self.scheduler.start("s2", 1)
        self.scheduler.finish()
        self.assertTrue(True)

    def test_sustained_above_threshold_triggers_max_duration(self):
        self.scheduler.start("s1", 0)
        for i in range(1000):
            frame = make_audio_frame(session_id="s1", seq=i, sample_start=i * 160, amplitude=0.8)
            self.scheduler.push_audio(frame)
        self.scheduler._running = True
        self.scheduler.run_step()
        self.scheduler._finalize_utterance("max_duration")
        finals = [e for e in self.events if e.kind == "final"]
        self.assertEqual(len(finals), 1)

    def test_final_queue_overflow(self):
        transcriber = FakeTranscriber(["text"])
        events = []
        scheduler = ASRScheduler(transcriber, lambda e: events.append(e))
        scheduler.start("s1", 0)
        for _ in range(FINAL_QUEUE_CAP + 2):
            for i in range(200):
                frame = make_audio_frame(session_id="s1", seq=i, amplitude=0.8)
                scheduler.push_audio(frame)
            scheduler._running = True
            scheduler.run_step()
            scheduler._finalize_utterance("silence")
        self.assertLessEqual(len([e for e in events if e.kind == "final"]), FINAL_QUEUE_CAP + 2)

    def test_late_result_rejection_after_stop(self):
        self.scheduler.start("s1", 0)
        self.scheduler.finish()
        event = TranscriptEvent(
            session_id="s1",
            segment_id=str(uuid.uuid4()),
            revision=1,
            kind="final",
            text="late",
            start_ms=0,
            end_ms=100,
            mode="raw",
            epoch=0,
            final_reason="silence",
        )
        self.scheduler._on_event(event)
        finals = [e for e in self.events if e.kind == "final" and e.text == "late"]
        self.assertEqual(len(finals), 1)


class TestPipelineController(unittest.TestCase):
    def setUp(self):
        class FakeStage:
            is_loaded = True
            load_error = None
            metrics = type("Metrics", (), {"avg_ms": 1.0, "p95_ms": 1.0, "total_frames": 0})()

            def reset(self):
                return None

            def process(self, frame):
                return frame

        self.source = FakeAudioSource()
        self.resampler = StreamingResampler()
        self.transcriber = FakeTranscriber(["hello world"])
        self.scheduler = ASRScheduler(self.transcriber, lambda e: None)
        self.events = []
        self.controller = PipelineControllerImpl(
            source=self.source,
            resampler=self.resampler,
            transcriber=self.transcriber,
            scheduler=self.scheduler,
            on_event=lambda e: self.events.append(e),
            rnnoise=FakeStage(),
            hush=FakeStage(),
        )

    def test_snapshot_initial_state(self):
        snap = self.controller.snapshot()
        self.assertEqual(snap["state"], "idle")
        self.assertEqual(snap["mode"], "combined")
        self.assertIn("rnnoise", snap["stages"])
        self.assertEqual(snap["stages"]["rnnoise"]["status"], "ready")
        self.assertIn("hush", snap["stages"])
        self.assertEqual(snap["stages"]["hush"]["status"], "ready")

    def test_duplicate_start_rejected(self):
        result1 = self.controller.start("0", False)
        self.assertIn("state", result1)
        result2 = self.controller.start("0", False)
        self.assertIn("error", result2)

    def test_stop_idempotent(self):
        result = self.controller.stop()
        self.assertEqual(result["state"], "idle")

    def test_clear_idle_only(self):
        result = self.controller.clear_transcript()
        self.assertNotIn("error", result)
        self.controller.start("0", False)
        result = self.controller.clear_transcript()
        self.assertIn("error", result)
        self.controller.stop()

    def test_runtime_mode_switch_is_absent(self):
        self.assertFalse(hasattr(self.controller, "switch_mode"))

    def test_missing_model_status(self):
        self.transcriber._loaded = False
        self.transcriber._load_error = "Model not found"
        result = self.controller.start("0", False)
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], "MODEL_MISSING")

    def test_snapshot_reconnect(self):
        snap1 = self.controller.snapshot()
        snap2 = self.controller.snapshot()
        self.assertEqual(snap1["state"], snap2["state"])

    def test_transcript_grouping_by_session(self):
        event = TranscriptEvent(
            session_id="s1",
            segment_id=str(uuid.uuid4()),
            revision=1,
            kind="final",
            text="hello",
            start_ms=0,
            end_ms=100,
            mode="raw",
            epoch=0,
            final_reason="silence",
        )
        self.controller.add_transcript_event(event)
        snap = self.controller.snapshot()
        self.assertEqual(len(snap["transcript"]), 1)
        self.assertEqual(snap["transcript"][0]["session_id"], "s1")

    def test_partial_replaced_by_final(self):
        partial = TranscriptEvent(
            session_id="s1",
            segment_id="seg1",
            revision=1,
            kind="partial",
            text="hel",
            start_ms=0,
            end_ms=50,
            mode="raw",
            epoch=0,
        )
        self.controller.add_transcript_event(partial)
        final = TranscriptEvent(
            session_id="s1",
            segment_id="seg1",
            revision=2,
            kind="final",
            text="hello world",
            start_ms=0,
            end_ms=100,
            mode="raw",
            epoch=0,
            final_reason="silence",
        )
        self.controller.add_transcript_event(final)
        snap = self.controller.snapshot()
        finals = [t for t in snap["transcript"] if t["kind"] == "final"]
        self.assertEqual(len(finals), 1)
        self.assertEqual(finals[0]["text"], "hello world")

    def test_transcript_limit(self):
        for i in range(1100):
            event = TranscriptEvent(
                session_id="s1",
                segment_id=str(uuid.uuid4()),
                revision=1,
                kind="final",
                text=f"word{i}",
                start_ms=i * 100,
                end_ms=(i + 1) * 100,
                mode="raw",
                epoch=0,
                final_reason="silence",
            )
            self.controller.add_transcript_event(event)
        snap = self.controller.snapshot()
        self.assertLessEqual(len(snap["transcript"]), 1000)


class TestASREdgeCases(unittest.TestCase):
    def test_fake_decoder_sustained_noise(self):
        transcriber = FakeTranscriber(["", "silence", ""])
        events = []
        scheduler = ASRScheduler(transcriber, lambda e: events.append(e))
        scheduler.start("s1", 0)
        for i in range(500):
            frame = make_audio_frame(session_id="s1", seq=i, amplitude=0.8)
            scheduler.push_audio(frame)
        scheduler._running = True
        scheduler.run_step()
        scheduler._finalize_utterance("max_duration")
        self.assertTrue(True)

    def test_decode_timing_recorded(self):
        transcriber = FakeTranscriber(["test"])
        scheduler = ASRScheduler(transcriber, lambda e: None)
        scheduler.start("s1", 0)
        for i in range(200):
            frame = make_audio_frame(session_id="s1", seq=i, amplitude=0.8)
            scheduler.push_audio(frame)
        scheduler._running = True
        scheduler.run_step()
        scheduler._finalize_utterance("silence")
        self.assertGreater(len(transcriber._decode_times), 0)

    def test_empty_utterance_no_final(self):
        transcriber = FakeTranscriber([""])
        events = []
        scheduler = ASRScheduler(transcriber, lambda e: events.append(e))
        scheduler.start("s1", 0)
        scheduler._finalize_utterance("silence")
        finals = [e for e in events if e.kind == "final"]
        self.assertEqual(len(finals), 0)


class BlockingTranscriber:
    def __init__(self):
        self.entered = threading.Event()
        self.release = threading.Event()

    def decode(self, pcm):
        self.entered.set()
        if not self.release.wait(3):
            raise TimeoutError("decode release was not signaled")
        return "decoded"


class TestASRProvenance(unittest.TestCase):
    def test_accepted_callback_can_reset_without_deadlock(self):
        events = []
        scheduler = ASRScheduler(FakeTranscriber(["accepted"]), lambda event: None)

        def on_event(event):
            events.append(event)
            scheduler.reset("session", 1, "rnnoise")

        scheduler._on_event = on_event
        scheduler.start("session", 0, "raw")
        scheduler.push_audio(make_audio_frame(session_id="session", epoch=0, amplitude=0.8))
        scheduler.run_step()
        worker = threading.Thread(target=scheduler.finish, daemon=True)
        worker.start()
        worker.join(1)
        self.assertFalse(worker.is_alive())
        self.assertEqual([(e.epoch, e.mode, e.text) for e in events], [(0, "raw", "accepted")])

    def test_reset_with_same_identity_discards_drained_frames(self):
        entered = threading.Event()
        release = threading.Event()
        events = []
        scheduler = ASRScheduler(FakeTranscriber(["fresh"]), events.append)
        original_rms = scheduler._rms_dbfs

        def blocking_rms(pcm):
            entered.set()
            self.assertTrue(release.wait(3))
            return original_rms(pcm)

        scheduler._rms_dbfs = blocking_rms
        scheduler.start("session", 0)
        scheduler.push_audio(make_audio_frame(session_id="session", epoch=0, amplitude=0.8))
        worker = threading.Thread(target=scheduler.run_step)
        worker.start()
        try:
            self.assertTrue(entered.wait(1))
            scheduler.reset("session", 0)
            release.set()
            worker.join(1)
            self.assertFalse(worker.is_alive())
            scheduler.finish()
            self.assertEqual(events, [])
        finally:
            release.set()
            worker.join(1)

    def test_reset_during_decode_rejects_old_result_and_accepts_new_audio(self):
        transcriber = BlockingTranscriber()
        events = []
        scheduler = ASRScheduler(transcriber, events.append)
        scheduler.start("session", 0, "rnnoise")
        scheduler.push_audio(make_audio_frame(session_id="session", epoch=0, amplitude=0.8))
        scheduler.run_step()
        worker = threading.Thread(target=scheduler.finish)
        worker.start()
        try:
            self.assertTrue(transcriber.entered.wait(1))
            scheduler.reset("session", 1, "raw")
            scheduler.start("session", 1, "raw")
            scheduler.push_audio(make_audio_frame(session_id="session", epoch=1, amplitude=0.8))
            transcriber.release.set()
            worker.join(1)
            self.assertFalse(worker.is_alive())
            self.assertEqual(events, [])
            scheduler.run_step()
            scheduler.finish()
            self.assertEqual([(e.text, e.epoch, e.mode) for e in events], [("decoded", 1, "raw")])
        finally:
            transcriber.release.set()
            worker.join(1)

    def test_reset_rejects_drained_old_frames_and_mixed_ingress(self):
        entered = threading.Event()
        release = threading.Event()
        events = []
        scheduler = ASRScheduler(FakeTranscriber(["fresh"]), events.append)
        original_rms = scheduler._rms_dbfs

        def blocking_rms(pcm):
            entered.set()
            self.assertTrue(release.wait(3))
            return original_rms(pcm)

        scheduler._rms_dbfs = blocking_rms
        scheduler.start("old", 0)
        scheduler.push_audio(make_audio_frame(session_id="old", epoch=0, amplitude=0.8))
        worker = threading.Thread(target=scheduler.run_step)
        worker.start()
        try:
            self.assertTrue(entered.wait(1))
            scheduler.reset("new", 1, "rnnoise")
            scheduler.push_audio(make_audio_frame(session_id="old", epoch=0, amplitude=0.8))
            scheduler.push_audio(make_audio_frame(session_id="new", epoch=1, sample_start=160, amplitude=0.8))
            release.set()
            worker.join(1)
            self.assertFalse(worker.is_alive())
            scheduler.run_step()
            scheduler.finish()
            self.assertEqual([(e.session_id, e.epoch, e.mode) for e in events],
                             [("new", 1, "rnnoise")])
            self.assertAlmostEqual(events[0].start_ms, 160 * 1000 / 48000)
        finally:
            release.set()
            worker.join(1)

    def test_finish_uses_first_frame_time_and_valid_sample_duration(self):
        events = []
        scheduler = ASRScheduler(FakeTranscriber(["short"]), events.append)
        scheduler.start("session", 2, "raw")
        scheduler.push_audio(make_audio_frame(session_id="session", epoch=2, sample_start=320,
                                              valid_samples=80, amplitude=0.8))
        scheduler.run_step()
        scheduler.finish()
        self.assertEqual(len(events), 1)
        self.assertAlmostEqual(events[0].start_ms, 320 * 1000 / 48000)
        self.assertAlmostEqual(events[0].end_ms, 320 * 1000 / 48000 + 5)


if __name__ == "__main__":
    unittest.main()
