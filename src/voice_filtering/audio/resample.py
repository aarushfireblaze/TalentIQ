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
        self._tail_buffer = np.array([], dtype=np.float32)
        self._metadata_fifo = []
        self._last_session = None
        self._last_epoch = None
        self._expected_sample_start = None
        self._pending_discontinuity = False

    def reset(self) -> None:
        self._stream.clear()
        self._tail_buffer = np.array([], dtype=np.float32)
        self._metadata_fifo.clear()
        self._last_session = None
        self._last_epoch = None
        self._expected_sample_start = None
        self._pending_discontinuity = True

    def _get_next_meta(self) -> dict:
        if self._metadata_fifo:
            return self._metadata_fifo.pop(0)
        raise ValueError("Metadata FIFO underflow; output exceeds pushed source frames")

    def _chunk_output(self, arr: np.ndarray, is_last: bool = False) -> list[AudioFrame]:
        if len(self._tail_buffer) > 0:
            arr = np.concatenate([self._tail_buffer, arr])
            self._tail_buffer = np.array([], dtype=np.float32)
            
        all_blocks = []
        offset = 0
        while offset + OUTPUT_FRAME_SAMPLES <= len(arr):
            chunk = arr[offset:offset+OUTPUT_FRAME_SAMPLES].copy()
            meta = self._get_next_meta()
            
            discont = self._pending_discontinuity
            self._pending_discontinuity = False

            all_blocks.append(
                AudioFrame(
                    session_id=meta['session_id'],
                    epoch=meta['epoch'],
                    seq=meta['seq'],
                    sample_start=meta['sample_start'],
                    captured_ns=meta['captured_ns'],
                    sample_rate=TARGET_RATE,
                    pcm=chunk,
                    valid_samples=OUTPUT_FRAME_SAMPLES,
                    discontinuity=discont,
                )
            )
            offset += OUTPUT_FRAME_SAMPLES
            
        remaining = arr[offset:]
        if is_last and len(remaining) > 0:
            padded = np.zeros(OUTPUT_FRAME_SAMPLES, dtype=np.float32)
            padded[:len(remaining)] = remaining
            meta = self._get_next_meta()
            
            discont = self._pending_discontinuity
            self._pending_discontinuity = False

            all_blocks.append(
                AudioFrame(
                    session_id=meta['session_id'],
                    epoch=meta['epoch'],
                    seq=meta['seq'],
                    sample_start=meta['sample_start'],
                    captured_ns=meta['captured_ns'],
                    sample_rate=TARGET_RATE,
                    pcm=padded,
                    valid_samples=len(remaining),
                    discontinuity=discont,
                )
            )
        elif len(remaining) > 0:
            self._tail_buffer = remaining
            
        return all_blocks

    def push(self, frame: AudioFrame) -> list[AudioFrame]:
        pcm = frame.pcm[: frame.valid_samples].astype(np.float32).copy()
        if len(pcm) == 0:
            return []
            
        is_discontinuous = False
        if self._last_session is not None:
            if frame.session_id != self._last_session or frame.epoch != self._last_epoch:
                is_discontinuous = True
            elif self._expected_sample_start is not None and frame.sample_start != self._expected_sample_start:
                is_discontinuous = True
            elif frame.discontinuity:
                is_discontinuous = True

        if is_discontinuous:
            self.reset()
            self._pending_discontinuity = True
            
        if frame.discontinuity:
            self._pending_discontinuity = True

        self._last_session = frame.session_id
        self._last_epoch = frame.epoch
        self._expected_sample_start = frame.sample_start + len(pcm)
        
        self._metadata_fifo.append({
            'session_id': frame.session_id,
            'epoch': frame.epoch,
            'seq': frame.seq,
            'sample_start': frame.sample_start,
            'captured_ns': frame.captured_ns
        })

        out = self._stream.resample_chunk(pcm, last=False)
        return self._chunk_output(out, is_last=False)

    def finish(self) -> list[AudioFrame]:
        dummy = np.array([], dtype=np.float32)
        out = self._stream.resample_chunk(dummy, last=True)
        ret = self._chunk_output(out, is_last=True)
        self.reset()
        return ret
