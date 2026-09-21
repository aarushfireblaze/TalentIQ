from __future__ import annotations

import unittest
from unittest.mock import patch

from starlette.testclient import TestClient

from voice_filtering.service import create_app


class FakeSource:
    def start(self, *, device_id, session_id):
        return None

    def stop(self):
        return None

    def read_frame(self, timeout_s):
        return None

    def get_drop_count(self):
        return 0


class FakeResampler:
    def reset(self):
        return None

    def finish(self):
        return []

    def push(self, frame):
        return []


class FakeProcessor:
    load_error = None
    metrics = type("Metrics", (), {"avg_ms": 1.0, "p95_ms": 1.0, "total_frames": 0})()

    def __init__(self, loaded=True, error=None):
        self.is_loaded = loaded
        self.load_error = error

    def reset(self):
        return None

    def process(self, frame):
        return frame


class FakeASR:
    is_loaded = True
    load_error = None

    def __init__(self, model_path):
        self.model_path = model_path

    def load(self):
        return None

    def decode(self, pcm):
        return ""


class TestCombinedService(unittest.TestCase):
    def build_client(self, hush=None, rnnoise=None):
        patches = [
            patch("voice_filtering.service.CaptureSource", return_value=FakeSource()),
            patch("voice_filtering.service.StreamingResampler", return_value=FakeResampler()),
            patch("voice_filtering.service.RNNoiseProcessor", return_value=rnnoise or FakeProcessor()),
            patch("voice_filtering.service.HushProcessor", return_value=hush or FakeProcessor()),
            patch("voice_filtering.service.WhisperASR", FakeASR),
            patch("voice_filtering.service.enumerate_devices", return_value=[]),
            patch("voice_filtering.service.get_default_device_id", return_value=None),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        return TestClient(create_app("model"))

    def test_start_forces_combined_when_legacy_mode_is_sent(self):
        client = self.build_client()
        response = client.post("/api/start", json={"device_id": "0", "mode": "raw", "record": False})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["mode"], "combined")
        client.post("/api/stop")

    def test_runtime_mode_route_is_not_exposed(self):
        client = self.build_client()
        self.assertEqual(client.post("/api/mode", json={"mode": "raw"}).status_code, 404)

    def test_missing_hush_returns_explicit_stage_error(self):
        client = self.build_client(hush=FakeProcessor(loaded=False, error="model missing"))
        response = client.post("/api/start", json={"device_id": "0", "record": False})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["stage"], "hush")

    def test_missing_rnnoise_returns_explicit_stage_error(self):
        client = self.build_client(rnnoise=FakeProcessor(loaded=False, error="native library missing"))
        response = client.post("/api/start", json={"device_id": "0", "record": False})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["stage"], "rnnoise")


if __name__ == "__main__":
    unittest.main()
