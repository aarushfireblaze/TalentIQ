#!/usr/bin/env python3
"""Deterministic replay of a 48 kHz WAV through Raw and RNNoise pipeline modes.

Usage:
    python scripts/replay_ab.py \
        --wav tests/fixtures/generated/noisy_speech.wav \
        --model models/faster-whisper-tiny.en \
        --report artifacts/replay/ab-report.json

Runs the same immutable source through both Raw and RNNoise modes with
identical ASR settings, producing transcript, timing, and metric evidence
for H1 A/B comparison.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import wave
from pathlib import Path

import numpy as np


def read_wav_48k_mono(path: Path) -> tuple[np.ndarray, int]:
    """Read a WAV file, return (float32 samples, sample_rate)."""
    with wave.open(str(path), "rb") as wf:
        rate = wf.getframerate()
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if sampwidth == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 4:
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"Unsupported sample width: {sampwidth}")

    if channels > 1:
        samples = samples.reshape(-1, channels)[:, 0]

    return samples, rate


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def run_pipeline_mode(
    samples: np.ndarray,
    sample_rate: int,
    mode: str,
    model_path: str,
) -> dict:
    """Run audio through pipeline in a given mode, return metrics + transcript."""
    from voice_filtering.audio.resample import StreamingResampler
    from voice_filtering.audio.rnnoise import RNNoiseProcessor
    from voice_filtering.contracts import AudioFrame
    from voice_filtering.asr.whisper import WhisperASR

    FRAME_SIZE = 480
    t0 = time.monotonic()

    resampler = StreamingResampler()
    rnnoise = RNNoiseProcessor() if mode == "rnnoise" else None
    asr = WhisperASR(model_path)
    try:
        asr.load()
    except Exception as e:
        return {"error": f"ASR load failed: {e}"}

    denoise_time = 0.0
    denoise_frames = 0
    resample_time = 0.0
    asr_time = 0.0
    transcript_parts: list[str] = []

    total_samples = len(samples)
    seq = 0
    offset = 0
    session_id = "replay"
    captured_ns = 0

    while offset < total_samples:
        chunk = samples[offset : offset + FRAME_SIZE]
        valid = len(chunk)
        if valid < FRAME_SIZE:
            padded = np.zeros(FRAME_SIZE, dtype=np.float32)
            padded[:valid] = chunk
            chunk = padded

        frame = AudioFrame(
            session_id=session_id,
            epoch=0,
            seq=seq,
            sample_start=seq * FRAME_SIZE,
            captured_ns=captured_ns,
            sample_rate=sample_rate,
            pcm=chunk,
            valid_samples=valid,
            discontinuity=(seq == 0),
        )

        if rnnoise is not None and rnnoise.is_loaded:
            dt0 = time.monotonic()
            frame = rnnoise.process(frame)
            denoise_time += time.monotonic() - dt0
            denoise_frames += 1

        rt0 = time.monotonic()
        resampled = resampler.push(frame)
        resample_time += time.monotonic() - rt0

        for rframe in resampled:
            pcm16 = rframe.pcm[: rframe.valid_samples]
            if len(pcm16) > 0:
                at0 = time.monotonic()
                text = asr.decode(pcm16)
                asr_time += time.monotonic() - at0
                if text.strip():
                    transcript_parts.append(text.strip())

        seq += 1
        offset += FRAME_SIZE

    flush = resampler.finish()
    for rframe in flush:
        pcm16 = rframe.pcm[: rframe.valid_samples]
        if len(pcm16) > 0:
            at0 = time.monotonic()
            text = asr.decode(pcm16)
            asr_time += time.monotonic() - at0
            if text.strip():
                transcript_parts.append(text.strip())

    total_time = time.monotonic() - t0
    full_text = " ".join(transcript_parts)

    result = {
        "mode": mode,
        "input_samples": int(total_samples),
        "input_duration_s": total_samples / sample_rate,
        "sample_rate": sample_rate,
        "total_time_s": round(total_time, 4),
        "denoise_time_s": round(denoise_time, 4),
        "denoise_frames": denoise_frames,
        "denoise_avg_ms": round(denoise_time / max(denoise_frames, 1) * 1000, 4),
        "resample_time_s": round(resample_time, 4),
        "asr_time_s": round(asr_time, 4),
        "transcript": full_text,
        "transcript_segments": len(transcript_parts),
    }

    if rnnoise is not None and rnnoise.is_loaded:
        m = rnnoise.metrics
        result["rnnoise_avg_ms"] = m.avg_ms
        result["rnnoise_p95_ms"] = m.p95_ms
        result["rnnoise_total_frames"] = m.total_frames

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="A/B replay for H1 comparison")
    parser.add_argument("--wav", required=True, help="Input 48 kHz mono WAV")
    parser.add_argument("--model", required=True, help="ASR model path")
    parser.add_argument("--report", required=True, help="Output JSON report path")
    args = parser.parse_args()

    wav_path = Path(args.wav)
    if not wav_path.exists():
        print(f"ERROR: WAV not found: {wav_path}", file=sys.stderr)
        return 1

    model_path = Path(args.model)
    if not model_path.exists():
        print(f"ERROR: Model not found: {model_path}", file=sys.stderr)
        return 1

    samples, rate = read_wav_48k_mono(wav_path)
    wav_hash = file_sha256(wav_path)

    print(f"Input: {wav_path.name} ({len(samples)/rate:.1f}s, {rate} Hz, sha256={wav_hash[:16]}...)")

    print("Running Raw mode...")
    raw_result = run_pipeline_mode(samples, rate, "raw", str(model_path))

    print("Running RNNoise mode...")
    rn_result = run_pipeline_mode(samples, rate, "rnnoise", str(model_path))

    report = {
        "input_file": str(wav_path),
        "input_sha256": wav_hash,
        "model_path": str(model_path),
        "raw": raw_result,
        "rnnoise": rn_result,
    }

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nRaw transcript: {raw_result.get('transcript', 'N/A')[:200]}")
    print(f"RNNoise transcript: {rn_result.get('transcript', 'N/A')[:200]}")
    print(f"Report saved: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
