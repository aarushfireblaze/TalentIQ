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

    def test_start_with_recording_returns_listening(self):
        resp = self.client.post("/api/start", json={"device_id": "0", "mode": "raw", "record": True})
        self.assertEqual(resp.status_code, 202)
        data = resp.json()
        self.assertEqual(data["state"], "listening")
        self.assertEqual(data["recording"], True)
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
        self.assertIn(data["stages"]["rnnoise"]["status"], ("unavailable", "failed"))
        self.assertEqual(data["stages"]["hush"]["status"], "unavailable")
        self.assertIn("Hush processor not injected", data["stages"]["hush"]["reason"])

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

class FakeRNNoise:
    def __init__(self):
        self.is_loaded = True
        self.load_error = None
        from voice_filtering.audio.rnnoise import RNNoiseMetrics
        self.metrics = RNNoiseMetrics()

    def process(self, frame):
        return frame

    def reset(self):
        pass


class FakeHush:
    def __init__(self):
        self.is_loaded = True
        self.load_error = None
        from voice_filtering.audio.hush import HushMetrics
        self.metrics = HushMetrics()

    def reset(self):
        pass

    def process(self, frame):
        return frame


class TestCombinedService(unittest.TestCase):
    @patch('voice_filtering.service.HushProcessor')
    @patch('voice_filtering.service.RNNoiseProcessor')
    @patch('voice_filtering.service.CaptureSource')
    @patch('voice_filtering.service.WhisperASR')
    def test_start_capture_error_is_not_reported_as_listening(self, mock_asr, mock_source, mock_rnnoise, mock_hush):
        source = FakeSource()
        source.start = lambda **kwargs: (_ for _ in ()).throw(RuntimeError("device denied"))
        mock_source.return_value = source
        mock_asr.return_value = FakeTranscriber()
        mock_rnnoise.return_value = FakeRNNoise()
        mock_hush.return_value = FakeHush()
        app = create_app("dummy")
        client = TestClient(app)
        reply = client.post('/api/start', json={"mode": "combined"})
        self.assertEqual(reply.status_code, 409)
        self.assertEqual(reply.json()["state"], "error")
        self.assertEqual(reply.json()["last_error"]["stage"], "capture")

    @patch('voice_filtering.service.HushProcessor')
    @patch('voice_filtering.service.RNNoiseProcessor')
    @patch('voice_filtering.service.CaptureSource')
    @patch('voice_filtering.service.WhisperASR')
    def test_combined_api_and_runtime_failure_event(self, mock_asr, mock_source, mock_rnnoise, mock_hush):
        mock_source.return_value = FakeSource()
        mock_asr.return_value = FakeTranscriber()
        mock_rnnoise.return_value = FakeRNNoise()
        mock_hush.return_value = FakeHush()
        app = create_app("dummy")
        client = TestClient(app)
        reply = client.post('/api/start', json={"device_id": "0", "mode": "combined", "record": False})
        self.assertEqual(reply.status_code, 202)
        self.assertEqual(reply.json()["stages"]["rnnoise"]["status"], "active")
        self.assertEqual(reply.json()["stages"]["hush"]["status"], "active")
        events = app.state.hub.subscribe("test")
        app.state.controller._stage_failed("hush", "native inference failed")
        self.assertTrue(any(event["type"] == "error" and event["payload"]["stage"] == "hush" for event in events))
        self.assertEqual(client.get('/api/state').json()["last_error"]["stage"], "hush")
        client.post('/api/stop')

    @patch('voice_filtering.service.HushProcessor')
    @patch('voice_filtering.service.RNNoiseProcessor')
    @patch('voice_filtering.service.CaptureSource')
    @patch('voice_filtering.service.WhisperASR')
    def test_combined_start_rejects_missing_hush(self, mock_asr, mock_source, mock_rnnoise, mock_hush):
        mock_source.return_value = FakeSource()
        mock_asr.return_value = FakeTranscriber()
        mock_rnnoise.return_value = FakeRNNoise()
        hush = FakeHush()
        hush.is_loaded = False
        hush.load_error = "model missing"
        mock_hush.return_value = hush
        app = create_app("dummy")
        reply = TestClient(app).post('/api/start', json={"mode": "combined"})
        self.assertEqual(reply.status_code, 409)
        self.assertEqual(reply.json()["error"]["stage"], "hush")
        self.assertEqual(app.state.controller.snapshot()["state"], "idle")

from voice_filtering.asr.whisper import ASRScheduler
original_init = ASRScheduler.__init__

class TestServiceIntegration(unittest.TestCase):
    @patch('voice_filtering.service.RNNoiseProcessor')
    @patch('voice_filtering.service.CaptureSource')
    @patch('voice_filtering.service.WhisperASR')
    def test_integration_event_routing_and_history(self, mock_asr, mock_source, mock_rnnoise):
        mock_source.return_value = FakeSource()
        mock_asr.return_value = FakeTranscriber(["hello integration"])
        mock_rnnoise.return_value = FakeRNNoise()
        
        callback_ref = []
        def mocked_init(self_obj, transcriber, on_transcript, *args, **kwargs):
            callback_ref.append(on_transcript)
            original_init(self_obj, transcriber, on_transcript, *args, **kwargs)

        with patch.object(ASRScheduler, '__init__', mocked_init):
            app = create_app("dummy")
            client = TestClient(app)
            
            self.assertEqual(len(callback_ref), 1)
            on_transcript = callback_ref[0]
            
            # Start service
            resp = client.post("/api/start", json={"device_id": "0", "mode": "raw", "record": False})
            self.assertEqual(resp.status_code, 202)
            
            # Subscribe to hub to prove it publishes exactly once
            hub = app.state.hub
            client_id = "test-client"
            buf = hub.subscribe(client_id)
            
            try:
                # Emit event via the configured callback
                event1 = TranscriptEvent(
                    session_id="sess1", segment_id="seg1", revision=1, kind="final",
                    text="hello integration", start_ms=0, end_ms=100, mode="raw",
                    epoch=0, final_reason="silence"
                )
                on_transcript(event1)
                
                # 1. Hub published once
                self.assertEqual(len(buf), 1)
                hub_event = buf.popleft()
                self.assertEqual(hub_event["payload"]["text"], "hello integration")
                
                # 2. GET state retains accepted event fields
                resp = client.get("/api/state")
                state_data = resp.json()
                self.assertEqual(len(state_data["transcript"]), 1)
                self.assertEqual(state_data["transcript"][0]["text"], "hello integration")
                self.assertEqual(state_data["transcript"][0]["mode"], "raw")
                self.assertEqual(state_data["transcript"][0]["session_id"], "sess1")
                self.assertEqual(state_data["transcript"][0]["epoch"], 0)
                
                # 3. Stop preserves committed history
                resp = client.post("/api/stop")
                self.assertEqual(resp.status_code, 200)
                resp = client.get("/api/state")
                self.assertEqual(len(resp.json()["transcript"]), 1)
                
                # 4. Mode switch preserves committed history
                resp = client.post("/api/mode", json={"mode": "rnnoise"})
                self.assertEqual(resp.status_code, 200)
                resp = client.get("/api/state")
                self.assertEqual(len(resp.json()["transcript"]), 1)
                self.assertEqual(resp.json()["transcript"][0]["mode"], "raw")
                self.assertEqual(resp.json()["transcript"][0]["epoch"], 0)
                
                # Start requested rnnoise
                resp = client.post("/api/start", json={"device_id": "0", "mode": "rnnoise", "record": False})
                self.assertEqual(resp.status_code, 202)
                
                # Emit another event
                event2 = TranscriptEvent(
                    session_id="sess2", segment_id="seg2", revision=1, kind="final",
                    text="new epoch", start_ms=100, end_ms=200, mode="rnnoise",
                    epoch=1, final_reason="silence"
                )
                on_transcript(event2)
                resp = client.get("/api/state")
                self.assertEqual(len(resp.json()["transcript"]), 2)
                self.assertEqual(resp.json()["transcript"][1]["mode"], "rnnoise")
                
                # 5. Clear empties history
                resp = client.post("/api/stop")
                self.assertEqual(resp.status_code, 200)
                resp = client.post("/api/transcript/clear")
                self.assertEqual(resp.status_code, 200)
                resp = client.get("/api/state")
                self.assertEqual(len(resp.json()["transcript"]), 0)
            finally:
                client.post("/api/stop")
                hub.unsubscribe(client_id)

if __name__ == "__main__":
    unittest.main()
