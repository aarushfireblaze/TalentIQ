from __future__ import annotations

import time
import unittest

import numpy as np

from voice_filtering.contracts import AudioFrame
from voice_filtering.pipeline.controller import PipelineControllerImpl


class FakeSource:
    def __init__(self):
        self.started = False
        self.stopped = False

    def start(self, *, device_id, session_id):
        self.started = True

    def stop(self):
        self.stopped = True

    def read_frame(self, timeout_s):
        return None


class FakeTranscriber:
    is_loaded = True
    load_error = None


class Stage:
    is_loaded = True
    load_error = None
    metrics = type("Metrics", (), {"avg_ms": 1.0, "p95_ms": 1.0, "total_frames": 1})()

    def __init__(self, name, calls):
        self.name = name
        self.calls = calls
        self.fail = False

    def reset(self):
        return None

    def process(self, frame):
        if self.fail:
            raise RuntimeError(self.name + " failed")
        self.calls.append((self.name, frame.sample_rate))
        return frame


class Resampler:
    def __init__(self, calls):
        self.calls = calls

    def reset(self):
        return None

    def finish(self):
        return []

    def push(self, frame):
        self.calls.append(("resampler", frame.sample_rate))
        return [AudioFrame(
            session_id=frame.session_id, epoch=frame.epoch, seq=frame.seq,
            sample_start=frame.sample_start, captured_ns=frame.captured_ns,
            sample_rate=16000, pcm=frame.pcm[:160], valid_samples=160,
            discontinuity=frame.discontinuity,
        )]


class Scheduler:
    def __init__(self, calls):
        self.calls = calls
        self.mode = None
        self.frames = []

    def start(self, session_id, epoch, mode):
        self.mode = mode

    def finish(self, timeout_s):
        return True

    def push_audio(self, frame):
        self.calls.append(("asr", frame.sample_rate))
        self.frames.append(frame)

    def run_step(self):
        return None


class TestCombinedPipeline(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.source = FakeSource()
        self.rnnoise = Stage("rnnoise", self.calls)
        self.hush = Stage("hush", self.calls)
        self.scheduler = Scheduler(self.calls)
        self.controller = PipelineControllerImpl(
            source=self.source,
            resampler=Resampler(self.calls),
            transcriber=FakeTranscriber(),
            scheduler=self.scheduler,
            on_event=lambda event: None,
            rnnoise=self.rnnoise,
            hush=self.hush,
        )

    def frame(self):
        return AudioFrame(
            session_id="old", epoch=99, seq=0, sample_start=0,
            captured_ns=time.monotonic_ns(), sample_rate=48000,
            pcm=np.ones(480, dtype=np.float32), valid_samples=480,
            discontinuity=False,
        )

    def test_start_ignores_legacy_mode_and_uses_combined(self):
        result = self.controller.start("0", False)
        self.assertEqual(result["state"], "listening")
        self.assertEqual(result["mode"], "combined")
        self.assertEqual(self.scheduler.mode, "combined")
        self.controller.stop()

    def test_combined_order_has_one_resampling_boundary(self):
        self.controller.start("0", False)
        self.assertTrue(self.controller._capture_loop_body(self.frame()))
        self.assertEqual(self.calls, [
            ("rnnoise", 48000), ("resampler", 48000), ("hush", 16000), ("asr", 16000),
        ])
        self.assertEqual(self.scheduler.frames[0].session_id, self.controller.snapshot()["session_id"])
        self.controller.stop()

    def test_missing_rnnoise_blocks_capture(self):
        self.rnnoise.is_loaded = False
        self.rnnoise.load_error = "native library missing"
        result = self.controller.start("0", False)
        self.assertEqual(result["error"]["stage"], "rnnoise")
        self.assertFalse(self.source.started)

    def test_missing_hush_blocks_capture(self):
        self.hush.is_loaded = False
        self.hush.load_error = "model missing"
        result = self.controller.start("0", False)
        self.assertEqual(result["error"]["stage"], "hush")
        self.assertFalse(self.source.started)

    def test_stage_failure_never_falls_back(self):
        self.controller.start("0", False)
        self.hush.fail = True
        self.assertFalse(self.controller._capture_loop_body(self.frame()))
        self.assertEqual(self.controller.snapshot()["last_error"]["stage"], "hush")
        self.assertEqual(self.scheduler.frames, [])
        self.controller.stop()

    def test_mode_switch_api_is_absent(self):
        self.assertFalse(hasattr(self.controller, "switch_mode"))


if __name__ == "__main__":
    unittest.main()
