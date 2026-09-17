from __future__ import annotations

import asyncio
import json
import threading
import time
from collections import deque
from typing import Any

from voice_filtering.contracts import TranscriptEvent

EVENT_BUFFER_SIZE = 128
HEARTBEAT_INTERVAL_S = 15


class EventHub:
    def __init__(self) -> None:
        self._subscribers: dict[str, deque[dict]] = {}
        self._lock = threading.Lock()
        self._event_counter: int = 0
        self._snapshot: dict | None = None

    def publish(self, event: dict) -> None:
        with self._lock:
            self._event_counter += 1
            event["event_id"] = self._event_counter
            event["emitted_ns"] = str(time.monotonic_ns())
            self._snapshot = event if event.get("type") == "snapshot" else self._snapshot
            dead = []
            for client_id, buf in self._subscribers.items():
                if len(buf) >= EVENT_BUFFER_SIZE:
                    buf.popleft()
                buf.append(event)
            for cid in dead:
                del self._subscribers[cid]

    def subscribe(self, client_id: str) -> deque[dict]:
        with self._lock:
            buf: deque[dict] = deque(maxlen=EVENT_BUFFER_SIZE)
            self._subscribers[client_id] = buf
            if self._snapshot:
                buf.append(self._snapshot)
            return buf

    def unsubscribe(self, client_id: str) -> None:
        with self._lock:
            self._subscribers.pop(client_id, None)

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)

    def make_event(self, type_: str, payload: dict, session_id: str | None = None, epoch: int = 0) -> dict:
        return {
            "v": 1,
            "event_id": 0,
            "type": type_,
            "session_id": session_id,
            "epoch": epoch,
            "emitted_ns": "",
            "payload": payload,
        }

    def publish_state(self, state: str, session_id: str = "", epoch: int = 0) -> None:
        event = self.make_event("state", {"state": state}, session_id=session_id, epoch=epoch)
        self.publish(event)

    def publish_level(self, rms_dbfs: float, peak_dbfs: float, session_id: str = "", epoch: int = 0) -> None:
        event = self.make_event("level", {"rms_dbfs": rms_dbfs, "peak_dbfs": peak_dbfs}, session_id=session_id, epoch=epoch)
        self.publish(event)

    def publish_transcript(self, event: TranscriptEvent) -> None:
        payload = {
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
        sse = self.make_event("transcript", payload, session_id=event.session_id, epoch=event.epoch)
        self.publish(sse)

    def publish_error(self, code: str, stage: str, message: str, recoverable: bool = False) -> None:
        payload = {"code": code, "stage": stage, "message": message, "recoverable": recoverable}
        event = self.make_event("error", payload)
        self.publish(event)
