from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import uuid
from collections import deque
from pathlib import Path

import numpy as np

from voice_filtering.contracts import AudioFrame, TranscriptEvent

MODEL_DIR = Path("models")
MANIFEST_PATH = MODEL_DIR / "manifest.json"
DEFAULT_MODEL_ID = "Systran/faster-whisper-tiny.en"
DEFAULT_REVISION = "0d3d19a32d3338f10357c0889762bd8d64bbdeba"

INGRESS_CAP = 100
UTTERANCE_MAX_S = 8.0
UTTERANCE_PREROLL_S = 0.2
PARTIAL_CADENCE_S = 0.75
PARTIAL_MIN_S = 1.0
FINAL_QUEUE_CAP = 4
ASR_FLUSH_TIMEOUT_S = 5.0


class WhisperASR:
    def __init__(self, model_path: str | Path) -> None:
        self._model_path = Path(model_path)
        self._model = None
        self._loaded = False
        self._load_error: str | None = None

    def load(self) -> None:
        from faster_whisper import WhisperModel

        if not self._model_path.exists():
            self._load_error = f"Model directory not found: {self._model_path}"
            raise FileNotFoundError(self._load_error)
        try:
            self._model = WhisperModel(
                str(self._model_path),
                device="cpu",
                compute_type="int8",
                cpu_threads=4,
                num_workers=1,
                local_files_only=True,
            )
            self._loaded = True
        except Exception as e:
            self._load_error = str(e)
            raise

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def decode(self, pcm16k: np.ndarray) -> str:
        if not self._loaded or self._model is None:
            raise RuntimeError("Model not loaded")
        pcm = np.asarray(pcm16k, dtype=np.float32)
        if len(pcm) == 0:
            return ""
        segments, info = self._model.transcribe(
            pcm,
            language="en",
            beam_size=1,
            temperature=0,
            condition_on_previous_text=False,
            vad_filter=False,
        )
        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())
        return " ".join(text_parts).strip()


class ASRScheduler:
    def __init__(self, transcriber: WhisperASR, on_event) -> None:
        self._transcriber = transcriber
        self._on_event = on_event
        self._ingress: deque[AudioFrame] = deque(maxlen=INGRESS_CAP)
        self._utterance_buf: list[AudioFrame] = []
        self._utterance_samples: int = 0
        self._session_id: str = ""
        self._epoch: int = 0
        self._segment_counter: int = 0
        self._running: bool = False
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._speech_start_ns: int = 0
        self._in_speech: bool = False
        self._utterance_start_ms: float = 0.0
        self._final_queue: deque[TranscriptEvent] = deque(maxlen=FINAL_QUEUE_CAP)
        self._drop_count: int = 0
        self._partial_count: int = 0

    def start(self, session_id: str, epoch: int) -> None:
        with self._lock:
            self._session_id = session_id
            self._epoch = epoch
            self._segment_counter = 0
            self._utterance_buf.clear()
            self._utterance_samples = 0
            self._in_speech = False
            self._running = True
            self._final_queue.clear()
            self._drop_count = 0
            self._partial_count = 0

    def push_audio(self, frame: AudioFrame) -> None:
        if not self._running:
            return
        with self._lock:
            if len(self._ingress) >= INGRESS_CAP:
                self._ingress.popleft()
                self._drop_count += 1
            self._ingress.append(frame)

    def finish(self, timeout_s: float = ASR_FLUSH_TIMEOUT_S) -> bool:
        with self._lock:
            self._running = False
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=timeout_s)
        self._flush_utterance()
        return True

    def reset(self, session_id: str, epoch: int) -> None:
        with self._lock:
            self._session_id = session_id
            self._epoch = epoch
            self._segment_counter += 1000
            self._utterance_buf.clear()
            self._utterance_samples = 0
            self._in_speech = False

    def close(self) -> None:
        self.finish()

    def _flush_utterance(self) -> None:
        with self._lock:
            buf = list(self._utterance_buf)
            self._utterance_buf.clear()
            self._utterance_samples = 0
            self._in_speech = False
        if not buf:
            return
        pcm = self._concat_utterance(buf)
        if len(pcm) == 0:
            return
        try:
            text = self._transcriber.decode(pcm)
        except Exception as e:
            print('ASR Decode Error:', e)
            import traceback
            traceback.print_exc()
            return
        if not text.strip():
            print('ASR empty text')
            return
        print('ASR text:', text)
        with self._lock:
            self._segment_counter += 1
            seg_id = str(uuid.uuid4())
            start_ms = self._utterance_start_ms
            end_ms = start_ms + len(buf) * 10.0
            event = TranscriptEvent(
                session_id=self._session_id,
                segment_id=seg_id,
                revision=1,
                kind="final",
                text=text,
                start_ms=start_ms,
                end_ms=end_ms,
                mode="raw",
                epoch=self._epoch,
                final_reason="stop",
            )
            self._final_queue.append(event)
        self._on_event(event)

    def _concat_utterance(self, frames: list[AudioFrame]) -> np.ndarray:
        parts = [f.pcm[: f.valid_samples] for f in frames]
        return np.concatenate(parts) if parts else np.array([], dtype=np.float32)

    def _rms_dbfs(self, pcm: np.ndarray) -> float:
        if len(pcm) == 0:
            return -100.0
        rms = float(np.sqrt(np.mean(pcm.astype(np.float32) ** 2)))
        if rms <= 0:
            return -100.0
        return 20.0 * np.log10(rms)

    def run_step(self) -> bool:
        frames: list[AudioFrame] = []
        with self._lock:
            while self._ingress:
                frames.append(self._ingress.popleft())
        if not frames:
            return False
        for frame in frames:
            rms = self._rms_dbfs(frame.pcm[: frame.valid_samples])
            if rms > -45.0:
                if not self._in_speech:
                    self._in_speech = True
                    self._speech_start_ns = frame.captured_ns
                    self._utterance_start_ms = frame.sample_start * 1000.0 / 48000.0
                    self._utterance_buf.clear()
                    self._utterance_samples = 0
                self._utterance_buf.append(frame)
                self._utterance_samples += frame.valid_samples
                duration_s = self._utterance_samples / 16000.0
                if duration_s >= UTTERANCE_MAX_S:
                    self._finalize_utterance("max_duration")
            else:
                if self._in_speech:
                    self._utterance_buf.append(frame)
                    self._utterance_samples += frame.valid_samples
                    duration_s = self._utterance_samples / 16000.0
                    if duration_s >= 0.6:
                        self._finalize_utterance("silence")
        return True

    def _finalize_utterance(self, reason: str) -> None:
        buf = list(self._utterance_buf)
        self._utterance_buf.clear()
        self._utterance_samples = 0
        self._in_speech = False
        if not buf:
            return
        pcm = self._concat_utterance(buf)
        if len(pcm) == 0:
            return
        try:
            text = self._transcriber.decode(pcm)
        except Exception as e:
            print('ASR Decode Error:', e)
            import traceback
            traceback.print_exc()
            return
        if not text.strip():
            print('ASR empty text')
            return
        print('ASR text:', text)
        with self._lock:
            self._segment_counter += 1
            seg_id = str(uuid.uuid4())
            start_ms = self._utterance_start_ms
            end_ms = start_ms + len(buf) * 10.0
            event = TranscriptEvent(
                session_id=self._session_id,
                segment_id=seg_id,
                revision=1,
                kind="final",
                text=text,
                start_ms=start_ms,
                end_ms=end_ms,
                mode="raw",
                epoch=self._epoch,
                final_reason=reason,
            )
            self._final_queue.append(event)
        self._on_event(event)

    def get_ingress_drop_count(self) -> int:
        with self._lock:
            return self._drop_count
