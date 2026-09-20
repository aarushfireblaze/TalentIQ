from __future__ import annotations

import threading
import time
import uuid
from dataclasses import replace
from typing import Callable

import numpy as np

from voice_filtering.contracts import AudioFrame, TranscriptEvent
from voice_filtering.audio.capture import CaptureSource, enumerate_devices, get_default_device_id
from voice_filtering.audio.resample import StreamingResampler
from voice_filtering.asr.whisper import WhisperASR, ASRScheduler
from voice_filtering.audio.recording import WAVWriter
from pathlib import Path

_VALID_MODES = ("raw", "rnnoise", "hush", "combined")


class PipelineControllerImpl:
    def __init__(
        self,
        source: CaptureSource,
        resampler: StreamingResampler,
        transcriber: WhisperASR,
        scheduler: ASRScheduler,
        on_event: Callable[[dict], None],
        on_level: Callable[[float, float, str, int], None] = lambda r, p, s, e: None,
        clock=time.monotonic,
        rnnoise=None,
        hush=None,
        on_error: Callable[[dict], None] = lambda error: None,
        dev_recording: bool = False,
    ) -> None:
        self._source = source
        self._resampler = resampler
        self._transcriber = transcriber
        self._scheduler = scheduler
        self._on_event = on_event
        self._on_level = on_level
        self._clock = clock
        self._rnnoise = rnnoise
        self._hush = hush
        self._on_error = on_error
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
        self._pending_mode: str | None = None
        self._drop_count: int = 0
        self._gap_count: int = 0
        self._mode_switch_count: int = 0
        self._dev_recording = dev_recording
        self._raw_writer = WAVWriter(Path("artifacts/m6/recordings"), 48000)
        self._rnnoise_writer = WAVWriter(Path("artifacts/m6/recordings"), 48000)
        self._hush_writer = WAVWriter(Path("artifacts/m6/recordings"), 16000)
        self._combined_writer = WAVWriter(Path("artifacts/m6/recordings"), 16000)

    def start(self, device_id: str, mode: str, record: bool) -> dict:
        with self._lock:
            if self._state not in ("idle", "error"):
                return {"error": {"code": "INVALID_STATE", "stage": "pipeline", "message": "Already running", "recoverable": False}}
            if mode not in _VALID_MODES:
                return {"error": {"code": "INVALID_MODE", "stage": "pipeline", "message": f"Mode '{mode}' not supported", "recoverable": False}}
            if mode in ("rnnoise", "combined") and not self._rnnoise_available():
                return {"error": {"code": "STAGE_UNAVAILABLE", "stage": "rnnoise", "message": self._rnnoise_unavailable_reason(), "recoverable": False}}
            if mode in ("hush", "combined") and not self._hush_available():
                return {"error": {"code": "STAGE_UNAVAILABLE", "stage": "hush", "message": self._hush_unavailable_reason(), "recoverable": False}}
            if not self._transcriber.is_loaded:
                return {"error": {"code": "MODEL_MISSING", "stage": "asr", "message": "ASR model not loaded", "recoverable": True}}
            self._session_id = str(uuid.uuid4())
            self._epoch = 0
            self._device_id = device_id
            self._mode = mode
            self._recording = record
            self._state = "starting"
            self._last_error = None
            self._pending_mode = None
            self._drop_count = 0
            self._gap_count = 0
            self._mode_switch_count = 0
            self._capture_stop_event.clear()
            self._dsp_stop_event.clear()
            self._running = True
            
            if self._recording and self._dev_recording:
                self._raw_writer.start(self._session_id + "_raw")
                self._rnnoise_writer.start(self._session_id + "_rnnoise")
                self._hush_writer.start(self._session_id + "_hush")
                self._combined_writer.start(self._session_id + "_combined")
        try:
            self._source.start(device_id=device_id, session_id=self._session_id)
        except Exception as e:
            with self._lock:
                self._state = "error"
                self._last_error = {"code": "AUDIO_DEVICE_ERROR", "stage": "capture", "message": str(e), "recoverable": True}
            self._source.stop()
            self._on_error(self._last_error)
            return self.snapshot()
        for stage, reset in (
            ("resampler", self._resampler.reset),
            ("rnnoise", self._rnnoise.reset if self._rnnoise is not None else lambda: None),
            ("hush", self._hush.reset if self._hush is not None else lambda: None),
            ("asr", lambda: self._scheduler.start(self._session_id, self._epoch, self._mode)),
        ):
            try:
                reset()
            except Exception as error:
                self._stage_failed(stage, str(error))
                self._source.stop()
                return self.snapshot()
        with self._lock:
            self._state = "listening"
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._dsp_thread = threading.Thread(target=self._dsp_loop, daemon=True)
        self._capture_thread.start()
        self._dsp_thread.start()
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
        
        self._raw_writer.stop()
        self._rnnoise_writer.stop()
        self._hush_writer.stop()
        self._combined_writer.stop()
        
        with self._lock:
            self._state = "idle"
        return self.snapshot()

    def switch_mode(self, mode: str) -> dict:
        with self._lock:
            if mode not in _VALID_MODES:
                return {"error": {"code": "INVALID_MODE", "stage": "pipeline", "message": f"Mode '{mode}' not supported", "recoverable": False}}
            if mode in ("rnnoise", "combined") and not self._rnnoise_available():
                return {"error": {"code": "STAGE_UNAVAILABLE", "stage": "rnnoise", "message": self._rnnoise_unavailable_reason(), "recoverable": False}}
            if mode in ("hush", "combined") and not self._hush_available():
                return {"error": {"code": "STAGE_UNAVAILABLE", "stage": "hush", "message": self._hush_unavailable_reason(), "recoverable": False}}
            if self._state not in ("listening", "idle"):
                return {"error": {"code": "INVALID_STATE", "stage": "pipeline", "message": "Can only switch mode while idle or listening", "recoverable": False}}
            if mode == self._mode and self._state == "idle":
                return self._snapshot_locked()
            if self._state == "idle":
                self._mode = mode
                return self._snapshot_locked()
            self._pending_mode = mode
        return self.snapshot()

    def _apply_mode_switch(self) -> bool:
        """Called from capture loop at a frame boundary to apply pending mode."""
        with self._lock:
            pending = self._pending_mode
            if pending is None:
                return True
            if pending == self._mode:
                self._pending_mode = None
                return True
            self._pending_mode = None
            self._mode = pending
            self._epoch += 1
            self._mode_switch_count += 1
            self._gap_count += 1
        for stage, reset in (
            ("asr", lambda: self._scheduler.reset(self._session_id, self._epoch, self._mode)),
            ("resampler", self._resampler.reset),
            ("rnnoise", self._rnnoise.reset if self._rnnoise is not None else lambda: None),
            ("hush", self._hush.reset if self._hush is not None else lambda: None),
        ):
            try:
                reset()
            except Exception as error:
                return self._stage_failed(stage, str(error))
        return True

    def clear_transcript(self) -> dict:
        with self._lock:
            if self._state != "idle":
                return {"error": {"code": "INVALID_STATE", "stage": "pipeline", "message": "Can only clear while idle", "recoverable": False}}
            self._transcript.clear()
        return self.snapshot()

    def _rnnoise_available(self) -> bool:
        return self._rnnoise is not None and self._rnnoise.is_loaded

    def _rnnoise_unavailable_reason(self) -> str:
        if self._rnnoise is None:
            return "RNNoise processor not injected"
        if self._rnnoise.load_error:
            return self._rnnoise.load_error
        return "RNNoise not loaded"

    def _hush_available(self) -> bool:
        return self._hush is not None and self._hush.is_loaded

    def _hush_unavailable_reason(self) -> str:
        if self._hush is None:
            return "Hush processor not injected"
        if self._hush.load_error:
            return self._hush.load_error
        return "Hush not loaded"

    def _snapshot_locked(self) -> dict:
        if self._rnnoise is not None and self._rnnoise.is_loaded:
            rnnoise_status = (
                "active" if self._state == "listening" and self._mode in ("rnnoise", "combined")
                else "ready"
            )
            rnnoise_reason = None
        elif self._rnnoise is not None and self._rnnoise.load_error:
            rnnoise_status = "failed"
            rnnoise_reason = self._rnnoise.load_error
        else:
            rnnoise_status = "unavailable"
            rnnoise_reason = self._rnnoise_unavailable_reason()

        rnnoise_rev = None
        if self._rnnoise is not None and self._rnnoise.is_loaded:
            rnnoise_rev = "xiph/rnnoise@70f1d25"

        if self._hush is not None and self._hush.is_loaded:
            hush_status = (
                "active" if self._state == "listening" and self._mode in ("hush", "combined")
                else "ready"
            )
            hush_reason = None
        elif self._hush is not None and self._hush.load_error:
            hush_status = "failed"
            hush_reason = self._hush.load_error
        else:
            hush_status = "unavailable"
            hush_reason = self._hush_unavailable_reason()

        hush_rev = None
        if self._hush is not None and self._hush.is_loaded:
            hush_rev = "weya-ai/hush@a55d932cbf6344d284ac985f21e7f6e5bc4d38a5"

        stages = {
            "capture": {
                "status": "active" if self._state == "listening" else "ready",
                "reason": None,
                "model_revision": None,
            },
            "rnnoise": {
                "status": rnnoise_status,
                "reason": rnnoise_reason,
                "model_revision": rnnoise_rev,
            },
            "hush": {
                "status": hush_status,
                "reason": hush_reason,
                "model_revision": hush_rev,
            },
            "asr": {
                "status": "active" if self._state == "listening" else ("ready" if self._transcriber.is_loaded else "unavailable"),
                "reason": self._transcriber.load_error if not self._transcriber.is_loaded else None,
                "model_revision": None,
            },
        }

        metrics: dict = {}
        if self._rnnoise is not None and self._rnnoise.is_loaded:
            m = self._rnnoise.metrics
            metrics["rnnoise_avg_ms"] = m.avg_ms
            metrics["rnnoise_p95_ms"] = m.p95_ms
            metrics["rnnoise_total_frames"] = m.total_frames
        if self._hush is not None and self._hush.is_loaded:
            m = self._hush.metrics
            metrics["hush_avg_ms"] = m.avg_ms
            metrics["hush_p95_ms"] = m.p95_ms
            metrics["hush_total_frames"] = m.total_frames
        capture_drops = self._source.get_drop_count() if hasattr(self._source, "get_drop_count") else 0
        asr_drops = self._scheduler.get_ingress_drop_count() if hasattr(self._scheduler, "get_ingress_drop_count") else 0
        metrics["capture_drop_count"] = capture_drops
        metrics["asr_drop_count"] = asr_drops
        metrics["drop_count"] = capture_drops + asr_drops
        metrics["gap_count"] = self._gap_count
        metrics["mode_switch_count"] = self._mode_switch_count

        return {
            "state": self._state,
            "session_id": self._session_id,
            "epoch": self._epoch,
            "mode": self._mode,
            "pending_mode": self._pending_mode,
            "device_id": self._device_id,
            "recording": self._recording,
            "stages": stages,
            "transcript": list(self._transcript),
            "last_error": self._last_error,
            "metrics": metrics,
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

    def _capture_loop_body(self, frame: AudioFrame) -> bool:
        """Process a single captured frame. Returns False if capture should stop."""
        if not self._apply_mode_switch():
            return False

        with self._lock:
            epoch = self._epoch
            session_id = self._session_id
        frame = replace(frame, epoch=epoch, session_id=session_id)

        pcm = frame.pcm[: frame.valid_samples]
        if len(pcm) > 0:
            rms = float(np.sqrt(np.mean(pcm.astype(np.float32) ** 2)))
            if rms > 0:
                dbfs = 20.0 * np.log10(rms)
            else:
                dbfs = -100.0
            self._on_level(dbfs, dbfs, self._session_id, self._epoch)

        self._raw_writer.write_frame(frame)

        current_mode = self._mode
        if current_mode in ("rnnoise", "combined"):
            if not self._rnnoise_available():
                return self._stage_failed("rnnoise", self._rnnoise_unavailable_reason())
            try:
                frame = self._rnnoise.process(frame)
                self._rnnoise_writer.write_frame(frame)
            except Exception as e:
                return self._stage_failed("rnnoise", str(e))

        try:
            resampled = self._resampler.push(frame)
        except Exception as e:
            return self._stage_failed("resampler", str(e))
        for rframe in resampled:
            if current_mode in ("hush", "combined"):
                if not self._hush_available():
                    return self._stage_failed("hush", self._hush_unavailable_reason())
                try:
                    rframe = self._hush.process(rframe)
                    self._hush_writer.write_frame(rframe)
                except Exception as e:
                    return self._stage_failed("hush", str(e))
            if current_mode == "combined":
                self._combined_writer.write_frame(rframe)
            self._scheduler.push_audio(rframe)
        return True

    def _stage_failed(self, stage: str, message: str) -> bool:
        error = {"code": "STAGE_FAILED", "stage": stage, "message": message, "recoverable": False}
        with self._lock:
            self._last_error = error
            self._state = "error"
            self._running = False
            self._capture_stop_event.set()
            self._dsp_stop_event.set()
        self._source.stop()
        self._on_error(error)
        return False

    def _capture_loop(self) -> None:
        while not self._capture_stop_event.is_set():
            frame = self._source.read_frame(timeout_s=0.1)
            if frame is None:
                continue
            if not self._capture_loop_body(frame):
                break

        self._resampler.finish()

    def _dsp_loop(self) -> None:
        while not self._dsp_stop_event.is_set():
            self._scheduler.run_step()
            time.sleep(0.01)
