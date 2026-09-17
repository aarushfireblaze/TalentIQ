# M0 Baseline Handoff

## Status: Ready for H0

## Setup Commands

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --cache-dir .cache/pip -r requirements.lock.txt
.venv/bin/python -m pip install --cache-dir .cache/pip --no-deps --no-build-isolation -e .
.venv/bin/python scripts/setup_models.py
HF_HUB_OFFLINE=1 .venv/bin/python -m voice_filtering \
  --host 127.0.0.1 --port 8765 --model models/faster-whisper-tiny.en
```

## Automated Test Results

- 66 tests pass (test_audio: 8, test_asr: 21, test_pipeline: 20, test_service: 17)
- pip check: No broken requirements
- ASR model loads and decodes successfully (faster-whisper-tiny.en, int8 CPU)
- Synthetic WAV decoded in 0.67s, produces text output

## Real ASR Smoke

- Model: Systran/faster-whisper-tiny.en @ 0d3d19a32d3338f10357c0889762bd8d64bbdeba
- Compute type: int8, CPU threads: 4
- Model download: ~50MB, stored in models/
- JFK test audio unavailable (external CDN blocked); synthetic tone verified model load+decode

## UI Inspection

- HTML/CSS/JS served at http://127.0.0.1:8765
- Status display: Idle/Listening/Processing/Error
- Device selector with real PortAudio enumeration
- Input level meter from real audio RMS
- Four mode labels with RNNoise/Hush/Combined visibly unavailable
- Partial/final transcript with session grouping
- Copy (clipboard API + fallback) and Clear buttons
- Permission notice shown when idle

## Remaining H0 Items

- [ ] Human selects laptop microphone
- [ ] Human grants macOS permission
- [ ] Human speaks "This is the raw microphone baseline. My next interview starts at three thirty."
- [ ] Human observes level meter and transcript
- [ ] Human presses Stop; verifies device release, text persistence, Copy/Clear
- [ ] Human restarts and speaks different phrase
- [ ] Human optionally tests --dev-recording mode

## Filter Unavailability

RNNoise, Hush, and Combined modes are visibly labeled "Not implemented in M0" in the UI and return STAGE_UNAVAILABLE on mode switch attempts.

## H0 Feedback Section

_Awaiting human feedback. Only actual human feedback can fill this section._

- Date:
- Host/Device:
- Commit:
- Model revision:
- Permission outcome:
- Actual transcript:
- Latency notes:
- Stop/restart behavior:
- Copy/Clear behavior:
- Errors:
- Requested changes:
