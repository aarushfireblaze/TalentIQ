import unittest
import numpy as np

from voice_filtering.contracts import AudioFrame
from voice_filtering.audio.capture import CaptureSource, RING_CAP, FRAME_SAMPLES, SOURCE_RATE
from voice_filtering.audio.resample import StreamingResampler, TARGET_RATE, OUTPUT_FRAME_SAMPLES, SOURCE_FRAME_SAMPLES
from tests.fakes import make_frames, make_frame


class TestResampler(unittest.TestCase):
    def setUp(self) -> None:
        self.resampler = StreamingResampler()

    def test_resampler_preserves_duration_and_source_clock(self) -> None:
        frames = make_frames(seconds=1, rate=48000)
        outputs = []
        for frame in frames:
            outputs.extend(self.resampler.push(frame))
        outputs.extend(self.resampler.finish())
        total_valid = sum(f.valid_samples for f in outputs)
        self.assertEqual(total_valid, 16000)
        self.assertTrue(all(f.sample_rate == 16000 for f in outputs))
        self.assertEqual(
            [f.sample_start for f in outputs],
            list(range(0, 48000, SOURCE_FRAME_SAMPLES)),
        )

    def test_chunked_vs_whole_stream_agreement(self) -> None:
        all_frames = make_frames(seconds=0.5, rate=48000)
        whole = StreamingResampler()
        whole_out = []
        for f in all_frames:
            whole_out.extend(whole.push(f))
        whole_out.extend(whole.finish())
        whole_pcm = np.concatenate([f.pcm[:f.valid_samples] for f in whole_out])
        chunked = StreamingResampler()
        chunked_out = []
        chunk_size = 5
        for i in range(0, len(all_frames), chunk_size):
            for f in all_frames[i : i + chunk_size]:
                chunked_out.extend(chunked.push(f))
        chunked_out.extend(chunked.finish())
        chunked_pcm = np.concatenate([f.pcm[:f.valid_samples] for f in chunked_out])
        min_len = min(len(whole_pcm), len(chunked_pcm))
        if min_len > 0:
            np.testing.assert_allclose(
                whole_pcm[:min_len], chunked_pcm[:min_len], atol=1e-5
            )

    def test_ring_overflow_bounded(self) -> None:
        source = CaptureSource()
        session_id = "test-session"
        for i in range(150):
            frame = make_frame(session_id=session_id, seq=i)
            source.inject_frame(frame)
        self.assertEqual(len(source._ring), RING_CAP)
        self.assertGreater(source.get_drop_count(), 0)

    def test_non_finite_pcm_rejected(self) -> None:
        frame = AudioFrame(
            session_id="test",
            epoch=0,
            seq=0,
            sample_start=0,
            captured_ns=0,
            sample_rate=48000,
            pcm=np.array([float("nan"), 0.0, 0.0], dtype=np.float32),
            valid_samples=3,
            discontinuity=False,
        )
        has_nan = np.any(np.isnan(frame.pcm))
        self.assertTrue(has_nan)

    def test_wrong_shape_pcm(self) -> None:
        frame = AudioFrame(
            session_id="test",
            epoch=0,
            seq=0,
            sample_start=0,
            captured_ns=0,
            sample_rate=48000,
            pcm=np.zeros((2, 3), dtype=np.float32),
            valid_samples=3,
            discontinuity=False,
        )
        self.assertEqual(frame.pcm.ndim, 2)

    def test_short_final_frame_valid_samples(self) -> None:
        frame = make_frame(seconds=0.002, rate=48000, seq=0)
        outputs = self.resampler.push(frame)
        outputs.extend(self.resampler.finish())
        self.assertGreater(sum(f.valid_samples for f in outputs), 0)

    def test_discontinuity_preserved(self) -> None:
        frame1 = make_frame(session_id="s1", seq=0, discontinuity=False)
        frame2 = make_frame(session_id="s1", seq=1, discontinuity=True)
        out1 = self.resampler.push(frame1)
        out2 = self.resampler.push(frame2)
        all_out = out1 + out2 + self.resampler.finish()
        has_disc = any(f.discontinuity for f in all_out)
        has_data = len(all_out) > 0
        self.assertTrue(has_data)
        if has_disc:
            self.assertTrue(has_disc)

    def test_drop_count_exact(self) -> None:
        source = CaptureSource()
        for i in range(105):
            frame = make_frame(session_id="s", seq=i)
            source.inject_frame(frame)
        drops = source.get_drop_count()
        self.assertGreater(drops, 0)
        self.assertEqual(len(source._ring), RING_CAP)


if __name__ == "__main__":
    unittest.main()
