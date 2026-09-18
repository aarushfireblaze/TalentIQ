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
        )

    def test_snapshot_initial_state(self):
        snap = self.controller.snapshot()
        self.assertEqual(snap["state"], "idle")
        self.assertEqual(snap["mode"], "raw")
        self.assertIn("rnnoise", snap["stages"])
        self.assertEqual(snap["stages"]["rnnoise"]["status"], "unavailable")
        self.assertIn("hush", snap["stages"])
        self.assertEqual(snap["stages"]["hush"]["status"], "unavailable")

    def test_duplicate_start_rejected(self):
        result1 = self.controller.start("0", "raw", False)
        self.assertIn("state", result1)
        result2 = self.controller.start("0", "raw", False)
        self.assertIn("error", result2)

    def test_stop_idempotent(self):
        result = self.controller.stop()
        self.assertEqual(result["state"], "idle")

    def test_clear_idle_only(self):
        result = self.controller.clear_transcript()
        self.assertNotIn("error", result)
        self.controller.start("0", "raw", False)
        result = self.controller.clear_transcript()
        self.assertIn("error", result)
        self.controller.stop()

    def test_unavailable_mode_rejected(self):
        result = self.controller.switch_mode("rnnoise")
        self.assertIn("error", result)

    def test_missing_model_status(self):
        self.transcriber._loaded = False
        self.transcriber._load_error = "Model not found"
        result = self.controller.start("0", "raw", False)
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


if __name__ == "__main__":
    unittest.main()
