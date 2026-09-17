from __future__ import annotations

import numpy as np
import soxr

from voice_filtering.contracts import AudioFrame

TARGET_RATE = 16000
SOURCE_RATE = 48000
OUTPUT_FRAME_SAMPLES = 160
SOURCE_FRAME_SAMPLES = 480


class StreamingResampler:
    def __init__(self) -> None:
        self._buffer: list[np.ndarray] = []
        self._total_input_samples: int = 0
        self._output_frame_count: int = 0

    def reset(self) -> None:
        self._buffer = []
        self._total_input_samples = 0
        self._output_frame_count = 0

    def push(self, frame: AudioFrame) -> list[AudioFrame]:
        pcm = frame.pcm[: frame.valid_samples].astype(np.float32).copy()
        if len(pcm) == 0:
            return []
        self._buffer.append(pcm)
        self._total_input_samples += len(pcm)
        return []

    def finish(self) -> list[AudioFrame]:
        if not self._buffer:
            return []
        combined = np.concatenate(self._buffer)
        full_resampled = soxr.resample(combined, SOURCE_RATE, TARGET_RATE, quality="HQ")
        full_resampled = np.asarray(full_resampled, dtype=np.float32)
        expected_frames = self._total_input_samples // SOURCE_FRAME_SAMPLES
        all_blocks: list[AudioFrame] = []
        offset = 0
        for i in range(expected_frames):
            if offset + OUTPUT_FRAME_SAMPLES > len(full_resampled):
                break
            chunk = full_resampled[offset : offset + OUTPUT_FRAME_SAMPLES].copy()
            sample_start = i * SOURCE_FRAME_SAMPLES
            all_blocks.append(
                AudioFrame(
                    session_id="",
                    epoch=0,
                    seq=0,
                    sample_start=sample_start,
                    captured_ns=0,
                    sample_rate=TARGET_RATE,
                    pcm=chunk,
                    valid_samples=OUTPUT_FRAME_SAMPLES,
                    discontinuity=False,
                )
            )
            offset += OUTPUT_FRAME_SAMPLES
        tail = full_resampled[offset:]
        if len(tail) > 0:
            padded = np.zeros(OUTPUT_FRAME_SAMPLES, dtype=np.float32)
            padded[: len(tail)] = tail
            sample_start = expected_frames * SOURCE_FRAME_SAMPLES
            all_blocks.append(
                AudioFrame(
                    session_id="",
                    epoch=0,
                    seq=0,
                    sample_start=sample_start,
                    captured_ns=0,
                    sample_rate=TARGET_RATE,
                    pcm=padded,
                    valid_samples=len(tail),
                    discontinuity=False,
                )
            )
        self._output_frame_count = len(all_blocks)
        return all_blocks
