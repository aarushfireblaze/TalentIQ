import unittest
import subprocess
import sys
import json
import tempfile
from pathlib import Path
import wave
import numpy as np

class TestEvaluator(unittest.TestCase):
    def test_evaluator_help(self):
        result = subprocess.run([sys.executable, "scripts/replay_four_modes.py", "-h"], capture_output=True, text=True)
        self.assertIn("--wav", result.stdout)

    def test_evaluator_scoring(self):
        # We can test the scoring by running it on a tiny generated wav file.
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            wav_path = td / "test.wav"
            with wave.open(str(wav_path), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(48000)
                pcm = np.zeros(48000, dtype=np.int16) # 1 sec of silence
                output.writeframes(pcm.tobytes())
            
            # Since hush and rnnoise might not load if libraries aren't found, 
            # we should skip running the actual script if the native libraries aren't present.
            if not Path("lib/librnnoise.0.dylib").exists() or not Path("lib/libweya_nc.dylib").exists():
                self.skipTest("Native libraries not found, skipping integration test.")
            
            result = subprocess.run([
                sys.executable, "scripts/replay_four_modes.py",
                "--wav", str(wav_path),
                "--model", "models/faster-whisper-tiny.en",
                "--output-dir", str(td / "out"),
                "--primary-reference", "hello world",
                "--background-reference", "background noise"
            ], capture_output=True, text=True)
            
            self.assertEqual(result.returncode, 0, result.stderr)
            report_path = td / "out" / "report.json"
            self.assertTrue(report_path.exists())
            with open(report_path) as f:
                report = json.load(f)
            self.assertIn("raw", report["modes"])
            # The transcript will be empty because of silence
            # Background intrusion rate should be 0.0 because there are no words
            self.assertEqual(report["modes"]["raw"]["background_intrusion_rate_pct"], 0.0)

if __name__ == '__main__':
    unittest.main()
