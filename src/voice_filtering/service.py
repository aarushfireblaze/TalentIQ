from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse, PlainTextResponse
from starlette.routing import Route
from starlette.websockets import WebSocket, WebSocketDisconnect

from voice_filtering.audio.capture import CaptureSource, enumerate_devices, get_default_device_id
from voice_filtering.audio.resample import StreamingResampler
from voice_filtering.asr.whisper import WhisperASR, ASRScheduler
from voice_filtering.pipeline.controller import PipelineControllerImpl
from voice_filtering.events import EventHub


def create_app(model_path: str, host: str = "127.0.0.1", port: int = 8765, dev_recording: bool = False) -> Starlette:
    source = CaptureSource()
    resampler = StreamingResampler()
    transcriber = WhisperASR(model_path)
    hub = EventHub()

    try:
        transcriber.load()
    except Exception as e:
        hub.publish_error("MODEL_MISSING", "asr", str(e), recoverable=True)

    scheduler = ASRScheduler(transcriber, hub.publish_transcript)
    controller = PipelineControllerImpl(
        source=source, resampler=resampler, transcriber=transcriber,
        scheduler=scheduler, on_event=hub.publish_transcript,
    )

    async def get_state(request: Request) -> JSONResponse:
        snap = controller.snapshot()
        return JSONResponse(snap)

    async def get_devices(request: Request) -> JSONResponse:
        devices = enumerate_devices()
        default_id = get_default_device_id()
        return JSONResponse({"devices": devices, "default_device_id": default_id})

    async def post_start(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": {"code": "INVALID_STATE", "stage": "api", "message": "Invalid JSON", "recoverable": False}}, status_code=422)
        if not isinstance(body, dict):
            return JSONResponse({"error": {"code": "INVALID_STATE", "stage": "api", "message": "Invalid JSON", "recoverable": False}}, status_code=422)
        device_id = body.get("device_id", "0")
        mode = body.get("mode", "raw")
        record = body.get("record", False)
        result = controller.start(device_id, mode, record)
        if "error" in result:
            status = 409 if result["error"]["code"] in ("INVALID_STATE", "STAGE_UNAVAILABLE") else 422
            return JSONResponse(result, status_code=status)
        hub.publish_state("listening", controller._session_id, controller._epoch)
        return JSONResponse(result, status_code=202)

    async def post_stop(request: Request) -> JSONResponse:
        result = controller.stop()
        hub.publish_state("idle")
        return JSONResponse(result)

    async def post_mode(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": {"code": "INVALID_STATE", "stage": "api", "message": "Invalid JSON", "recoverable": False}}, status_code=422)
        mode = body.get("mode", "raw")
        result = controller.switch_mode(mode)
        if "error" in result:
            return JSONResponse(result, status_code=409)
        return JSONResponse(result)

    async def post_clear(request: Request) -> JSONResponse:
        result = controller.clear_transcript()
        if "error" in result:
            return JSONResponse(result, status_code=409)
        return JSONResponse(result)

    async def get_events(request: Request) -> StreamingResponse:
        client_id = str(uuid.uuid4())
        buf = hub.subscribe(client_id)

        async def event_generator():
            try:
                while True:
                    while buf:
                        event = buf.popleft()
                        yield f"data: {json.dumps(event)}\n\n"
                    await asyncio.sleep(0.05)
                    yield f": heartbeat\n\n"
            except asyncio.CancelledError:
                pass
            finally:
                hub.unsubscribe(client_id)

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    async def index(request: Request) -> HTMLResponse:
        ui_path = Path(__file__).parent.parent.parent / "apps" / "ui" / "index.html"
        if ui_path.exists():
            return HTMLResponse(ui_path.read_text())
        return HTMLResponse("<h1>Voice Filtering M0</h1><p>UI not found</p>")

    async def static_css(request: Request) -> PlainTextResponse:
        css_path = Path(__file__).parent.parent.parent / "apps" / "ui" / "styles.css"
        if css_path.exists():
            return PlainTextResponse(css_path.read_text(), media_type="text/css")
        return PlainTextResponse("", media_type="text/css")

    async def static_js(request: Request) -> PlainTextResponse:
        js_path = Path(__file__).parent.parent.parent / "apps" / "ui" / "app.js"
        if js_path.exists():
            return PlainTextResponse(js_path.read_text(), media_type="application/javascript")
        return PlainTextResponse("", media_type="application/javascript")

    from starlette.responses import StreamingResponse

    routes = [
        Route("/api/state", get_state, methods=["GET"]),
        Route("/api/devices", get_devices, methods=["GET"]),
        Route("/api/start", post_start, methods=["POST"]),
        Route("/api/stop", post_stop, methods=["POST"]),
        Route("/api/mode", post_mode, methods=["POST"]),
        Route("/api/transcript/clear", post_clear, methods=["POST"]),
        Route("/api/events", get_events, methods=["GET"]),
        Route("/", index, methods=["GET"]),
        Route("/styles.css", static_css, methods=["GET"]),
        Route("/app.js", static_js, methods=["GET"]),
    ]

    app = Starlette(routes=routes)
    app.state.controller = controller
    app.state.hub = hub
    return app
