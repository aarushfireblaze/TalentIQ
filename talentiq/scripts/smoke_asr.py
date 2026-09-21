#!/usr/bin/env python3
"""ASR smoke test: decode a known WAV and verify nonempty output."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def main() -> int:
    parser = argparse.ArgumentParser(description="ASR smoke test")
    parser.add_argument("--wav", required=True, help="Path to WAV file")
    parser.add_argument("--model", required=True, help="Path to model directory")
    parser.add_argument("--report", required=True, help="Path for JSON report")
    args = parser.parse_args()

    os.environ["HF_HUB_OFFLINE"] = "1"

    from voice_filtering.asr.whisper import WhisperASR, DEFAULT_REVISION

    model_path = Path(args.model)
    wav_path = Path(args.wav)
    report_path = Path(args.report)

    if not wav_path.exists():
        print(f"ERROR: WAV not found: {wav_path}", file=sys.stderr)
        return 1
    if not model_path.exists():
        print(f"ERROR: Model not found: {model_path}", file=sys.stderr)
        return 1

    print(f"Loading model from {model_path}...")
    asr = WhisperASR(model_path)
    try:
        asr.load()
    except Exception as e:
        print(f"ERROR: Model load failed: {e}", file=sys.stderr)
        report = {"status": "fail", "error": str(e)}
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2))
        return 1

    print("Reading WAV...")
    import wave
    with wave.open(str(wav_path), "rb") as wf:
        n_frames = wf.getnframes()
        rate = wf.getframerate()
        raw = wf.readframes(n_frames)
    pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    duration_s = len(pcm) / rate
    print(f"Audio: {duration_s:.2f}s, {rate}Hz, {len(pcm)} samples")

    print("Decoding...")
    t0 = time.monotonic()
    text = asr.decode(pcm)
    decode_time = time.monotonic() - t0
    print(f"Text: {text!r}")
    print(f"Decode time: {decode_time:.2f}s")

    text_lower = text.lower()
    has_ask = "ask not" in text_lower
    has_country = "country" in text_lower
    passed = bool(text.strip()) and has_ask and has_country
    status = "pass" if passed else "fail"

    report = {
        "status": status,
        "model_revision": DEFAULT_REVISION,
        "compute_type": "int8",
        "audio_duration_s": round(duration_s, 2),
        "decode_duration_s": round(decode_time, 2),
        "text": text,
        "has_ask_not": has_ask,
        "has_country": has_country,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    print(f"Report: {report_path}")
    print(f"Result: {status.upper()}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
