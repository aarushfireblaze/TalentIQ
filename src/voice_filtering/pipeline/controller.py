from __future__ import annotations

import threading
import time
import uuid
from typing import Callable

from voice_filtering.contracts import AudioFrame, TranscriptEvent
from voice_filtering.audio.capture import CaptureSource, enumerate_devices, get_default_device_id
from voice_filtering.audio.resample import StreamingResampler
from voice_filtering.asr.whisper import WhisperASR, ASRScheduler


class PipelineControllerImpl:
    def __init__(
        self,
        source: CaptureSource,
        resampler: StreamingResampler,
        transcriber: WhisperASR,
        scheduler: ASRScheduler,
        on_event: Callable[[dict], None],
        clock=time.monotonic,
    ) -> None:
        self._source = source
        self._resampler = resampler
        self._transcriber = transcriber
        self._scheduler = scheduler
        self._on_event = on_event
        self._clock = clock
        self._state: str = "idle"
        self._session_id: str = ""
        self._epoch: int = 0
        self._device_id: str = ""
        self._mode: str = "raw"
        self._recording: bool = False
        self._transcript: list[dict] = []
        self._last_error: dict | None = None
        self._lock = threading.Lock()
        self._capture_thread: threading.Thread | None = None
        self._dsp_thread: threading.Thread | None = None
        self._running: bool = False
        self._capture_stop_event = threading.Event()
        self._dsp_stop_event = threading.Event()

    def start(self, device_id: str, mode: str, record: bool) -> dict:
        with self._lock:
            if self._state not in ("idle", "error"):
                return {"error": {"code": "INVALID_STATE", "stage": "pipeline", "message": "Already running", "recoverable": False}}
            if mode != "raw":
                return {"error": {"code": "STAGE_UNAVAILABLE", "stage": mode, "message": f"Mode '{mode}' not implemented in M0", "recoverable": False}}
            if not self._transcriber.is_loaded:
                return {"error": {"code": "MODEL_MISSING", "stage": "asr", "message": "ASR model not loaded", "recoverable": True}}
            self._session_id = str(uuid.uuid4())
            self._epoch = 0
            self._device_id = device_id
            self._mode = mode
            self._recording = record
            self._state = "starting"
            self._last_error = None
            self._capture_stop_event.clear()
            self._dsp_stop_event.clear()
            self._running = True
        try:
            self._source.start(device_id=device_id, session_id=self._session_id)
            self._scheduler.start(self._session_id, self._epoch)
            with self._lock:
                self._state = "listening"
            self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._dsp_thread = threading.Thread(target=self._dsp_loop, daemon=True)
            self._capture_thread.start()
            self._dsp_thread.start()
        except Exception as e:
            with self._lock:
                self._state = "error"
                self._last_error = {"code": "AUDIO_DEVICE_ERROR", "stage": "capture", "message": str(e), "recoverable": True}
            self._source.stop()
            return self.snapshot()
        return self.snapshot()

    def stop(self) -> dict:
        with self._lock:
            if self._state == "idle":
                return self._snapshot_locked()
            self._state = "stopping"
            self._running = False
            self._capture_stop_event.set()
            self._dsp_stop_event.set()
        self._source.stop()
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)
        if self._dsp_thread and self._dsp_thread.is_alive():
            self._dsp_thread.join(timeout=2.0)
        self._scheduler.finish(timeout_s=5.0)
        with self._lock:
            self._state = "idle"
        return self.snapshot()

    def switch_mode(self, mode: str) -> dict:
        if mode != "raw":
            return {"error": {"code": "STAGE_UNAVAILABLE", "stage": mode, "message": f"Mode '{mode}' not implemented in M0", "recoverable": False}}
        return self.snapshot()

    def clear_transcript(self) -> dict:
        with self._lock:
            if self._state != "idle":
                return {"error": {"code": "INVALID_STATE", "stage": "pipeline", "message": "Can only clear while idle", "recoverable": False}}
            self._transcript.clear()
        return self.snapshot()

    def _snapshot_locked(self) -> dict:
        stages = {
            "capture": {"status": "active" if self._state == "listening" else "ready", "reason": None, "model_revision": None},
            "rnnoise": {"status": "unavailable", "reason": "Not implemented in M0", "model_revision": None},
            "hush": {"status": "unavailable", "reason": "Not implemented in M0", "model_revision": None},
            "asr": {
                "status": "active" if self._state == "listening" else ("ready" if self._transcriber.is_loaded else "unavailable"),
                "reason": self._transcriber.load_error if not self._transcriber.is_loaded else None,
                "model_revision": None,
            },
        }
        return {
            "state": self._state,
            "session_id": self._session_id,
            "epoch": self._epoch,
            "mode": self._mode,
            "device_id": self._device_id,
            "recording": self._recording,
            "stages": stages,
            "transcript": list(self._transcript),
            "last_error": self._last_error,
            "metrics": {},
        }

    def snapshot(self) -> dict:
        with self._lock:
            return self._snapshot_locked()

    def add_transcript_event(self, event: TranscriptEvent) -> None:
        with self._lock:
            entry = {
                "session_id": event.session_id,
                "segment_id": event.segment_id,
                "revision": event.revision,
                "kind": event.kind,
                "text": event.text,
                "start_ms": event.start_ms,
                "end_ms": event.end_ms,
                "mode": event.mode,
                "epoch": event.epoch,
                "final_reason": event.final_reason,
            }
            if event.kind == "final":
                existing_idx = None
                for i, t in enumerate(self._transcript):
                    if t["session_id"] == event.session_id and t["segment_id"] == event.segment_id:
                        existing_idx = i
                        break
                if existing_idx is not None:
                    self._transcript[existing_idx] = entry
                else:
                    self._transcript.append(entry)
            elif event.kind == "partial":
                replaced = False
                for i, t in enumerate(self._transcript):
                    if (
                        t["session_id"] == event.session_id
                        and t["kind"] == "partial"
                    ):
                        self._transcript[i] = entry
                        replaced = True
                        break
                if not replaced:
                    self._transcript.append(entry)
            if len(self._transcript) > 1000:
                self._transcript = self._transcript[-1000:]

    def _capture_loop(self) -> None:
        while not self._capture_stop_event.is_set():
            frame = self._source.read_frame(timeout_s=0.1)
            if frame is None:
                continue
            resampled = self._resampler.push(frame)
            for rframe in resampled:
                self._scheduler.push_audio(rframe)
        self._resampler.finish()

    def _dsp_loop(self) -> None:
        while not self._dsp_stop_event.is_set():
            self._scheduler.run_step()
            time.sleep(0.01)
