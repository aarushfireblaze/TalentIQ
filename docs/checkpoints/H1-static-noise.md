# H1 — Static Noise Checkpoint: RNNoise A/B

Status: **NOT RUN**
Depends on: H0 pass + M1 completion
Blocks: H2, H3

---

## 1. Objective

Validate RNNoise noise suppression against the raw baseline. Compare transcript quality and audio quality in a controlled static-noise scenario (fan, HVAC, keyboard). Establish the A/B comparison methodology for later checkpoints.

## 2. What H1 Validates

| Requirement | Validated? |
|-------------|------------|
| FR-03 — RNNoise stage | NOT RUN |
| FR-07 — Bypass modes (Raw vs RNNoise) | NOT RUN |
| FR-09 — Local recording for QA | NOT RUN |
| FR-10 — No silent fallback | NOT RUN |
| P-03 — Background noise reduction | NOT RUN |
| P-05 — Primary speech retention | NOT RUN |
| P-07 — Mode switching without restart | NOT RUN |

## 3. Test Inputs

| Input | Description |
|-------|-------------|
| Primary speaker | Person at normal laptop mic distance |
| Noise source | Fan or HVAC positioned 1–2 feet from laptop, running at moderate speed |
| Keyboard | Typing on laptop keyboard during speech |
| Reference passage | "The quick brown fox jumps over the lazy dog. She sells seashells by the seashore. The rain in Spain stays mainly in the plain." (30 seconds) |

## 4. Fair Same-Clip Comparison Method

To ensure a fair A/B comparison:

1. **Record once in Raw mode** with noise + speech for 60 seconds. Save as `raw_t2.wav`.
2. **Replay the same WAV** through RNNoise-only mode. Save as `rnnoise_t2.wav`.
3. Transcribe both recordings with the same ASR model.
4. Compare transcript word counts, background word intrusions, and subjective clarity.

**Critical:** Replaying the same recorded WAV is the only way to ensure identical input. Live re-speaking the passage is NOT the same input and is not a fair comparison. When live replay is not feasible, record two back-to-back sessions in identical conditions (same speaker, same noise level, same position) within 60 seconds of each other and note this as a limitation.

## 5. Human Test Script

### Launch

**Note:** Exact launch commands depend on architecture decisions. Update after architecture handoff.

1. Launch the application with RNNoise enabled.
2. Confirm RNNoise model loaded (no error in status).

### Test Steps

| Step | Action | Expected Result | Status |
|------|--------|----------------|--------|
| 1 | Position fan/HVAC near laptop at moderate level | Noise is audible in the room | NOT RUN |
| 2 | Start recording in Raw mode | Transcript includes noise artifacts (keyboard clatter, fan hum transcription attempts) | NOT RUN |
| 3 | Speak the reference passage for 30 seconds | Primary speech is transcribed but noise degrades quality | NOT RUN |
| 4 | Switch to RNNoise mode (live, without restart) | Mode indicator changes; audio processing continues | NOT RUN |
| 5 | Speak the same reference passage for 30 seconds | Transcript is cleaner; fan/keyboard noise is reduced or absent | NOT RUN |
| 6 | Switch back to Raw mode | Mode indicator changes; noise returns to transcript | NOT RUN |
| 7 | Stop recording | Final transcript visible | NOT RUN |
| 8 | Listen to saved WAVs (if A/B recording is enabled) | RNNoise.wav has less fan/keyboard noise than raw.wav; primary voice is still present | NOT RUN |
| 9 | Check developer panel for RNNoise timing metrics | Per-frame processing time and avg/p95 are displayed | NOT RUN |

### Error Scenarios

| Step | Action | Expected Result | Status |
|------|--------|----------------|--------|
| E1 | Start with RNNoise model file missing/renamed | Error message: "RNNoise model not available" (FR-10) | NOT RUN |
| E2 | Start with RNNoise model file corrupted | Error message indicating model load failure | NOT RUN |

## 6. Automated Tests

| Test | What it checks | Status |
|------|---------------|--------|
| Unit: RNNoise wrapper processes frames | Mock PCM frame in → denoised frame out (non-zero output) | NOT RUN |
| Unit: RNNoise wrapper handles 48 kHz input | Input at 48 kHz produces valid output (native rate) | NOT RUN |
| Integration: Raw → RNNoise path | Pipeline in RNNoise-only mode produces output frames | NOT RUN |
| Unit: Mode switch Raw↔RNNoise | PipelineController.switch_mode toggles RNNoise without crash | NOT RUN |
| Unit: RNNoise model missing error | Missing model file triggers FR-10 error event | NOT RUN |

## 7. Latency / Timing Collection

| Metric | How to collect | Status |
|--------|---------------|--------|
| RNNoise per-frame processing time (avg) | Instrument wrapper, log mean | NOT RUN |
| RNNoise per-frame processing time (p95) | Instrument wrapper, log 95th percentile | NOT RUN |
| End-to-end latency (Raw mode) | Timestamp capture → transcript display | NOT RUN |
| End-to-end latency (RNNoise mode) | Timestamp capture → transcript display | NOT RUN |
| Dropped frames during mode switch | Count frames lost during live mode switch | NOT RUN |

## 8. Pass Criteria

- RNNoise-only mode produces a cleaner transcript than Raw in static-noise conditions.
- Mode switching works without restart or crash.
- RNNoise.wav shows audible noise reduction compared to raw.wav (if A/B recording available).
- Primary speech remains intelligible in RNNoise mode — no word erasure.
- Error messages appear when RNNoise model is unavailable.
- Developer panel shows RNNoise timing metrics.

## 9. Known Limitations at This Stage

- RNNoise is designed for non-speech noise (fans, HVAC, keyboard). It will **not** suppress competing human speech — that is Hush's job (H2).
- If the test environment has both fan noise AND competing speech, RNNoise alone will not address the speech interference.
- RNNoise operates at 48 kHz natively; a resampling boundary to 16 kHz for Hush is expected at the M4 stage. At H1, only RNNoise is active, so resampling is not yet tested.

## 10. Feedback Record

| Date | Tester | Feedback | Action Taken |
|------|--------|----------|--------------|
| — | — | — | — |
