from __future__ import annotations

import ctypes
import os
import platform
import statistics
import time
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray

from voice_filtering.contracts import AudioFrame

FRAME_SIZE = 480
SOURCE_RATE = 48000
_SCALE_UP = 32768.0
_SCALE_DOWN = 1.0 / 32768.0
_MAX_INT16 = 32767.0
_MIN_INT16 = -32768.0
_METRICS_WINDOW = 1000


class RNNoiseLoadError(Exception):
    pass


class RNNoiseState:
    """Opaque handle to the native rnnoise DenoiseState."""

    def __init__(self, lib: ctypes.CDLL, state_ptr: ctypes.c_void_p) -> None:
        self._lib = lib
        self._ptr = state_ptr

    @property
    def ptr(self) -> ctypes.c_void_p:
        return self._ptr

    def close(self) -> None:
        if self._ptr:
            self._lib.rnnoise_destroy(self._ptr)
            self._ptr = ctypes.c_void_p(None)


class RNNoiseMetrics:
    def __init__(self) -> None:
        self._durations: list[float] = []
        self._window: list[float] = []

    def record(self, duration_s: float) -> None:
        self._durations.append(duration_s)
        self._window.append(duration_s)
        if len(self._window) > _METRICS_WINDOW:
            self._window.pop(0)

    def reset(self) -> None:
        self._window.clear()

    @property
    def avg_ms(self) -> float | None:
        if not self._window:
            return None
        return statistics.mean(self._window) * 1000.0

    @property
    def p95_ms(self) -> float | None:
        if not self._window:
            return None
        sorted_w = sorted(self._window)
        idx = int(len(sorted_w) * 0.95)
        idx = min(idx, len(sorted_w) - 1)
        return sorted_w[idx] * 1000.0

    @property
    def total_frames(self) -> int:
        return len(self._durations)


def _load_native_library() -> ctypes.CDLL:
    """Attempt to load the native RNNoise shared library.

    Searches:
      1. RNNOISE_LIB_PATH env var (explicit path)
      2. lib/ directory next to this file
      3. System default paths via ctypes.util.find_library

    Raises RNNoiseLoadError if nothing can be loaded.
    """
    env_path = os.environ.get("RNNOISE_LIB_PATH")
    candidates: list[str] = []

    if env_path:
        candidates.append(env_path)

    lib_dir = Path(__file__).parent.parent.parent.parent / "lib"
    if lib_dir.is_dir():
        for name in (
            "librnnoise.0.dylib",
            "librnnoise.dylib",
            "librnnoise.so",
            "librnnoise.so.0",
            "rnnoise.dll",
        ):
            p = lib_dir / name
            if p.exists():
                candidates.append(str(p))

    local_dir = Path(__file__).parent.parent.parent.parent
    for sub in ("lib", ".libs"):
        for name in ("librnnoise.0.dylib", "librnnoise.dylib", "librnnoise.so"):
            p = local_dir / sub / name
            if p.exists():
                candidates.append(str(p))

    try:
        import ctypes.util
        found = ctypes.util.find_library("rnnoise")
        if found:
            candidates.append(found)
    except Exception:
        pass

    last_err: Exception | None = None
    for path in candidates:
        try:
            lib = ctypes.CDLL(path)
            return lib
        except Exception as e:
            last_err = e

    msg = "RNNoise native library not found"
    if last_err:
        msg += f": {last_err}"
    if platform.system() == "Darwin":
        msg += (
            ". Build from xiph/rnnoise and set RNNOISE_LIB_PATH or place "
            "librnnoise.0.dylib in the lib/ directory."
        )
    raise RNNoiseLoadError(msg)


def _configure_api(lib: ctypes.CDLL) -> None:
    lib.rnnoise_get_frame_size.argtypes = []
    lib.rnnoise_get_frame_size.restype = ctypes.c_int

    lib.rnnoise_create.argtypes = [ctypes.c_void_p]
    lib.rnnoise_create.restype = ctypes.c_void_p

    lib.rnnoise_destroy.argtypes = [ctypes.c_void_p]
    lib.rnnoise_destroy.restype = None

    lib.rnnoise_process_frame.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    lib.rnnoise_process_frame.restype = ctypes.c_float


def load_model(lib: ctypes.CDLL) -> RNNoiseState:
    """Create a RNNoise denoise state with the built-in default model.

    Returns an RNNoiseState on success; raises on failure.
    """
    state_ptr = lib.rnnoise_create(None)
    if not state_ptr:
        raise RNNoiseLoadError("rnnoise_create returned NULL")
    return RNNoiseState(lib, state_ptr)


def validate_frame_size(lib: ctypes.CDLL) -> int:
    """Return the expected native frame size; raise if unexpected."""
    fs = lib.rnnoise_get_frame_size()
    if fs != FRAME_SIZE:
        raise RNNoiseLoadError(
            f"Unexpected RNNoise frame size {fs}, expected {FRAME_SIZE}"
        )
    return fs


def process_frame(state: RNNoiseState, pcm_in: NDArray[np.float32]) -> tuple[NDArray[np.float32], float]:
    """Process one 480-sample frame through RNNoise.

    Args:
        state: Active denoise state.
        pcm_in: float32 array of exactly 480 samples in normalized [-1,1].

    Returns:
        (denoised, vad_probability) where denoised is float32 in [-1,1].
    """
    if len(pcm_in) != FRAME_SIZE:
        raise ValueError(f"Expected {FRAME_SIZE} samples, got {len(pcm_in)}")
    if not np.all(np.isfinite(pcm_in)):
        raise ValueError("Input contains non-finite samples")

    scaled_in = (pcm_in * _SCALE_UP).astype(np.float32)
    out_buf = np.empty(FRAME_SIZE, dtype=np.float32)
    in_buf = np.ascontiguousarray(scaled_in)

    vad = state._lib.rnnoise_process_frame(
        state.ptr,
        out_buf.ctypes.data,
        in_buf.ctypes.data,
    )
    denoised = (out_buf * _SCALE_DOWN).astype(np.float32)
    return denoised, float(vad)


class RNNoiseProcessor:
    """FrameProcessor-compatible RNNoise denoiser wrapper.

    Implements the reset/process/close contract expected by the pipeline.
    Loads the native library once at construction; if unavailable, all
    process() calls raise and status reflects the failure.
    """

    def __init__(self) -> None:
        self._lib: ctypes.CDLL | None = None
        self._state: RNNoiseState | None = None
        self._loaded = False
        self._load_error: str | None = None
        self._metrics = RNNoiseMetrics()

        try:
            self._lib = _load_native_library()
            _configure_api(self._lib)
            validate_frame_size(self._lib)
            self._state = load_model(self._lib)
            self._loaded = True
        except (RNNoiseLoadError, OSError, ValueError) as e:
            self._load_error = str(e)
            self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def load_error(self) -> str | None:
        return self._load_error

    @property
    def metrics(self) -> RNNoiseMetrics:
        return self._metrics

    def reset(self) -> None:
        self._metrics.reset()
        if self._loaded and self._lib is not None:
            if self._state is not None:
                self._state.close()
            self._state = load_model(self._lib)

    def process(self, frame: AudioFrame) -> AudioFrame:
        if not self._loaded or self._state is None:
            raise RuntimeError(
                f"RNNoise not available: {self._load_error or 'not loaded'}"
            )
        pcm = frame.pcm[: frame.valid_samples]
        if len(pcm) == 0:
            return frame
        if len(pcm) != FRAME_SIZE:
            raise ValueError(
                f"Expected {FRAME_SIZE} samples, got {len(pcm)}"
            )

        t0 = time.monotonic()
        denoised, _vad = process_frame(self._state, pcm)
        elapsed = time.monotonic() - t0
        self._metrics.record(elapsed)

        out_pcm = np.zeros(FRAME_SAMPLES_PAD, dtype=np.float32)
        out_pcm[: len(denoised)] = denoised

        return AudioFrame(
            session_id=frame.session_id,
            epoch=frame.epoch,
            seq=frame.seq,
            sample_start=frame.sample_start,
            captured_ns=frame.captured_ns,
            sample_rate=frame.sample_rate,
            pcm=out_pcm,
            valid_samples=frame.valid_samples,
            discontinuity=frame.discontinuity,
        )

    def close(self) -> None:
        if self._state is not None:
            self._state.close()
            self._state = None
        self._loaded = False


FRAME_SAMPLES_PAD = FRAME_SIZE
