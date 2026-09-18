# M1 RNNoise Handoff

## Status: Complete — RNNoise mode implemented, native load blocked

## Scope

Implemented M1 RNNoise-only mode: native wrapper, pipeline integration, UI mode switching, epoch/reset, metrics, deterministic replay, and 30 dedicated tests. Hush/Combined remain unavailable.

## Files changed

| File | Change |
|---|---|
| `src/voice_filtering/audio/rnnoise.py` | **NEW** — RNNoise native wrapper with ctypes FFI, load fallback, FrameProcessor protocol, timing metrics |
| `src/voice_filtering/pipeline/controller.py` | Added RNNoise processor injection, mode switching (raw↔rnnoise) with epoch boundaries, `_capture_loop_body()`, metrics |
| `src/voice_filtering/service.py` | Injected RNNoiseProcessor, updated error reporting and stage availability |
| `apps/ui/index.html` | RNNoise radio button (enabled when available), metrics section, mode tags on transcript |
| `apps/ui/app.js` | Handles RNNoise stage status, mode switching, metrics display |
| `apps/ui/styles.css` | Added `.mode-tag` style |
| `scripts/replay_ab.py` | **NEW** — Deterministic A/B replay of 48kHz WAV through Raw and RNNoise modes |
| `tests/test_rnnoise.py` | **NEW** — 30 M1 tests: wrapper validation, mode switching, epoch/reset, failure/no-fallback, metrics, lifecycle |
| `tests/test_service.py` | Updated `test_stages_unavailable` for M1 stage status semantics |

## RNNoise native build evidence

- **Source**: xiph/rnnoise commit `70f1d256acd4b34a572f999a05c87bf00b67730d`
- **Build**: autotools (autogen.sh → configure → make), CC=`gcc -arch arm64 -isysroot MacOSX14.4.sdk`, MACOSX_DEPLOYMENT_TARGET=12.0
- **Output**: `librnnoise.0.dylib` — Mach-O 64-bit arm64, depends only on libSystem.B.dylib
- **Install**: `/tmp/rnnoise-install/lib/librnnoise.0.dylib`
- **API confirmed**: `rnnoise_get_frame_size()` returns 480; `rnnoise_create(NULL)` uses default model; `rnnoise_process_frame(st, out, in)` returns float VAD probability; `rnnoise_destroy(st)` frees state
- **Model data**: embedded as `src/rnnoise_data.c` (compiled into dylib), hash from `model_version` file: `0a8755f8e2d834eff6a54714ecc7d75f9932e845df35f8b59bc52a7cfe6e8b37`
- **License**: BSD-3-Clause (upstream), model data included

### Native smoke blocker

Python ctypes probe of the built dylib **timed out** (20s). Root cause undetermined — may be a loader issue with the SDK-built library, a macOS security gate, or a library initialization hang. The dylib loads via `otool` and `file` correctly. The wrapper is designed to detect this at runtime and set stage to `failed` with the load error.

## How to attempt native load

```bash
# 1. Place the built dylib in the project lib/ directory
mkdir -p lib
cp /tmp/rnnoise-install/lib/librnnoise.0.dylib lib/

# 2. Or set the env var
export RNNOISE_LIB_PATH=/tmp/rnnoise-install/lib/librnnoise.0.dylib

# 3. Start the service — it will attempt to load at startup
.venv/bin/python -m voice_filtering --model models/faster-whisper-tiny.en

# Check snapshot for rnnoise stage status:
# curl http://127.0.0.1:8765/api/state | python -m json.tool | grep -A2 rnnoise
```

If the load succeeds, rnnoise stage shows `status: "ready"`. If it times out or fails, it shows `status: "failed"` with the error reason.

## Setup commands

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --cache-dir .cache/pip -r requirements.lock.txt
.venv/bin/python -m pip install --cache-dir .cache/pip --no-deps --no-build-isolation -e .
.venv/bin/python scripts/setup_models.py
HF_HUB_OFFLINE=1 .venv/bin/python -m voice_filtering \
  --host 127.0.0.1 --port 8765 --model models/faster-whisper-tiny.en
```

## Automated test results

- **96 tests pass** (M0: 66, M1 new: 30)
- `pip check`: No broken requirements
- Tests cover: frame validation, scaling, finite PCM, mode switching, epoch increment, reset, failure/no-fallback, metrics, lifecycle, service API, transcript, ASR scheduling

## What's implemented

- RNNoise wrapper: loads native lib via ctypes, 480-sample float32↔int16-amplitude conversion, process_frame(), timing metrics (avg/p95), graceful unavailability
- Pipeline: raw↔rnnoise mode switching with serialized epoch boundaries, no cross-mode ASR windows, resampler and processor reset on switch, RNNoise failure stops capture with STAGE_FAILED error
- UI: RNNoise radio button (enabled/disabled/failed based on stage), mode tags on transcript entries, RNNoise timing metrics display
- Replay: `scripts/replay_ab.py` runs same 48kHz WAV through both modes with identical ASR settings

## What's NOT implemented (out of scope for M1)

- Hush, Combined modes — remain unavailable
- Native load success — requires resolving the ctypes probe timeout
- Real noise suppression validation — requires H1 human testing
- ASR optimization

## H1 checkpoint commands

After native load is resolved, run the A/B replay:

```bash
# Record a 48kHz WAV with noise + speech (dev-recording mode)
HF_HUB_OFFLINE=1 .venv/bin/python -m voice_filtering \
  --host 127.0.0.1 --port 8765 --model models/faster-whisper-tiny.en --dev-recording

# Or use the replay script with an existing fixture:
.venv/bin/python scripts/replay_ab.py \
  --wav tests/fixtures/generated/noisy_speech.wav \
  --model models/faster-whisper-tiny.en \
  --report artifacts/replay/ab-report.json
```

## Known limitations

1. Native RNNoise dylib built but Python ctypes probe timed out — stage shows `failed` with reproducible error
2. RNNoise at 48kHz processes 480-sample (10ms) frames; no resampling before RNNoise, resampling happens after in the pipeline
3. Mode switch is pending until next frame boundary (capture loop checks `_pending_mode` per frame)
4. The FakeRNNoise in tests bypasses native library entirely — mocks cannot prove real denoising
5. H1 comparative acceptance requires real native load + same-input WAV replay evidence
