import unittest
import numpy as np
from voice_filtering.contracts import AudioFrame
from voice_filtering.audio.resample import StreamingResampler, TARGET_RATE, SOURCE_RATE

class TestStreamingResamplerMetadata(unittest.TestCase):
    def test_streaming_metadata_preservation(self):
        resampler = StreamingResampler()
        frame1 = AudioFrame(
            session_id="session1", epoch=0, seq=0,
            sample_start=0, captured_ns=1000,
            sample_rate=SOURCE_RATE, pcm=np.ones(480, dtype=np.float32),
            valid_samples=480, discontinuity=False
        )
        out1 = resampler.push(frame1)
        
        frame2 = AudioFrame(
            session_id="session1", epoch=0, seq=1,
            sample_start=480, captured_ns=1000 + 10_000_000,
            sample_rate=SOURCE_RATE, pcm=np.ones(480, dtype=np.float32),
            valid_samples=480, discontinuity=False
        )
        out2 = resampler.push(frame2)
        out_finish = resampler.finish()
        
        all_out = out1 + out2 + out_finish
        self.assertEqual(len(all_out), 2)
        
        self.assertEqual(all_out[0].session_id, "session1")
        self.assertEqual(all_out[0].sample_start, 0)
        self.assertEqual(all_out[0].seq, 0)
        self.assertEqual(all_out[0].captured_ns, 1000)
        self.assertEqual(all_out[0].valid_samples, 160)
        
        self.assertEqual(all_out[1].session_id, "session1")
        self.assertEqual(all_out[1].sample_start, 480)
        self.assertEqual(all_out[1].seq, 1)
        self.assertEqual(all_out[1].captured_ns, 1000 + 10_000_000)
        self.assertEqual(all_out[1].valid_samples, 160)

    def test_zero_output_then_multiple_frames_released(self):
        resampler = StreamingResampler()
        base_ns = 1000
        
        inputs = []
        for i in range(200):
            inputs.append(AudioFrame(
                session_id="delayed", epoch=0, seq=i,
                sample_start=i*480, captured_ns=base_ns + i*10_000_000,
                sample_rate=SOURCE_RATE, pcm=np.ones(480, dtype=np.float32),
                valid_samples=480, discontinuity=False
            ))
            
        out1 = resampler.push(inputs[0])
        self.assertEqual(len(out1), 0)
        
        all_out = []
        multi_frame_released = False
        for i in range(1, 200):
            out = resampler.push(inputs[i])
            if len(out) > 1:
                multi_frame_released = True
            all_out.extend(out)
            
        self.assertTrue(multi_frame_released)
        all_out.extend(resampler.finish())
        self.assertEqual(len(all_out), 200)
        
        for i in range(200):
            self.assertEqual(all_out[i].seq, i)
            self.assertEqual(all_out[i].sample_start, i*480)
            self.assertEqual(all_out[i].captured_ns, base_ns + i*10_000_000)

    def test_explicit_reset_same_session_epoch(self):
        resampler_test = StreamingResampler()
        resampler_fresh = StreamingResampler()
        
        # Give resampler_test a distinct prior waveform (e.g. 2s, ones)
        for i in range(5):
            resampler_test.push(AudioFrame(
                session_id="same_sess", epoch=0, seq=i,
                sample_start=i*480, captured_ns=1000+i*10_000_000,
                sample_rate=SOURCE_RATE, pcm=np.ones(480, dtype=np.float32) * 0.5,
                valid_samples=480, discontinuity=False
            ))
            
        resampler_test.reset()
        
        # New frame for both resamplers
        frame2 = AudioFrame(
            session_id="same_sess", epoch=1, seq=10,
            sample_start=4800, captured_ns=5000,
            sample_rate=SOURCE_RATE, pcm=np.ones(480, dtype=np.float32) * 0.2,
            valid_samples=480, discontinuity=False
        )
        
        out_test = resampler_test.push(frame2) + resampler_test.finish()
        out_fresh = resampler_fresh.push(frame2) + resampler_fresh.finish()
        
        self.assertEqual(len(out_test), 1)
        self.assertEqual(len(out_fresh), 1)
        self.assertEqual(out_test[0].epoch, 1)
        self.assertEqual(out_test[0].seq, 10)
        self.assertEqual(out_test[0].sample_start, 4800)
        self.assertTrue(out_test[0].discontinuity)
        
        # PCM should be identical if state bleed is eliminated
        np.testing.assert_array_equal(out_test[0].pcm, out_fresh[0].pcm)

    def test_same_session_unannounced_epoch_or_sample_gap(self):
        resampler = StreamingResampler()
        frame1 = AudioFrame(
            session_id="sess_gap", epoch=0, seq=0,
            sample_start=0, captured_ns=1000,
            sample_rate=SOURCE_RATE, pcm=np.ones(480, dtype=np.float32),
            valid_samples=480, discontinuity=False
        )
        resampler.push(frame1)
        
        # Unannounced sample gap
        frame2 = AudioFrame(
            session_id="sess_gap", epoch=0, seq=5,
            sample_start=2400, captured_ns=1000 + 5*10_000_000,
            sample_rate=SOURCE_RATE, pcm=np.ones(480, dtype=np.float32),
            valid_samples=480, discontinuity=False
        )
        out2 = resampler.push(frame2)
        out_finish = resampler.finish()
        all_out = out2 + out_finish
        
        self.assertEqual(len(all_out), 1)
        self.assertEqual(all_out[0].sample_start, 2400)
        self.assertTrue(all_out[0].discontinuity)

    def test_discontinuity_and_reset(self):
        resampler = StreamingResampler()
        frame1 = AudioFrame(
            session_id="sess_A", epoch=0, seq=10,
            sample_start=4800, captured_ns=5000,
            sample_rate=SOURCE_RATE, pcm=np.ones(480, dtype=np.float32),
            valid_samples=480, discontinuity=False
        )
        resampler.push(frame1)
        
        # New session
        frame2 = AudioFrame(
            session_id="sess_B", epoch=1, seq=0,
            sample_start=10000, captured_ns=10000 + 10_000_000,
            sample_rate=SOURCE_RATE, pcm=np.ones(480, dtype=np.float32),
            valid_samples=480, discontinuity=False
        )
        out2 = resampler.push(frame2)
        out_finish = resampler.finish()
        all_out = out2 + out_finish
        
        self.assertGreater(len(all_out), 0)
        last_frame = all_out[-1]
        self.assertEqual(last_frame.session_id, "sess_B")
        self.assertEqual(last_frame.epoch, 1)
        self.assertEqual(last_frame.sample_start, 10000)
        self.assertTrue(last_frame.discontinuity)

    def test_same_session_unannounced_epoch_change(self):
        resampler = StreamingResampler()
        frame1 = AudioFrame(
            session_id="sess_epoch", epoch=0, seq=0,
            sample_start=0, captured_ns=1000,
            sample_rate=SOURCE_RATE, pcm=np.ones(480, dtype=np.float32),
            valid_samples=480, discontinuity=False
        )
        resampler.push(frame1)
        
        # Unannounced epoch change
        frame2 = AudioFrame(
            session_id="sess_epoch", epoch=1, seq=1,
            sample_start=480, captured_ns=1000 + 10_000_000,
            sample_rate=SOURCE_RATE, pcm=np.ones(480, dtype=np.float32),
            valid_samples=480, discontinuity=False
        )
        out2 = resampler.push(frame2)
        out_finish = resampler.finish()
        all_out = out2 + out_finish
        
        self.assertEqual(len(all_out), 1)
        self.assertEqual(all_out[0].epoch, 1)
        self.assertTrue(all_out[0].discontinuity)

    def test_partial_final_padding_checked_zero(self):
        resampler = StreamingResampler()
        frame1 = AudioFrame(
            session_id="sess_pad", epoch=0, seq=0,
            sample_start=0, captured_ns=1000,
            sample_rate=SOURCE_RATE, pcm=np.ones(480, dtype=np.float32),
            valid_samples=480, discontinuity=False
        )
        out1 = resampler.push(frame1)
        
        partial_pcm = np.ones(240, dtype=np.float32)
        frame2 = AudioFrame(
            session_id="sess_pad", epoch=0, seq=1,
            sample_start=480, captured_ns=1000 + 10_000_000,
            sample_rate=SOURCE_RATE, pcm=partial_pcm,
            valid_samples=240, discontinuity=False
        )
        out2 = resampler.push(frame2)
        out_finish = resampler.finish()
        
        all_out = out1 + out2 + out_finish
        total_valid = sum(f.valid_samples for f in all_out)
        self.assertEqual(total_valid, 240)
        
        self.assertTrue(len(all_out) > 0)
        last_frame = all_out[-1]
        
        self.assertEqual(last_frame.valid_samples, 80)
        self.assertEqual(len(last_frame.pcm), 160)
        
        padding = last_frame.pcm[last_frame.valid_samples:]
        np.testing.assert_array_equal(padding, np.zeros_like(padding))

    def test_partial_valid_samples(self):
        resampler = StreamingResampler()
        frame = AudioFrame(
            session_id="sess_partial", epoch=0, seq=5,
            sample_start=2400, captured_ns=8000,
            sample_rate=SOURCE_RATE, pcm=np.ones(240, dtype=np.float32),
            valid_samples=240, discontinuity=False
        )
        
        out = resampler.push(frame)
        out_finish = resampler.finish()
        all_out = out + out_finish
        
        self.assertEqual(len(all_out), 1)
        self.assertEqual(all_out[0].session_id, "sess_partial")
        self.assertEqual(all_out[0].sample_start, 2400)
        self.assertEqual(all_out[0].valid_samples, 80)
        self.assertEqual(len(all_out[0].pcm), 160)
        

