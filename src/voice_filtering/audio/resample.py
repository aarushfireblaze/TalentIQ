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
        self._stream = soxr.ResampleStream(
            in_rate=float(SOURCE_RATE),
            out_rate=float(TARGET_RATE),
            num_channels=1,
            dtype='float32',
            quality='HQ'
        )
        self._total_input_samples: int = 0
        self._output_frame_count: int = 0
        self._tail_buffer = np.array([], dtype=np.float32)

    def reset(self) -> None:
        self._stream.clear()
        self._total_input_samples = 0
        self._output_frame_count = 0
        self._tail_buffer = np.array([], dtype=np.float32)

    def _chunk_output(self, arr: np.ndarray, is_last: bool = False) -> list[AudioFrame]:
        if len(self._tail_buffer) > 0:
            arr = np.concatenate([self._tail_buffer, arr])
            self._tail_buffer = np.array([], dtype=np.float32)
            
        all_blocks = []
        offset = 0
        while offset + OUTPUT_FRAME_SAMPLES <= len(arr):
            chunk = arr[offset:offset+OUTPUT_FRAME_SAMPLES].copy()
            sample_start = self._output_frame_count * SOURCE_FRAME_SAMPLES
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
            self._output_frame_count += 1
            offset += OUTPUT_FRAME_SAMPLES
            
        remaining = arr[offset:]
        if is_last and len(remaining) > 0:
            padded = np.zeros(OUTPUT_FRAME_SAMPLES, dtype=np.float32)
            padded[:len(remaining)] = remaining
            sample_start = self._output_frame_count * SOURCE_FRAME_SAMPLES
            all_blocks.append(
                AudioFrame(
                    session_id="",
                    epoch=0,
                    seq=0,
                    sample_start=sample_start,
                    captured_ns=0,
                    sample_rate=TARGET_RATE,
                    pcm=padded,
                    valid_samples=len(remaining),
                    discontinuity=False,
                )
            )
            self._output_frame_count += 1
        elif len(remaining) > 0:
            self._tail_buffer = remaining
            
        return all_blocks

    def push(self, frame: AudioFrame) -> list[AudioFrame]:
        pcm = frame.pcm[: frame.valid_samples].astype(np.float32).copy()
        if len(pcm) == 0:
            return []
        self._total_input_samples += len(pcm)
        out = self._stream.resample_chunk(pcm, last=False)
        return self._chunk_output(out, is_last=False)

    def finish(self) -> list[AudioFrame]:
        dummy = np.array([], dtype=np.float32)
        out = self._stream.resample_chunk(dummy, last=True)
        return self._chunk_output(out, is_last=True)
