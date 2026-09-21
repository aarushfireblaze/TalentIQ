# Voice Filtering MVP

Local microphone processing with one fixed path:

```text
48 kHz microphone → RNNoise → one 16 kHz conversion → Hush → local ASR → transcript UI
```

The app has no Raw, RNNoise-only, or Hush-only operation. If RNNoise or Hush
cannot load, startup reports that stage error and does not process unfiltered
audio.

## Quick start

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --cache-dir .cache/pip -r requirements.lock.txt
.venv/bin/python -m pip install --cache-dir .cache/pip --no-deps --no-build-isolation -e .
.venv/bin/python scripts/setup_models.py
HF_HUB_OFFLINE=1 .venv/bin/python -m voice_filtering \
  --host 127.0.0.1 --port 8765 --model models/faster-whisper-tiny.en
```

Open `http://127.0.0.1:8765`. Select microphone, optionally enable short WAV
captures for QA, then press Start.

RNNoise needs a local build of `xiph/rnnoise` commit
`70f1d256acd4b34a572f999a05c87bf00b67730d`. Put `librnnoise.0.dylib` in
`lib/`, or set `RNNOISE_LIB_PATH` before launch. Hush assets must be present
under `models/hush/`. Stage status in UI identifies missing or failed assets.

## Included features

- 48 kHz mono microphone capture and bounded pipeline queues
- Fixed RNNoise, Hush, and local Whisper-family ASR pipeline
- Partial and final transcript events over SSE
- Device selector, Start/Stop, input meter, copy, clear, and explicit errors
- Opt-in short WAV capture with `--dev-recording`
- RNNoise and Hush timing metrics

## Testing

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m pip check
```

## Known limits

- Hush assumes intended speaker is nearest and loudest. A loud or close
  competing speaker can still appear in transcript.
- Forced 8-second utterance cuts can split words.
- Energy gating can produce silence hallucinations.
- macOS may attribute microphone permission to Terminal or Python.
