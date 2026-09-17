from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class AudioFrame:
    session_id: str
    epoch: int
    seq: int
    sample_start: int
    captured_ns: int
    sample_rate: int
    pcm: NDArray[np.float32]
    valid_samples: int
    discontinuity: bool


@dataclass(frozen=True)
class TranscriptEvent:
    session_id: str
    segment_id: str
    revision: int
    kind: str  # "partial" | "final"
    text: str
    start_ms: float
    end_ms: float
    mode: str
    epoch: int
    final_reason: str | None = None


@dataclass(frozen=True)
class PipelineError:
    code: str
    stage: str
    message: str
    recoverable: bool


class StageStatus(enum.Enum):
    UNAVAILABLE = "unavailable"
    LOADING = "loading"
    READY = "ready"
    ACTIVE = "active"
    FAILED = "failed"
    BYPASSED = "bypassed"


@dataclass
class StageInfo:
    status: StageStatus
    reason: str | None = None
    model_revision: str | None = None


@runtime_checkable
class AudioSource(Protocol):
    def start(self, *, device_id: str, session_id: str) -> None: ...
    def read_frame(self, timeout_s: float) -> AudioFrame | None: ...
    def stop(self) -> None: ...


@runtime_checkable
class FrameProcessor(Protocol):
    def reset(self) -> None: ...
    def process(self, frame: AudioFrame) -> AudioFrame: ...
    def close(self) -> None: ...


@runtime_checkable
class Transcriber(Protocol):
    def start(self, session_id: str, epoch: int) -> None: ...
    def push_audio(self, frame: AudioFrame) -> None: ...
    def finish(self, timeout_s: float = 5.0) -> bool: ...
    def reset(self, session_id: str, epoch: int) -> None: ...
    def close(self) -> None: ...


@runtime_checkable
class PipelineController(Protocol):
    def start(self, device_id: str, mode: str, record: bool) -> dict: ...
    def stop(self) -> dict: ...
    def switch_mode(self, mode: str) -> dict: ...
    def clear_transcript(self) -> dict: ...
    def snapshot(self) -> dict: ...
