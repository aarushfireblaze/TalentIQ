from __future__ import annotations

import threading
import time
import uuid
from collections import deque

import numpy as np
import sounddevice as sd

from voice_filtering.contracts import AudioFrame, PipelineError

FRAME_SAMPLES = 480
SOURCE_RATE = 48000
RING_CAP = 100


class CaptureSource:
    def __init__(self) -> None:
        self._stream: sd.InputStream | None = None
        self._ring: deque[AudioFrame] = deque(maxlen=RING_CAP)
        self._lock = threading.Lock()
        self._session_id: str = ""
        self._epoch: int = 0
        self._seq: int = 0
        self._running: bool = False
        self._drop_count: int = 0
        self._session_t0_ns: int = 0

    def start(self, *, device_id: str, session_id: str) -> None:
        if self._running:
            return
        self._session_id = session_id
        self._epoch = 0
        self._seq = 0
        self._drop_count = 0
        self._ring.clear()
        try:
            info = sd.query_devices(int(device_id), "input")
            if info["max_input_channels"] < 1:
                raise PipelineError(
                    code="AUDIO_DEVICE_ERROR",
                    stage="capture",
                    message=f"Device {device_id} has no input channels",
                    recoverable=True,
                )
            sd.check_input_settings(
                device=int(device_id), channels=1, dtype="float32", samplerate=SOURCE_RATE
            )
        except sd.PortAudioError as e:
            raise PipelineError(
                code="AUDIO_DEVICE_ERROR",
                stage="capture",
                message=str(e),
                recoverable=True,
            ) from e
        self._session_t0_ns = time.monotonic_ns()
        self._running = True
        try:
            self._stream = sd.InputStream(
                device=int(device_id),
                channels=1,
                samplerate=SOURCE_RATE,
                dtype="float32",
                blocksize=FRAME_SAMPLES,
                callback=self._callback,
            )
            self._stream.start()
        except Exception as e:
            self._running = False
            raise PipelineError(
                code="AUDIO_DEVICE_ERROR",
                stage="capture",
                message=str(e),
                recoverable=True,
            ) from e

    def _callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        if not self._running:
            return
        pcm = np.array(indata[:, 0], dtype=np.float32).copy()
        valid = len(pcm)
        sample_start = self._seq * FRAME_SAMPLES
        captured_ns = self._session_t0_ns + sample_start * 1_000_000_000 // SOURCE_RATE
        frame = AudioFrame(
            session_id=self._session_id,
            epoch=self._epoch,
            seq=self._seq,
            sample_start=sample_start,
            captured_ns=captured_ns,
            sample_rate=SOURCE_RATE,
            pcm=pcm,
            valid_samples=valid,
            discontinuity=False,
        )
        self._seq += 1
        with self._lock:
            if len(self._ring) >= RING_CAP:
                self._ring.popleft()
                self._drop_count += 1
            self._ring.append(frame)

    def read_frame(self, timeout_s: float) -> AudioFrame | None:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            with self._lock:
                if self._ring:
                    return self._ring.popleft()
            time.sleep(0.001)
        return None

    def stop(self) -> None:
        self._running = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def get_drop_count(self) -> int:
        with self._lock:
            return self._drop_count

    def reset_epoch(self) -> int:
        self._epoch += 1
        return self._epoch

    def inject_frame(self, frame: AudioFrame) -> None:
        with self._lock:
            if len(self._ring) >= RING_CAP:
                self._ring.popleft()
                self._drop_count += 1
            self._ring.append(frame)


def enumerate_devices() -> list[dict]:
    devices = []
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0:
            devices.append(
                {
                    "id": str(i),
                    "name": d["name"],
                    "host_api": sd.query_hostapis(d["hostapi"])["name"],
                    "max_input_channels": d["max_input_channels"],
                    "default_sample_rate": d["default_samplerate"],
                }
            )
    return devices


def get_default_device_id() -> str | None:
    dev = sd.default.device[0]
    if dev is None or dev < 0:
        devs = enumerate_devices()
        if devs:
            return devs[0]["id"]
        return None
    return str(dev)
