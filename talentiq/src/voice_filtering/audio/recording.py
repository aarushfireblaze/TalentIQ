from __future__ import annotations

import json
import os
import struct
import time
import wave
from pathlib import Path

import numpy as np

from voice_filtering.contracts import AudioFrame

MAX_DURATION_S = 2.0
MAX_RECORDING_S = 60.0


class WAVWriter:
    def __init__(self, output_dir: Path, sample_rate: int) -> None:
        self._output_dir = output_dir
        self._sample_rate = sample_rate
        self._frames: list[np.ndarray] = []
        self._total_samples: int = 0
        self._start_time: float = 0.0
        self._active: bool = False
        self._session_id: str = ""
        self._overflow: bool = False

    def start(self, session_id: str) -> None:
        self._frames = []
        self._total_samples = 0
        self._start_time = time.time()
        self._active = True
        self._session_id = session_id
        self._overflow = False

    def write_frame(self, frame: AudioFrame) -> None:
        if not self._active:
            return
        if self._total_samples / self._sample_rate >= MAX_RECORDING_S:
            self._overflow = True
            return
        self._frames.append(frame.pcm[: frame.valid_samples].copy())
        self._total_samples += frame.valid_samples

    def stop(self) -> Path | None:
        if not self._active:
            return None
        self._active = False
        if not self._frames:
            return None
        self._output_dir.mkdir(parents=True, exist_ok=True)
        session_dir = self._output_dir / f"{self._session_id}"
        session_dir.mkdir(exist_ok=True)
        wav_path = session_dir / "raw.wav"
        pcm = np.concatenate(self._frames)
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self._sample_rate)
            pcm16 = np.clip(pcm * 32767, -32768, 32767).astype(np.int16)
            wf.writeframes(pcm16.tobytes())
        metadata = {
            "session_id": self._session_id,
            "sample_rate": self._sample_rate,
            "total_samples": int(self._total_samples),
            "duration_s": self._total_samples / self._sample_rate,
            "overflow": self._overflow,
            "timestamp": self._start_time,
        }
        meta_path = session_dir / "metadata.json"
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)
        return wav_path

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def overflow(self) -> bool:
        return self._overflow
