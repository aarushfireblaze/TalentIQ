#!/usr/bin/env python3
"""Entry point for voice_filtering service."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> int:
    parser = argparse.ArgumentParser(description="Voice Filtering M0 Baseline")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (M0: loopback only)")
    parser.add_argument("--port", type=int, default=8765, help="Bind port")
    parser.add_argument("--model", default="models/faster-whisper-tiny.en", help="Model path")
    parser.add_argument("--dev-recording", action="store_true", help="Enable dev recording")
    args = parser.parse_args()

    if args.host not in ("127.0.0.1", "localhost"):
        print("ERROR: M0 only supports loopback binding (127.0.0.1 or localhost)", file=sys.stderr)
        return 1

    from voice_filtering.service import create_app
    import uvicorn

    app = create_app(
        model_path=args.model,
        host=args.host,
        port=args.port,
        dev_recording=args.dev_recording,
    )
    print(f"Starting voice filtering on http://{args.host}:{args.port}")
    print(f"Model: {args.model}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
