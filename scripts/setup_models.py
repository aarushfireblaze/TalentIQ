#!/usr/bin/env python3
"""Download the pinned faster-whisper-tiny.en model to models/."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from huggingface_hub import snapshot_download

MODEL_ID = "Systran/faster-whisper-tiny.en"
REVISION = "0d3d19a32d3338f10357c0889762bd8d64bbdeba"
MODEL_DIR = Path("models") / "faster-whisper-tiny.en"
MANIFEST_PATH = Path("models") / "manifest.json"
HF_CACHE = Path(".cache") / "huggingface"

REQUIRED_FILES = [
    "model.bin",
    "config.json",
    "tokenizer.json",
    "vocabulary.txt",
    "README.md",
]


def main() -> int:
    os.environ["HF_HOME"] = str(HF_CACHE)
    MODEL_DIR.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {MODEL_ID}@{REVISION}...")
    try:
        path = snapshot_download(
            MODEL_ID,
            revision=REVISION,
            local_dir=str(MODEL_DIR),
            local_dir_use_symlinks=False,
        )
        print(f"Downloaded to {path}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    manifest: dict[str, str] = {}
    for fname in REQUIRED_FILES:
        fpath = MODEL_DIR / fname
        if not fpath.exists():
            print(f"WARNING: {fname} not found in model dir", file=sys.stderr)
            continue
        sha = hashlib.sha256(fpath.read_bytes()).hexdigest()
        manifest[fname] = sha
        print(f"  {fname}: {sha[:16]}...")

    manifest["model_id"] = MODEL_ID
    manifest["revision"] = REVISION
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest written to {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
