# Voice Filtering MVP

Local microphone → optional RNNoise → ASR → transcript UI. Hush and Combined
remain future milestones. H1 RNNoise user retest is pending. See
[`progress.md`](progress.md) for current worktrees and task assignments.

## Quick Start

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --cache-dir .cache/pip -r requirements.lock.txt
.venv/bin/python -m pip install --cache-dir .cache/pip --no-deps --no-build-isolation -e .
.venv/bin/python scripts/setup_models.py
HF_HUB_OFFLINE=1 .venv/bin/python -m voice_filtering \
  --host 127.0.0.1 --port 8765 --model models/faster-whisper-tiny.en
```

Open http://127.0.0.1:8765 in browser.

RNNoise requires a native library built from `xiph/rnnoise` commit
`70f1d256acd4b34a572f999a05c87bf00b67730d`. Place
`librnnoise.0.dylib` in the project's `lib/` directory, or set
`RNNOISE_LIB_PATH` to its absolute path before launch. The library is a local
build artifact and is not included in this repository. Check stage status in
the UI; missing or failed native load must show an unavailable/error state.

## Current features

- Real microphone capture at 48 kHz mono
- Streaming resampling to 16 kHz for ASR
- Local Whisper-family ASR (faster-whisper-tiny.en, int8 CPU)
- Partial and final transcript events via SSE
- Start/Stop with device selection
- Copy and Clear transcript
- RNNoise-only mode when its native library loads; explicit unavailable status otherwise
- Visible unavailable states for Hush and Combined
- Input level meter from real audio
- Opt-in WAV recording with `--dev-recording`

## Pending milestones

- H1 user retest and controlled Raw/RNNoise acoustic comparison
- Hush speaker suppression (M2–M3)
- Combined pipeline (M4)
- Four-mode evaluation and live stability measurement (M5–M6)

## Testing

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m pip check
```

## ASR Smoke Test

```bash
.venv/bin/python scripts/setup_models.py
.venv/bin/python scripts/fetch_test_audio.py
HF_HUB_OFFLINE=1 .venv/bin/python scripts/smoke_asr.py \
  --wav tests/fixtures/generated/jfk.wav \
  --model models/faster-whisper-tiny.en \
  --report artifacts/m0/asr-smoke.json
```

## Project Structure

```
src/voice_filtering/     Application code
apps/ui/                 Static HTML/CSS/JS frontend
scripts/                 Model setup and smoke tests
tests/                   Automated tests
docs/requirements/       Approved PRD and searchable text copy
docs/handoffs/           Saved H1 draft patches; not accepted code
progress.md              Worktree tasks, checkpoints, current state
models/                  Downloaded ASR model (gitignored)
```

## Known Limitations

- Forced 8-second utterance cuts can split words
- Energy gating is imperfect; silence hallucinations possible
- No VAD beyond RMS threshold
- macOS permission dialog may appear as Orca/Terminal/Python
- Model download required during setup (~50MB)
