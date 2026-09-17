# H0 — Baseline Checkpoint: Raw Mic + Live ASR

Status: **NOT RUN**
Depends on: M0 implementation and independent specification/code-quality review
Blocks: M1 and later human checkpoints; coordinator may independently authorize offline M2 preparation

## 1. Objective and Evidence Boundary

Establish the raw microphone → 48 kHz PCM → stateful 16 kHz conversion → local CPU ASR → live transcript baseline through actual human feedback. Architecture contract v1 and the M0 plan prescribe this behavior; this document does not assert that M0 exists or works. All product tests below remain **NOT RUN**. No microphone access, installs, model inference or application launch occurred during this reconciliation.

## 2. What H0 Validates

| Requirement | Scope | Status |
|-------------|-------|--------|
| FR-01 | Actual native microphone/device behavior | NOT RUN |
| FR-02 | 48 kHz mono source, one stateful 16 kHz ASR conversion | NOT RUN |
| FR-05 / FR-06 | Real partial/final ASR and responsive UI | NOT RUN |
| FR-07 / FR-10 | Raw available; RNNoise/Hush/Combined disabled with reasons (full bypass acceptance deferred) | NOT RUN |
| FR-08 | Permission, device/rate, missing-model and ASR errors | NOT RUN |
| FR-09 | Optional development raw/ASR-input recording only | NOT RUN |
| P-01 / P-06 | Measured live delay against ≤1.5 s target; CPU-only operation | NOT RUN |

## 3. Prescribed Launch — NOT YET VERIFIED

These exact commands are copied from [the M0 plan](../plans/m0-baseline.md#human-checkpoint-h0-coordinator-presents-after-review). They describe the required implemented interface, **not commands verified to work**. Run only in an implementation checkout containing the prescribed files and after the coordinator presents H0. The eventual implementation README/handoff must record actual setup evidence and any reviewed deviations.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --cache-dir .cache/pip -r requirements.lock.txt
.venv/bin/python -m pip install --cache-dir .cache/pip --no-deps --no-build-isolation -e .
.venv/bin/python scripts/setup_models.py
HF_HUB_OFFLINE=1 .venv/bin/python -m voice_filtering \
  --host 127.0.0.1 --port 8765 --model models/faster-whisper-tiny.en
```

Open `http://127.0.0.1:8765`. Recording is off by default. Capture is native sounddevice/CoreAudio, not browser getUserMedia: macOS microphone permission belongs to the launching **Orca, Terminal or Python** host/process shown by the OS. Startup, page load and device enumeration must not open the microphone; first capture access occurs only after **Start**. Enumeration alone does not establish permission. Select/change devices and Clear Transcript only while **idle**.

## 4. Human Test Script

| Step | Action | Expected result | Status |
|------|--------|-----------------|--------|
| 1 | Launch/open UI without Start; wait for ASR readiness | No microphone capture; RNNoise/Hush/Combined disabled with reasons; English raw baseline labeled | NOT RUN |
| 2 | While idle, select laptop microphone | Selected device shown; enumeration does not open it | NOT RUN |
| 3 | Press Start; grant native macOS permission if prompted | Permission goes to displayed launching host/process; selected device opens, status progresses Processing → Listening | NOT RUN |
| 4 | Speak: “This is the raw microphone baseline. My next interview starts at three thirty.” | Real input meter responds; partial text is replaced and then finalized without duplicates | NOT RUN |
| 5 | Pause between phrases and stay silent for ten seconds | Record any silence hallucinations, wrong/missing words and perceived delay; ≤1.5 s is the target, not a verified result | NOT RUN |
| 6 | Inspect device selector and Clear while active | Both unavailable during starting/listening/stopping; Clear API rejects non-idle state | NOT RUN |
| 7 | Press Stop | Capture releases before bounded ASR finalization; Processing → Idle; final transcript retained | NOT RUN |
| 8 | Copy and paste transcript into an editor; Clear while idle | Full visible text copied (or selectable-text fallback); Clear empties retained text | NOT RUN |
| 9 | Start again and say a different phrase, then Stop | New session; no stale partial or duplicate final; prior finals persist unless cleared | NOT RUN |
| 10 | While idle, choose another available compatible device and repeat | Actual selected device used; no silent device substitution | NOT RUN |
| 11 | Inspect available metrics | Queue depths, drop/late counters, rates and ASR timing recorded; absent filter timing is null/unavailable | NOT RUN |

Optional recording: restart the prescribed service command with `--dev-recording`, then explicitly opt in through the UI. Verify timestamped `artifacts/captures/<UTC>-<session-id>/raw.wav` (48 kHz), `asr-input.wav` (16 kHz) and `metadata.json`; recording stops at 60 seconds while capture/ASR may continue. No `hush.wav` or `combined.wav` is expected in M0, and no application audio playback/monitoring loop is prescribed. This optional product check is **NOT RUN** and is not required for the basic human H0 experience.

### Error Scenarios

| Step | Action | Expected result | Status |
|------|--------|-----------------|--------|
| E1 | Deny native permission on Start | Confirmed denial: `MIC_PERMISSION_DENIED`; otherwise `AUDIO_DEVICE_ERROR` with native detail and macOS Settings → Privacy & Security → Microphone guidance; never infer permission from enumeration | NOT RUN |
| E2 | Disconnect selected microphone during capture | Explicit device failure, resource cleanup and retained final text | NOT RUN |
| E3 | Select a device incompatible with 48 kHz mono float32 | `UNSUPPORTED_SAMPLE_RATE` naming device/format; no silent fallback | NOT RUN |
| E4 | Launch with missing ASR model | UI explains `MODEL_MISSING`; Start disabled; no fabricated transcript | NOT RUN |
| E5 | Attempt a non-Raw mode | Disabled UI option and backend `STAGE_UNAVAILABLE`; no simulated filtering | NOT RUN |

## 5. Automated and Real-Model Evidence (All NOT RUN)

| Test | What it checks and cannot prove | Status |
|------|--------------------------------|--------|
| Deterministic source/resampler | Finite PCM, exact valid duration, source timeline, stateful flush, bounded drops and gap reset; no physical device evidence | NOT RUN |
| Fake transcriber/controller | Partial replacement, final once, stale-result rejection, bounded queues under slow inference and Stop/restart; no real ASR accuracy or latency evidence | NOT RUN |
| API/events/UI plumbing | Idle-only Clear, unavailable modes/model, structured errors, reconnect snapshots, retained finals and duplicate Start rejection; injected errors do not prove native permission handling | NOT RUN |
| Real pinned-model JFK WAV smoke | Actual CPU load/decode and consumed segments contain normalized “ask not” and “country”; no microphone, live latency or suppression evidence | NOT RUN |

The separate prescribed verification commands below are **NOT YET VERIFIED** and were **NOT RUN** in this task:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m pip check
.venv/bin/python scripts/setup_models.py
.venv/bin/python scripts/fetch_test_audio.py
HF_HUB_OFFLINE=1 .venv/bin/python scripts/smoke_asr.py \
  --wav tests/fixtures/generated/jfk.wav \
  --model models/faster-whisper-tiny.en \
  --report artifacts/m0/asr-smoke.json
```

## 6. Pass Criteria and Limitations

Actual human feedback must establish selected-device capture after Start, live transcription, honest disabled filter modes/errors, clean Stop/restart, retained text, Copy and idle-only Clear. Record latency against the PRD ≤1.5 s target and report any miss to the coordinator; do not convert an unmeasured target into a pass. Zero dropped frames is aspirational: the PRD defines no binding numeric drop threshold, but requires instrumentation and later stability evidence.

Raw includes no application filtering, though hardware/OS microphone processing may still apply; record the selected OS microphone mode. Raw is resampled once before ASR. ASR uses repeated bounded-window decoding, not native streaming Whisper; errors and delays remain empirical. H0 cannot establish filtering, the full four-mode contract, or T1–T6 acceptance. Background/noise transcription errors are baseline observations, not proof that later filters work.

## 7. Feedback Record

Record date, tester, host/device, implementation commit, model revision, OS microphone mode, permission outcome, actual transcript/latency notes, errors, Stop/restart, Copy/Clear and requested changes. Only actual human feedback can fill this record and release H0.

| Date | Tester | Evidence / feedback | Requested action |
|------|--------|---------------------|------------------|
| — | — | — | — |
