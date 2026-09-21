from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from voice_filtering.contracts import AudioFrame
from voice_filtering.audio.hush_native import WeyaModel, WeyaNC

FRAME_SIZE = 160
SOURCE_RATE = 16000
_METRICS_WINDOW = 1000

class HushMetrics:
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
        return sum(self._window) / len(self._window) * 1000.0

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

class HushProcessor:
    """FrameProcessor-compatible Hush denoiser wrapper.
    
    Implements the reset/process/close contract expected by the pipeline.
    Loads the native library and ONNX bundle once at construction.
    """
    
    def __init__(self) -> None:
        self._loaded = False
        self._load_error: str | None = None
        self._metrics = HushMetrics()
        self._model: WeyaModel | None = None
        self._session: WeyaNC | None = None
        
        base_dir = Path(__file__).parent.parent.parent.parent
        lib_dir = base_dir / "lib"
        import platform
        lib_name = "libweya_nc.so"
        if platform.system() == "Darwin":
            lib_name = "libweya_nc.dylib"
        elif platform.system() == "Windows":
            lib_name = "weya_nc.dll"
            
        lib_path = lib_dir / lib_name
        model_path = base_dir / "models" / "hush" / "advanced_dfnet16k_model_best_onnx.tar.gz"
        
        try:
            if not lib_path.exists():
                raise FileNotFoundError(f"Library not found at {lib_path}")
            if not model_path.exists():
                raise FileNotFoundError(f"Model not found at {model_path}")
                
            self._model = WeyaModel(lib_path=lib_path, model_path=model_path)
            self._session = self._model.create_session(sample_rate=SOURCE_RATE)
            self._loaded = True
        except Exception as e:
            self._load_error = str(e)
            self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def load_error(self) -> str | None:
        return self._load_error

    @property
    def metrics(self) -> HushMetrics:
        return self._metrics

    def reset(self) -> None:
        self._metrics.reset()
        if self._loaded and self._session is not None:
            self._session.reset()

    def process(self, frame: AudioFrame) -> AudioFrame:
        if not self._loaded or self._session is None:
            raise RuntimeError(
                f"Hush not available: {self._load_error or 'not loaded'}"
            )
        pcm = frame.pcm[: frame.valid_samples]
        if len(pcm) == 0:
            return frame
        if len(pcm) != FRAME_SIZE:
            raise ValueError(
                f"Expected {FRAME_SIZE} samples, got {len(pcm)}"
            )
            
        if frame.sample_rate != SOURCE_RATE:
            raise ValueError(
                f"Hush requires {SOURCE_RATE}Hz input, got {frame.sample_rate}Hz"
            )

        t0 = time.monotonic()
        # Native library accepts float32 but it might be between -1 and 1 or actual float32?
        # weya_nc wrapper says: "Accepts int16 or float32 input and returns the same dtype. The frame length must equal frame_length."
        # If float32, weya_nc.py does: `self._buf_in[:] = frame.astype(np.float32)`. So normal [-1, 1] is fine.
        denoised = self._session.process_frame(pcm.astype(np.float32))
        elapsed = time.monotonic() - t0
        self._metrics.record(elapsed)

        out_pcm = np.zeros(FRAME_SIZE, dtype=np.float32)
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
        if self._session is not None:
            self._session.close()
            self._session = None
        if self._model is not None:
            self._model.close()
            self._model = None
        self._loaded = False
