#!/usr/bin/env python3
"""Replay one immutable 48 kHz mono WAV through all four native pipeline modes."""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import time
import wave
from pathlib import Path

import numpy as np

from replay_ab import file_sha256, read_wav_48k_mono
from voice_filtering.asr.whisper import DEFAULT_REVISION, WhisperASR
from voice_filtering.audio.hush import HushProcessor
from voice_filtering.audio.resample import StreamingResampler
from voice_filtering.audio.rnnoise import RNNoiseProcessor
from voice_filtering.contracts import AudioFrame


def write_wav(path: Path, samples: np.ndarray) -> None:
    pcm = np.clip(samples, -1.0, 1.0)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        output.writeframes((pcm * 32767).astype("<i2").tobytes())


def measured_lag_ms(reference: np.ndarray, target: np.ndarray) -> float:
    """Find target lag against Raw by correlation within 200 ms."""
    max_shift = min(3200, len(reference) - 1, len(target) - 1)
    reference = reference.astype(np.float64)
    target = target.astype(np.float64)
    reference -= reference.mean()
    target -= target.mean()
    fft_size = 1 << (len(reference) + len(target) - 2).bit_length()
    correlation = np.fft.irfft(
        np.fft.rfft(target, fft_size) * np.conj(np.fft.rfft(reference, fft_size)),
        fft_size,
    )
    shifts = np.arange(-max_shift, max_shift + 1)
    window = correlation[shifts % fft_size]
    return round(int(shifts[np.argmax(window)]) / 16.0, 3)


def run_mode(samples: np.ndarray, mode: str, asr: WhisperASR, output_dir: Path) -> tuple[dict, np.ndarray]:
    rnnoise = RNNoiseProcessor() if mode in ("rnnoise", "combined") else None
    hush = HushProcessor() if mode in ("hush", "combined") else None
    if rnnoise is not None and not rnnoise.is_loaded:
        raise RuntimeError(f"RNNoise unavailable: {rnnoise.load_error}")
    if hush is not None and not hush.is_loaded:
        raise RuntimeError(f"Hush unavailable: {hush.load_error}")

    resampler = StreamingResampler()
    output: list[np.ndarray] = []
    counts = {"capture": 0, "rnnoise": 0, "resample": 0, "hush": 0, "output": 0}
    timings = {"rnnoise": 0.0, "resample": 0.0, "hush": 0.0}
    frame_size = 480
    start = time.monotonic()

    def consume(frame: AudioFrame) -> None:
        counts["resample"] += 1
        if hush is not None:
            valid = frame.valid_samples
            if valid < 160:
                padded = np.zeros(160, dtype=np.float32)
                padded[:valid] = frame.pcm[:valid]
                frame = AudioFrame(**{**frame.__dict__, "pcm": padded, "valid_samples": 160})
            before = time.monotonic()
            frame = hush.process(frame)
            timings["hush"] += time.monotonic() - before
            counts["hush"] += 1
            output.append(frame.pcm[:valid].copy() if valid < 160 else frame.pcm[:frame.valid_samples].copy())
        else:
            output.append(frame.pcm[:frame.valid_samples].copy())
        counts["output"] += 1

    for seq, offset in enumerate(range(0, len(samples), frame_size)):
        chunk = samples[offset:offset + frame_size]
        valid = len(chunk)
        if valid < frame_size:
            chunk = np.pad(chunk, (0, frame_size - valid))
        frame = AudioFrame(
            session_id=mode, epoch=0, seq=seq, sample_start=offset,
            captured_ns=offset * 1_000_000_000 // 48000,
            sample_rate=48000, pcm=chunk.astype(np.float32),
            valid_samples=valid, discontinuity=(seq == 0),
        )
        counts["capture"] += 1
        if rnnoise is not None:
            before = time.monotonic()
            padded_frame = AudioFrame(**{**frame.__dict__, "valid_samples": frame_size})
            frame = rnnoise.process(padded_frame)
            if valid < frame_size:
                frame = AudioFrame(**{**frame.__dict__, "valid_samples": valid})
            timings["rnnoise"] += time.monotonic() - before
            counts["rnnoise"] += 1
        before = time.monotonic()
        converted = resampler.push(frame)
        timings["resample"] += time.monotonic() - before
        for converted_frame in converted:
            consume(converted_frame)
    for converted_frame in resampler.finish():
        consume(converted_frame)

    pcm16 = np.concatenate(output) if output else np.array([], dtype=np.float32)
    asr_start = time.monotonic()
    transcript = asr.decode(pcm16)
    asr_time = time.monotonic() - asr_start
    wav_path = output_dir / f"{mode}.wav"
    write_wav(wav_path, pcm16)
    result = {
        "mode": mode, "transcript": transcript, "output_wav": str(wav_path),
        "output_sha256": file_sha256(wav_path), "input_frames": counts["capture"],
        "output_frames": counts["output"], "output_samples": len(pcm16),
        "expected_output_samples": round(len(samples) / 3),
        "gaps": 0, "drops": max(0, round(len(samples) / 3) - len(pcm16)),
        "stage_frames": counts, "stage_time_s": {key: round(value, 4) for key, value in timings.items()},
        "asr_time_s": round(asr_time, 4), "total_time_s": round(time.monotonic() - start, 4),
    }
    if rnnoise is not None:
        result["rnnoise_p95_ms"] = rnnoise.metrics.p95_ms
        rnnoise.close()
    if hush is not None:
        result["hush_p95_ms"] = hush.metrics.p95_ms
        hush.close()
    return result, pcm16


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wav", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--primary-reference", default="")
    parser.add_argument("--background-reference", default="")
    args = parser.parse_args()
    source = Path(args.wav)
    with wave.open(str(source), "rb") as input_wav:
        if input_wav.getnchannels() != 1:
            parser.error(f"Input must be mono; got {input_wav.getnchannels()} channels")
    samples, rate = read_wav_48k_mono(source)
    if rate != 48000:
        parser.error(f"Input must be 48000 Hz; got {rate} Hz")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    asr = WhisperASR(args.model)
    asr.load()
    report = {
        "input_wav": str(source), "input_sha256": file_sha256(source),
        "input_samples": len(samples), "sample_rate": rate, "channels": 1,
        "source_device": "prerecorded WAV", "os_audio_processing": "none during replay",
        "scored_interval_s": [0.0, round(len(samples) / rate, 3)],
        "reference_primary": args.primary_reference,
        "reference_background": args.background_reference,
        "asr_revision": DEFAULT_REVISION, "asr_settings": "int8 CPU; English; beam 1; temperature 0; VAD on",
        "asr_model_sha256": file_sha256(Path(args.model) / "model.bin"),
        "rnnoise_revision": "xiph/rnnoise@70f1d25", "hush_revision": "weya-ai/hush@a55d932",
        "native_source_revision": "pulp-vision/Hush@9f6414e", "modes": {},
        "rnnoise_library_sha256": file_sha256(Path("lib/librnnoise.0.dylib")),
        "hush_library_sha256": file_sha256(Path("lib/libweya_nc.dylib")),
        "hush_model_sha256": file_sha256(Path("models/hush/advanced_dfnet16k_model_best_onnx.tar.gz")),
    }
    raw_pcm = None
    for mode in ("raw", "rnnoise", "hush", "combined"):
        result, pcm = run_mode(samples, mode, asr, output_dir)
        if args.primary_reference:
            expected = re.findall(r"[a-z0-9']+", args.primary_reference.lower())
            actual = re.findall(r"[a-z0-9']+", result["transcript"].lower())
            matched = sum(block.size for block in difflib.SequenceMatcher(None, expected, actual).get_matching_blocks())
            result["primary_retention_pct"] = round(100 * matched / len(expected), 1)
        result["background_intrusion_rate_pct"] = None if not args.background_reference else "NOT_SCORED"
        result["alignment_delay_ms_vs_raw"] = 0.0 if raw_pcm is None else measured_lag_ms(raw_pcm, pcm)
        if raw_pcm is None:
            raw_pcm = pcm
        report["modes"][mode] = result
        print(f"{mode}: samples={len(pcm)} drops={result['drops']} lag={result['alignment_delay_ms_vs_raw']} ms transcript={result['transcript']!r}")
    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
