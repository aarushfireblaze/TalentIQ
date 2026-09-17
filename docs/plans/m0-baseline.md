# Voice Filtering M0 Baseline Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` for this assigned milestone. Do not spawn workers. The approved PRD authorizes implementation; do not ask for another design approval. The coordinator dispatches the implementer in a child worktree and owns review and human checkpoint H0.

**Goal:** Deliver real local microphone → raw level/optional WAV → local Whisper-family ASR → transcript UI, with honest unavailable-filter states.

**Architecture:** Implement [contract v1](../architecture.md) using a single Python local service, native sounddevice capture and a no-build static frontend. Capture, DSP, ASR scheduling/inference and optional recording have independent bounded queues. Only Raw is functional in M0.

**Tech Stack:** Python 3.13, NumPy 2.5.3, sounddevice 0.5.6, soxr 1.1.0, faster-whisper 1.2.1, CTranslate2 4.8.2, Starlette 1.6.0 and base Uvicorn 0.53.0. Pin model revisions and resolve/freeze transitives inside the project.

**Spec:** `docs/requirements/Voice_Filtering_System_PRD.txt`; `docs/architecture.md`; `progress.md`. Read all three before editing. Coordinator must commit PRD/progress into the main worktree before creating the implementation child; the architecture commit alone does not supply those prerequisites.

## Global constraints and ownership

- M0 is raw baseline only. Do not implement RNNoise/Hush, advertise enabled filter modes, generate fake transcript text in the app, or claim M1–M7 complete.
- Use local CPU ASR and no model/network downloads during service startup. Setup may download exact pinned artifacts. Installs, models, cache, binaries and recordings remain in this project.
- Capture mono 48 kHz float32, resample once to 16 kHz using persistent state. PortAudio callback never waits on inference/UI/disk.
- No worker microphone recording. Human performs H0. No pushes or changes to `progress.md`, requirements source documents, architecture contract or another worker's test plans.
- No application audio recording unless human explicitly enables development recording. Unit tests use synthetic samples, and the real ASR smoke uses an upstream prerecorded fixture.
- UI shows Idle / Listening / Processing / Error, device selection, meter, four mode labels, partial/final transcript, Stop, Copy and Clear. Non-Raw modes disabled with reasons. Device change and Clear are idle-only in M0.
- Independent review must issue separate specification and code/test-quality verdicts before H0. H0 feedback is required before M1 dependent work; automated passes cannot substitute for it.

The M0 implementer owns **only** these paths (all newly created):

```text
.gitignore
README.md
pyproject.toml
requirements.in
requirements.lock.txt
apps/ui/index.html
apps/ui/styles.css
apps/ui/app.js
src/voice_filtering/__init__.py
src/voice_filtering/__main__.py
src/voice_filtering/contracts.py
src/voice_filtering/service.py
src/voice_filtering/events.py
src/voice_filtering/audio/__init__.py
src/voice_filtering/audio/capture.py
src/voice_filtering/audio/resample.py
src/voice_filtering/audio/recording.py
src/voice_filtering/asr/__init__.py
src/voice_filtering/asr/whisper.py
src/voice_filtering/pipeline/__init__.py
src/voice_filtering/pipeline/controller.py
scripts/setup_models.py
scripts/smoke_asr.py
scripts/fetch_test_audio.py
tests/__init__.py
tests/test_audio.py
tests/test_asr.py
tests/test_pipeline.py
tests/test_service.py
tests/fakes.py
docs/handoffs/m0-baseline.md
```

Generated/gitignored project-local directories: `.venv/`, `.cache/`, `models/`, `artifacts/`, `tests/fixtures/generated/`. Do not commit these or audio/model bytes. Other paths require coordinator ownership assignment. Future wrappers belong in separately assigned paths and must conform to v1 contracts.

## Task 1: contracts, environment and deterministic audio foundation

**Files:** packaging/ignore files; `contracts.py`; `audio/capture.py`; `audio/resample.py`; package `__init__.py` files; `tests/fakes.py`, `tests/test_audio.py`.

**Interfaces:** Implement `AudioFrame`, `PipelineError`, `AudioSource` and processor/transcriber/controller protocols verbatim from architecture. `CaptureSource.start(device_id,session_id)` exposes a bounded 100-frame ring, nonblocking callback insertion, `read_frame(timeout_s)`, idempotent stop and device enumeration. `StreamingResampler.push(frame) -> list[AudioFrame]`, `finish() -> list[AudioFrame]`, `reset()` preserve source timeline and account for variable soxr output.

- [ ] Add failing `unittest` cases for non-finite/wrong-shape PCM, known 48k/16k mapping, ring overflow and idempotent resource cleanup. Use synthetic arrays only; importing a source must not open a microphone.
- [ ] Run `python3 -m unittest tests.test_audio -v` and record the expected missing-implementation failure.
- [ ] Add project packaging with a `src` layout and the required modules. Use these direct requirements in `requirements.in`:

```text
numpy==2.5.3
sounddevice==0.5.6
soxr==1.1.0
faster-whisper==1.2.1
ctranslate2==4.8.2
starlette==1.6.0
uvicorn==0.53.0
huggingface-hub==1.32.0
onnxruntime==1.30.0
av==18.1.0
tokenizers==0.23.2
setuptools==80.9.0
```

- [ ] Create `.venv` with `python3 -m venv .venv`. Install with `.venv/bin/python -m pip install --cache-dir .cache/pip -r requirements.in`, then `.venv/bin/python -m pip check`. Freeze resolved distributions using `.venv/bin/python -m pip freeze > requirements.lock.txt` **before** editable project installation, then `.venv/bin/python -m pip install --cache-dir .cache/pip --no-deps --no-build-isolation -e .` (declare `setuptools==80.9.0` and backend `setuptools.build_meta` in pyproject.toml; this pin is included above). A clean setup must work from this lock; do not leave an editable absolute child-worktree path in it.
- [ ] Implement callback copying/ring bounds, 48 kHz preflight and streaming resampling. Handle short final frames through `valid_samples`; do not discard real tail samples. `start`/`stop` exceptions must release partially opened streams.
- [ ] Run `.venv/bin/python -m unittest tests.test_audio -v`. Required observations: one second of source audio yields exactly 16,000 valid output samples after flush; chunked vs whole-stream conversion agrees to a stated numerical tolerance after delay alignment; 1,000 inputs leave at most 100 frames; reported dropped source duration is exact and gap metadata survives conversion. Inject unsupported device/rate and observe structured errors.

Minimal behavioral test shape (adapt constructors to the concrete class without weakening assertions):

```python
def test_resampler_preserves_duration_and_source_clock(self):
    frames = make_frames(seconds=1, rate=48000)  # deterministic sine; no device
    outputs = []
    for frame in frames:
        outputs.extend(self.resampler.push(frame))
    outputs.extend(self.resampler.finish())
    self.assertEqual(sum(f.valid_samples for f in outputs), 16000)
    self.assertTrue(all(f.sample_rate == 16000 for f in outputs))
    self.assertEqual([f.sample_start for f in outputs], list(range(0, 48000, 480)))
```

The test's `make_frames` helper belongs in `tests/fakes.py`; it emits the contract's 480-sample frames with deterministic session origin and valid sample counts.

## Task 2: actual ASR adapter, bounded scheduler and controller

**Files:** `asr/whisper.py`, `pipeline/controller.py`, `audio/recording.py`, `scripts/setup_models.py`, `scripts/smoke_asr.py`, `scripts/fetch_test_audio.py`, `tests/test_asr.py`, `tests/test_pipeline.py`.

**Interfaces:** Implement `Transcriber` and `PipelineController` from architecture. Inject source, transcriber and monotonic clock in controller constructors for tests; runtime uses real adapters. ASR scheduler emits versioned `TranscriptEvent` payloads via the event callback, owns the 8-second utterance/pre-roll buffer, and serializes real inference in its separate worker. Define `load_model(path)` and `decode(pcm16k)` internals; `decode` must consume the upstream generator.

- [ ] Write failing tests that block the fake decoder while feeding 1,000 frames, checking source/DSP progress, ASR ingress cap, latest-partial coalescing, final-queue overload, and late-result rejection after Stop/restart. Test that a partial revision replaces text and final emits once. Test stop before any speech and concurrent repeated Start/Stop calls.
- [ ] Run `.venv/bin/python -m unittest tests.test_asr tests.test_pipeline -v`; preserve the initial failure, then implement the architecture's exact capacities, gate thresholds, worker ownership and error paths.
- [ ] Implement setup-only snapshot download of `Systran/faster-whisper-tiny.en` at revision `0d3d19a32d3338f10357c0889762bd8d64bbdeba` into `models/faster-whisper-tiny.en`, with `HF_HOME` under `.cache/huggingface`. Download only model.bin/config.json/tokenizer.json/vocabulary.txt/README.md; hash downloaded files into `models/manifest.json`. Never request `main` or an unpinned model alias at runtime.
- [ ] Implement `scripts/fetch_test_audio.py` to fetch `https://raw.githubusercontent.com/ggml-org/whisper.cpp/da54572229bcf64ba367d96c7ef15770376c4280/samples/jfk.wav` into `tests/fixtures/generated/jfk.wav`. Validate the WAV header (mono, 16 kHz, PCM16) and store URL, commit and file SHA256 beside it; preserve provenance/license references. Fail on HTML, truncated WAV or rate mismatch. This is existing public test audio, not permission to capture a microphone.
- [ ] Implement actual CPU model construction/decode exactly as specified in architecture, including visible model-missing/load/inference errors. Make `scripts/smoke_asr.py --wav PATH --model PATH --report PATH` invoke that adapter with networking disabled, output JSON containing model revision, compute type, audio duration, decode duration, resulting text and pass/fail. Require nonempty text containing normalized `ask not` and `country` for this fixture; do not assert exact punctuation or benchmark performance from one decode.
- [ ] Implement opt-in raw/asr-input WAV writer with 2-second bound, 60-second recording cap, sample-rate-correct PCM16 headers and metadata. Overflow must mark incomplete output; a file-write error must not hang capture. Tests write synthetic audio to a temporary project directory only.
- [ ] Run automated unit tests, then explicitly separate the real smoke:

```bash
.venv/bin/python scripts/setup_models.py
.venv/bin/python scripts/fetch_test_audio.py
HF_HUB_OFFLINE=1 .venv/bin/python scripts/smoke_asr.py \
  --wav tests/fixtures/generated/jfk.wav \
  --model models/faster-whisper-tiny.en \
  --report artifacts/m0/asr-smoke.json
.venv/bin/python -m unittest tests.test_asr tests.test_pipeline -v
```

Failure to download/load/decode is a reported blocker, not a reason to substitute stub text. Record actual resolved versions and host details. Python's system TLS trust failed during architecture research; curl using system trust worked. If setup hits the same issue, diagnose the trust store and configure a valid CA bundle locally; do not disable certificate verification or mutate global Python/system certificates.

## Task 3: local API, observable UI and lifecycle

**Files:** `service.py`, `events.py`, `__main__.py`; all three `apps/ui/` files; `tests/test_service.py`; `README.md`, `docs/handoffs/m0-baseline.md`.

**Interfaces:** Implement every architecture endpoint/envelope/event and snapshot, using `PipelineController`. Event hub is thread-safe, transfers events to ASGI with `loop.call_soon_threadsafe` or equivalent, and enforces bounded/coalesced per-client delivery. No HTTP handler runs blocking model work. Start CLI is `python -m voice_filtering --host 127.0.0.1 --port 8765 --model models/faster-whisper-tiny.en [--dev-recording]`.

- [ ] Write failing API tests using an injected fake controller or an ephemeral loopback server, without acquiring a device. Assert missing-model status, invalid device/rate, unavailable modes, duplicate Start rejection, idempotent Stop, idle-only Clear, SSE reconnect snapshot and foreign-origin rejection. Native dependencies must not be mocked in the separate ASR smoke.
- [ ] Implement SSE/HTTP/static service and startup background model loading. Restrict CLI host to loopback for M0. Serving a missing-model status must still allow the UI to load and explain setup.
- [ ] Implement UI with textContent rendering (transcript is not HTML), one partial row per segment, stable final rows/session groups keyed by `(session_id,segment_id)`, visible permission instructions, working disabled states, Copy with selectable-text fallback, and Clear. Display English model/baseline status. Snapshot historical finals carry their original session_id and remain valid; reject stale arriving inference rather than rejecting retained snapshot history. No fake animation may represent actual audio activity; meter comes from input samples.
- [ ] On network disconnect disable Start, retain text and say Disconnected; reconnect installs authoritative snapshot. Last subscriber leaving triggers five-second capture stop grace period. Page teardown releases SSE. Confirm Stop releases device before waiting for ASR flush.
- [ ] Run `.venv/bin/python -m unittest discover -s tests -v` and `.venv/bin/python -m pip check`. Manually inspect the static page without pressing Start; record whether browser inspection was performed or unavailable. No screenshot/testing claim without actual observation.
- [ ] Write README and handoff with exact install/setup/run commands, expected URL, candidate versus validated version differences, automated test results, real ASR smoke evidence path, UI inspection evidence, remaining H0 items and filter unavailability. `docs/handoffs/m0-baseline.md` also holds a blank H0 feedback section; only actual human feedback can fill it.
- [ ] Commit only owned paths after checking `git diff --check` and the staged path list. Deliver the commit, exact commands/results and limitations to the coordinator. Do not edit `progress.md` or begin M1.

## Observable acceptance matrix

| Evidence | Pass observation | What it cannot establish |
|---|---|---|
| Audio unit tests | Correct finite PCM, duration/timestamps, stateful conversion and bounded drops | Physical microphone and real filter quality |
| Concurrency/lifecycle tests | Slow inference/UI never blocks capture; Stop/restart rejects stale results; no unbounded queues | CPU latency on live speech |
| API/UI tests | Honest unavailable modes/model errors; transcript replace/final behavior; snapshot reconnect | Real ASR correctness |
| Pinned-model JFK smoke | Real CTranslate2 loads locally, decodes known speech, records output/timing/revision | Live latency, microphone permission, competing-speaker suppression |
| H0 by human | Correct device/permission, level, live transcription, Stop/restart, Copy/Clear experience | Completion of filtering milestones or T1–T6 |

M0 should report partial delay measurements without relaxing the PRD's ≤1.5 s goal. If slower, deliver the actual measurement and constraint; coordinator decides follow-up. A synthetic 10-minute queue test is useful boundedness evidence, but does not satisfy the final live ten-minute test.

## Human checkpoint H0 (coordinator presents after review)

These commands are the required implemented interface, not commands that worked during the architecture task. From the implementation checkout containing the committed prerequisites:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --cache-dir .cache/pip -r requirements.lock.txt
.venv/bin/python -m pip install --cache-dir .cache/pip --no-deps --no-build-isolation -e .
.venv/bin/python scripts/setup_models.py
HF_HUB_OFFLINE=1 .venv/bin/python -m voice_filtering \
  --host 127.0.0.1 --port 8765 --model models/faster-whisper-tiny.en
```

Open `http://127.0.0.1:8765` in the laptop browser. Recording is off. The human then:

1. Waits for ASR ready and verifies RNNoise/Hush/Combined are disabled with reasons.
2. Selects the laptop microphone and presses Start. Grants the macOS permission to the displayed launching app/process; if refused, confirms an actionable error and retries after changing Settings.
3. Says: “This is the raw microphone baseline. My next interview starts at three thirty.” Watches the level meter and partial/final transcript; notes perceived delay, wrong/missing words and any silence hallucinations. Waits briefly between phrases.
4. Presses Stop; verifies the microphone indicator releases, final text persists, Copy works, and Clear works while idle.
5. Starts again and speaks a different phrase. Checks no old partial appears and no duplicate final appears. Stops before changing device; if another device exists, repeats with that selection.
6. Optionally tests a short saved WAV by restarting with `--dev-recording` and explicitly enabling recording in the UI. No opt-in is required to complete the basic H0 experience. Files must show correct raw/ASR rates and no invented filtered outputs.

Coordinator records date, host/device, commit, model revision, permission outcome, actual transcript/latency notes, Stop/restart and Copy/Clear behavior, errors, and the human's requested changes in the M0 handoff/progress ledger. H0 remains pending until that feedback is received. M1 waits; offline M2 preparation may be independently authorized by the coordinator.
