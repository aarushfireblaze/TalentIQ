from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from voice_filtering.audio.rnnoise import FRAME_SIZE, RNNoiseLoadError, RNNoiseMetrics, RNNoiseProcessor
from voice_filtering.contracts import AudioFrame


def make_frame(samples=480, valid_samples=480):
    return AudioFrame(
        session_id="test", epoch=0, seq=0, sample_start=0, captured_ns=0,
        sample_rate=48000, pcm=np.ones(samples, dtype=np.float32),
        valid_samples=valid_samples, discontinuity=False,
    )


class TestRNNoiseProcessor(unittest.TestCase):
    @patch("voice_filtering.audio.rnnoise._load_native_library", side_effect=RNNoiseLoadError("not found"))
    def test_reports_missing_native_library(self, mocked_load):
        processor = RNNoiseProcessor()
        self.assertFalse(processor.is_loaded)
        self.assertIn("not found", processor.load_error)

    def test_rejects_invalid_frame_size(self):
        processor = RNNoiseProcessor()
        processor._loaded = True
        processor._state = MagicMock()
        processor._state._lib = MagicMock()
        with self.assertRaises(ValueError):
            processor.process(make_frame(samples=100, valid_samples=100))

    def test_rejects_non_finite_samples(self):
        processor = RNNoiseProcessor()
        processor._loaded = True
        processor._state = MagicMock()
        frame = make_frame()
        frame = AudioFrame(**{**frame.__dict__, "pcm": np.full(FRAME_SIZE, np.nan, dtype=np.float32)})
        with self.assertRaises(ValueError):
            processor.process(frame)


class TestRNNoiseMetrics(unittest.TestCase):
    def test_records_and_resets_processing_window(self):
        metrics = RNNoiseMetrics()
        metrics.record(0.001)
        self.assertEqual(metrics.total_frames, 1)
        self.assertIsNotNone(metrics.avg_ms)
        self.assertIsNotNone(metrics.p95_ms)
        metrics.reset()
        self.assertIsNone(metrics.avg_ms)
        self.assertEqual(metrics.total_frames, 1)


if __name__ == "__main__":
    unittest.main()
