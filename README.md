# Voice Filtering M0 Baseline

Raw microphone → ASR → transcript UI. No filtering.

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

## What M0 Delivers

- Real microphone capture at 48 kHz mono
- Streaming resampling to 16 kHz for ASR
- Local Whisper-family ASR (faster-whisper-tiny.en, int8 CPU)
- Partial and final transcript events via SSE
- Start/Stop with device selection
- Copy and Clear transcript
- Visible unavailable states for RNNoise, Hush, Combined
- Input level meter from real audio
- Opt-in WAV recording with `--dev-recording`

## What M0 Does NOT Deliver

- RNNoise filtering (M1)
- Hush speaker suppression (M2-M3)
- Combined pipeline (M4)
- Live latency benchmarking (M5-M6)

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
docs/                    Architecture, plans, handoffs
models/                  Downloaded ASR model (gitignored)
```

## Known Limitations

- Forced 8-second utterance cuts can split words
- Energy gating is imperfect; silence hallucinations possible
- No VAD beyond RMS threshold
- macOS permission dialog may appear as Orca/Terminal/Python
- Model download required during setup (~50MB)
