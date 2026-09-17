#!/usr/bin/env python3
"""Fetch the JFK test WAV for ASR smoke testing."""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/ggml-org/whisper.cpp/da54572229bcf64ba367d96c7ef15770376c4280/samples/jfk.wav"
OUTPUT_DIR = Path("tests") / "fixtures" / "generated"
OUTPUT_PATH = OUTPUT_DIR / "jfk.wav"
PROVENANCE_PATH = OUTPUT_DIR / "jfk_provenance.json"
EXPECTED_COMMIT = "da54572229bcf64ba367d96c7ef15770376c4280"


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if OUTPUT_PATH.exists():
        print(f"Already exists: {OUTPUT_PATH}")
    else:
        print(f"Fetching {URL}...")
        try:
            req = urllib.request.Request(URL, headers={"User-Agent": "voice-m0-baseline/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1
        if b"<html" in data[:200].lower():
            print("ERROR: Got HTML instead of WAV", file=sys.stderr)
            return 1
        OUTPUT_PATH.write_bytes(data)
        print(f"Wrote {OUTPUT_PATH} ({len(data)} bytes)")

    data = OUTPUT_PATH.read_bytes()
    if len(data) < 44:
        print("ERROR: WAV file too small", file=sys.stderr)
        return 1
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        print("ERROR: Not a valid WAV file", file=sys.stderr)
        return 1
    import struct
    channels = struct.unpack_from("<H", data, 22)[0]
    sample_rate = struct.unpack_from("<I", data, 24)[0]
    bits_per_sample = struct.unpack_from("<H", data, 34)[0]
    print(f"WAV: channels={channels}, rate={sample_rate}, bits={bits_per_sample}")
    if channels != 1:
        print(f"ERROR: Expected mono, got {channels} channels", file=sys.stderr)
        return 1
    if sample_rate != 16000:
        print(f"ERROR: Expected 16kHz, got {sample_rate}Hz", file=sys.stderr)
        return 1
    if bits_per_sample != 16:
        print(f"ERROR: Expected 16-bit, got {bits_per_sample}-bit", file=sys.stderr)
        return 1

    sha256 = hashlib.sha256(data).hexdigest()
    provenance = {
        "url": URL,
        "commit": EXPECTED_COMMIT,
        "sha256": sha256,
        "size": len(data),
        "channels": channels,
        "sample_rate": sample_rate,
        "bits_per_sample": bits_per_sample,
    }
    PROVENANCE_PATH.write_text(json.dumps(provenance, indent=2))
    print(f"SHA256: {sha256}")
    print(f"Provenance: {PROVENANCE_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
