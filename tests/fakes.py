from __future__ import annotations

import numpy as np
import uuid
import time

from voice_filtering.contracts import AudioFrame

SOURCE_RATE = 48000
FRAME_SAMPLES = 480


def make_frame(
    seconds: float = 0.01,
    rate: int = SOURCE_RATE,
    session_id: str = "",
    epoch: int = 0,
    seq: int = 0,
    discontinuity: bool = False,
) -> AudioFrame:
    if not session_id:
        session_id = str(uuid.uuid4())
    n_samples = int(rate * seconds)
    pcm = np.sin(2 * np.pi * 440 * np.arange(n_samples) / rate).astype(np.float32) * 0.5
    valid = min(n_samples, FRAME_SAMPLES) if rate == SOURCE_RATE else min(n_samples, 160)
    sample_start = seq * (FRAME_SAMPLES if rate == SOURCE_RATE else 160)
    captured_ns = time.monotonic_ns()
    return AudioFrame(
        session_id=session_id,
        epoch=epoch,
        seq=seq,
        sample_start=sample_start,
        captured_ns=captured_ns,
        sample_rate=rate,
        pcm=pcm[:valid],
        valid_samples=valid,
        discontinuity=discontinuity,
    )


def make_frames(
    seconds: float = 1.0,
    rate: int = SOURCE_RATE,
    session_id: str = "",
    epoch: int = 0,
) -> list[AudioFrame]:
    if not session_id:
        session_id = str(uuid.uuid4())
    frame_size = FRAME_SAMPLES if rate == SOURCE_RATE else 160
    total_samples = int(rate * seconds)
    frames: list[AudioFrame] = []
    seq = 0
    offset = 0
    while offset < total_samples:
        n = min(frame_size, total_samples - offset)
        pcm = np.sin(2 * np.pi * 440 * np.arange(offset, offset + n) / rate).astype(
            np.float32
        ) * 0.5
        captured_ns = time.monotonic_ns()
        frames.append(
            AudioFrame(
                session_id=session_id,
                epoch=epoch,
                seq=seq,
                sample_start=seq * frame_size,
                captured_ns=captured_ns,
                sample_rate=rate,
                pcm=pcm,
                valid_samples=n,
                discontinuity=(seq == 0),
            )
        )
        seq += 1
        offset += n
    return frames


class FakeAudioSource:
    def __init__(self, frames: list[AudioFrame] | None = None) -> None:
        self._frames = frames or []
        self._idx = 0
        self._running = False

    def start(self, *, device_id: str, session_id: str) -> None:
        self._running = True
        self._idx = 0

    def read_frame(self, timeout_s: float) -> AudioFrame | None:
        if not self._running or self._idx >= len(self._frames):
            return None
        frame = self._frames[self._idx]
        self._idx += 1
        return frame

    def stop(self) -> None:
        self._running = False
