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

## Milestones

- M0–M6: Completed and integrated.
- M7 (Final Acceptance): Setup verified, evaluator run, T1–T6 results consolidated.

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

- **Loud Interferer (T6):** If a background person is louder or much closer than the primary speaker, Hush may not preserve the intended identity. This is a known architectural limit.
- **Controlled T3/T4:** Controlled comparative testing for T3 (Competing speaker) and T4 (Mixed noise) were NOT RUN. Primary word mix-ups and loud competing speech remain known limits.
- **Combined Mode Degradation:** Heavy static noise can cause the Combined mode (RNNoise + Hush) to drop primary speech words.
- Forced 8-second utterance cuts can split words.
- Energy gating is imperfect; silence hallucinations possible.
- No VAD beyond RMS threshold.
- macOS permission dialog may appear as Orca/Terminal/Python.
- Model download required during setup (~50MB).

## T1–T6 Evaluation Results

- **T1 (Quiet room):** Combined mode preserves primary speech intelligibility but introduces minor substitutions. (Raw: 100% retention; Combined: minor word differences).
- **T2 (Static room noise):** RNNoise and Combined successfully filter noise. However, heavy synthetic noise degrades the Combined mode transcript.
- **T3 (Competing speaker):** NOT RUN. Controlled comparison unavailable.
- **T4 (Mixed noise):** NOT RUN. Controlled comparison unavailable.
- **T5 (10-minute Stress Test):** Completed successfully. No crashes, no runaway memory (Peak ~512 MB), and 0 dropped frames. See `artifacts/m6_live_run.txt` for live metrics.
- **T6 (Loud interferer):** Known failure mode (Hush prioritizes loudest/closest speaker).

## Definition of Done Verification

- [x] Clean setup instructions working (verified).
- [x] Mic capture, RNNoise, Hush, ASR work continuously.
- [x] Four modes available and switchable.
- [x] Static noise reduction verified (T2).
- [x] 10-minute stress test completes without crash (T5).
- [x] Failure states surfaced explicitly.
- [x] Benchmarks, limitations, models, and licenses documented.

## Model and License Notices

- **ASR:** [Systran/faster-whisper-tiny.en](https://huggingface.co/Systran/faster-whisper-tiny.en) (MIT License / Whisper is MIT).
- **RNNoise:** [xiph/rnnoise](https://github.com/xiph/rnnoise) (BSD 3-Clause).
- **Hush:** [weya-ai/hush](https://huggingface.co/weya-ai/hush) (Check specific model license, typical open weights).
