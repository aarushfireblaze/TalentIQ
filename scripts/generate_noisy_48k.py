import wave
import numpy as np
from pathlib import Path
import soxr

def main():
    jfk_path = Path("tests/fixtures/generated/jfk.wav")
    out_path = Path("tests/fixtures/generated/noisy_speech.wav")

    with wave.open(str(jfk_path), "rb") as wf:
        assert wf.getframerate() == 16000
        assert wf.getsampwidth() == 2
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    
    # Upsample to 48k
    samples_48k = soxr.resample(samples, 16000, 48000)
    
    # Add noise
    np.random.seed(42)
    noise = np.random.normal(0, 0.05, len(samples_48k)).astype(np.float32)
    noisy_samples = samples_48k + noise
    noisy_samples = np.clip(noisy_samples, -1.0, 1.0)

    # Write 48k noisy
    noisy_int16 = (noisy_samples * 32767).astype(np.int16)
    
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(48000)
        wf.writeframes(noisy_int16.tobytes())
        
    print(f"Generated {out_path}")

if __name__ == "__main__":
    main()
