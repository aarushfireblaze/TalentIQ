import unittest
import json
import asyncio
import time
import uuid
from unittest.mock import MagicMock, patch, AsyncMock

from starlette.testclient import TestClient

from voice_filtering.contracts import AudioFrame, TranscriptEvent
from voice_filtering.audio.capture import CaptureSource
from voice_filtering.audio.resample import StreamingResampler
from voice_filtering.asr.whisper import WhisperASR, ASRScheduler
from voice_filtering.pipeline.controller import PipelineControllerImpl
from voice_filtering.events import EventHub
from voice_filtering.service import create_app


class FakeTranscriber:
    def __init__(self, texts=None):
        self._texts = texts or ["hello world"]
        self._call_count = 0
        self._loaded = True
        self._load_error = None

    @property
    def is_loaded(self):
        return self._loaded

    @property
    def load_error(self):
        return self._load_error

    def decode(self, pcm16k):
        time.sleep(0.005)
        idx = self._call_count % len(self._texts)
        self._call_count += 1
        return self._texts[idx]


class FakeSource:
    def __init__(self):
        self._running = False

    def start(self, *, device_id, session_id):
        self._running = True

    def read_frame(self, timeout_s):
        return None

    def stop(self):
        self._running = False


def make_app():
    source = FakeSource()
    resampler = StreamingResampler()
    transcriber = FakeTranscriber(["hello world"])
    hub = EventHub()
    scheduler = ASRScheduler(transcriber, hub.publish_transcript)
    controller = PipelineControllerImpl(
        source=source, resampler=resampler, transcriber=transcriber,
        scheduler=scheduler, on_event=hub.publish_transcript,
    )
    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.requests import Request
    from starlette.responses import JSONResponse, HTMLResponse

    async def get_state(request):
        return JSONResponse(controller.snapshot())

    async def get_devices(request):
        return JSONResponse({"devices": [{"id": "0", "name": "Fake Device", "host_api": "test", "max_input_channels": 1, "default_sample_rate": 48000}], "default_device_id": "0"})

    async def post_start(request):
        body = await request.json()
        result = controller.start(body.get("device_id", "0"), body.get("mode", "raw"), body.get("record", False))
        if "error" in result:
            return JSONResponse(result, status_code=409)
        return JSONResponse(result, status_code=202)

    async def post_stop(request):
        result = controller.stop()
        return JSONResponse(result)

    async def post_mode(request):
        body = await request.json()
        result = controller.switch_mode(body.get("mode", "raw"))
        if "error" in result:
            return JSONResponse(result, status_code=409)
        return JSONResponse(result)

    async def post_clear(request):
        result = controller.clear_transcript()
        if "error" in result:
            return JSONResponse(result, status_code=409)
        return JSONResponse(result)

    async def get_events(request):
        from starlette.responses import StreamingResponse
        client_id = str(uuid.uuid4())
        buf = hub.subscribe(client_id)
        async def gen():
            try:
                while True:
                    while buf:
                        event = buf.popleft()
                        yield f"data: {json.dumps(event)}\n\n"
                    await asyncio.sleep(0.05)
            except asyncio.CancelledError:
                pass
            finally:
                hub.unsubscribe(client_id)
        return StreamingResponse(gen(), media_type="text/event-stream")

    app = Starlette(routes=[
        Route("/api/state", get_state, methods=["GET"]),
        Route("/api/devices", get_devices, methods=["GET"]),
        Route("/api/start", post_start, methods=["POST"]),
        Route("/api/stop", post_stop, methods=["POST"]),
        Route("/api/mode", post_mode, methods=["POST"]),
        Route("/api/transcript/clear", post_clear, methods=["POST"]),
        Route("/api/events", get_events, methods=["GET"]),
    ])
    app.state.controller = controller
    app.state.hub = hub
    return app


class TestServiceState(unittest.TestCase):
    def setUp(self):
        self.app = make_app()
        self.client = TestClient(self.app)

    def test_get_state_idle(self):
        resp = self.client.get("/api/state")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["state"], "idle")

    def test_get_devices(self):
        resp = self.client.get("/api/devices")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("devices", data)
        self.assertIn("default_device_id", data)

    def test_start_returns_listening(self):
        resp = self.client.post("/api/start", json={"device_id": "0", "mode": "raw", "record": False})
        self.assertEqual(resp.status_code, 202)
        data = resp.json()
        self.assertEqual(data["state"], "listening")
        self.client.post("/api/stop")

    def test_stop_returns_idle(self):
        self.client.post("/api/start", json={"device_id": "0", "mode": "raw", "record": False})
        resp = self.client.post("/api/stop")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["state"], "idle")

    def test_duplicate_start_rejected(self):
        self.client.post("/api/start", json={"device_id": "0", "mode": "raw", "record": False})
        resp = self.client.post("/api/start", json={"device_id": "0", "mode": "raw", "record": False})
        self.assertEqual(resp.status_code, 409)
        self.client.post("/api/stop")

    def test_unavailable_mode_rejected(self):
        resp = self.client.post("/api/mode", json={"mode": "rnnoise"})
        self.assertEqual(resp.status_code, 409)
        data = resp.json()
        self.assertEqual(data["error"]["code"], "STAGE_UNAVAILABLE")

    def test_clear_idle(self):
        resp = self.client.post("/api/transcript/clear")
        self.assertEqual(resp.status_code, 200)

    def test_clear_while_running_rejected(self):
        self.client.post("/api/start", json={"device_id": "0", "mode": "raw", "record": False})
        resp = self.client.post("/api/transcript/clear")
        self.assertEqual(resp.status_code, 409)
        self.client.post("/api/stop")

    def test_snapshot_reconnect(self):
        resp1 = self.client.get("/api/state")
        resp2 = self.client.get("/api/state")
        self.assertEqual(resp1.json()["state"], resp2.json()["state"])

    def test_stages_unavailable(self):
        resp = self.client.get("/api/state")
        data = resp.json()
        self.assertEqual(data["stages"]["rnnoise"]["status"], "unavailable")
        self.assertEqual(data["stages"]["hush"]["status"], "unavailable")
        self.assertIn("Not implemented in M0", data["stages"]["rnnoise"]["reason"])

    def test_mode_raw_accepted(self):
        resp = self.client.post("/api/mode", json={"mode": "raw"})
        self.assertEqual(resp.status_code, 200)

    def test_transcript_event_appears(self):
        event = TranscriptEvent(
            session_id="s1", segment_id=str(uuid.uuid4()), revision=1,
            kind="final", text="test", start_ms=0, end_ms=100, mode="raw",
            epoch=0, final_reason="silence",
        )
        self.app.state.controller.add_transcript_event(event)
        resp = self.client.get("/api/state")
        data = resp.json()
        self.assertEqual(len(data["transcript"]), 1)


class TestServiceErrors(unittest.TestCase):
    def setUp(self):
        self.app = make_app()
        self.client = TestClient(self.app)

    def test_invalid_json_stop(self):
        resp = self.client.post("/api/stop", content=b"not json", headers={"Content-Type": "application/json"})
        self.assertEqual(resp.status_code, 200)

    def test_empty_body_mode(self):
        resp = self.client.post("/api/mode", json={})
        self.assertEqual(resp.status_code, 200)

    def test_empty_body_start(self):
        resp = self.client.post("/api/start", json={})
        self.assertIn(resp.status_code, (202, 409))


class TestServiceTranscript(unittest.TestCase):
    def setUp(self):
        self.app = make_app()
        self.client = TestClient(self.app)

    def test_partial_replaced_by_final(self):
        ctrl = self.app.state.controller
        partial = TranscriptEvent(
            session_id="s1", segment_id="seg1", revision=1, kind="partial",
            text="hel", start_ms=0, end_ms=50, mode="raw", epoch=0,
        )
        ctrl.add_transcript_event(partial)
        final = TranscriptEvent(
            session_id="s1", segment_id="seg1", revision=2, kind="final",
            text="hello world", start_ms=0, end_ms=100, mode="raw", epoch=0,
            final_reason="silence",
        )
        ctrl.add_transcript_event(final)
        resp = self.client.get("/api/state")
        data = resp.json()
        finals = [t for t in data["transcript"] if t["kind"] == "final"]
        self.assertEqual(len(finals), 1)
        self.assertEqual(finals[0]["text"], "hello world")

    def test_transcript_limit(self):
        ctrl = self.app.state.controller
        for i in range(1100):
            event = TranscriptEvent(
                session_id="s1", segment_id=str(uuid.uuid4()), revision=1,
                kind="final", text=f"word{i}", start_ms=i * 100,
                end_ms=(i + 1) * 100, mode="raw", epoch=0, final_reason="silence",
            )
            ctrl.add_transcript_event(event)
        resp = self.client.get("/api/state")
        data = resp.json()
        self.assertLessEqual(len(data["transcript"]), 1000)


if __name__ == "__main__":
    unittest.main()
