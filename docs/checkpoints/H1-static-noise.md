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

To ensure a fair A/B comparison, explicitly opt in to development recording (off by default) or use a documented recorded fixture. Mode replay must use the shared 48 kHz source and common ASR settings:

1. **Record once in Raw mode** with noise + speech for 60 seconds. Save as `raw_t2.wav`.
2. **Replay the same WAV** through RNNoise-only mode. Save as `rnnoise_t2.wav`.
3. Transcribe both recordings with the same ASR model.
4. Compare aligned audio noise-only intervals, transcript errors and primary retention separately using [the shared scoring protocol](../acceptance.md#shared-comparison-and-scoring-protocol). T2 has no background speech, so background intrusion rate is N/A. Record fixture hash, ASR settings, delays, resets and drops.

**Critical:** Replaying the same recorded WAV is the only way to ensure identical input. Live re-speaking the passage is NOT the same input and is not a fair comparison. Back-to-back live takes are exploratory only and cannot replace same-recorded-input comparative acceptance. If replay is unavailable, comparative acceptance remains **NOT RUN**; minimal replay support must be supplied before H1 even though the full evaluator is M5.

## 5. Human Test Script

### Launch

**NOT YET VERIFIED:** Architecture contract v1 defines the local native service; [H0](H0-baseline.md) contains prescribed M0 commands. Filtering setup/replay commands require the M1 implementation handoff; M0 commands alone do not enable RNNoise.

1. Launch the application with RNNoise enabled.
2. Confirm RNNoise model loaded (no error in status).

### Live Lifecycle / Exploratory Steps

These steps check switching and user experience. Fresh live takes do not establish comparative filtering quality; complete §4 with the same recorded input and record its evidence separately before passing H1.

| Step | Action | Expected Result | Status |
|------|--------|----------------|--------|
| 1 | Position fan/HVAC near laptop at moderate level | Noise is audible in the room | NOT RUN |
| 2 | Start capture in Raw mode | Status Listening; record actual baseline errors without assuming noise must become words | NOT RUN |
| 3 | Speak the reference passage for 30 seconds | Record primary transcript and observed noise impact | NOT RUN |
| 4 | Switch to RNNoise mode (live, without restart) | Mode indicator changes; audio processing continues | NOT RUN |
| 5 | Speak the same reference passage for 30 seconds | Record exploratory observations; comparative improvement is assessed in §4 | NOT RUN |
| 6 | Switch back to Raw mode | Mode indicator changes; observe without assuming particular transcript errors | NOT RUN |
| 7 | Stop capture | Final transcript visible | NOT RUN |
| 8 | Listen to the same-input WAV pair produced in §4 | RNNoise.wav has less fan/keyboard noise than raw.wav; primary voice is still present | NOT RUN |
| 9 | Check RNNoise timing metrics in the optional developer panel or report/log | Per-frame processing time and avg/p95 are displayed | NOT RUN |

### Error Scenarios

| Step | Action | Expected Result | Status |
|------|--------|----------------|--------|
| E1 | Start with RNNoise model file missing/renamed | Explicit RNNoise stage-unavailable reason; affected modes rejected (FR-10) | NOT RUN |
| E2 | Start with RNNoise model file corrupted | Error message indicating model load failure | NOT RUN |

## 6. Automated Tests

| Test | What it checks | Status |
|------|---------------|--------|
| Unit: RNNoise wrapper processes frames | Injected backend receives 480-sample 48 kHz frames; assert finite float32 shape, normalized/int16-unit scaling and preserved metadata; mocks cannot prove denoising | NOT RUN |
| Unit: RNNoise wrapper handles 48 kHz input | Assert native frame size 480 and reject wrong rate/shape or non-finite samples; zero output can be valid | NOT RUN |
| Integration: Raw → RNNoise path | Assert RNNoise then one stateful 48→16 kHz conversion before ASR; duration/clock and reset/flush remain correct | NOT RUN |
| Unit: Mode switch Raw↔RNNoise | Availability checked first; serialized epoch boundary, state reset and old-utterance finalization; no cross-mode ASR window | NOT RUN |
| Unit: RNNoise model missing error | Missing model/library reports unavailable stage; runtime failure stops capture with explicit error, never silent Raw fallback | NOT RUN |

Mocks establish plumbing only; nonzero output does not establish real suppression. A separate pinned real RNNoise fixture run must verify native loading, finite output and measured/aligned audio plus transcript quality. Its status is **NOT RUN**.

## 7. Latency / Timing Collection

| Metric | How to collect | Status |
|--------|---------------|--------|
| RNNoise per-frame processing time (avg) | Instrument wrapper, log mean | NOT RUN |
| RNNoise per-frame processing time (p95) | Instrument wrapper, log 95th percentile | NOT RUN |
| End-to-end latency (Raw mode) | Timestamp capture → transcript display | NOT RUN |
| End-to-end latency (RNNoise mode) | Timestamp capture → transcript display | NOT RUN |
| Dropped frames during mode switch | Record per-boundary dropped samples and gap resets separately from late frames; zero is aspirational, with no PRD numeric threshold | NOT RUN |

## 8. Pass Criteria

- RNNoise-only mode produces a cleaner transcript than Raw in static-noise conditions.
- Mode switching works without restart or crash.
- Same-input recorded audio shows audible noise reduction with primary intelligibility retained; missing replay evidence leaves this criterion NOT RUN.
- Primary speech remains intelligible and transcribable, with no normal phrase erasure; assess reference-based retention separately against Raw without inventing a numeric cutoff.
- Error messages appear when RNNoise model is unavailable.
- RNNoise timing metrics are collected; the developer panel is optional, so a report/log is sufficient.

## 9. Known Limitations at This Stage

- RNNoise is designed for non-speech noise (fans, HVAC, keyboard). Competing-speaker suppression is Hush's responsibility (H2); do not claim RNNoise alone fulfills it.
- If the test environment has both fan noise AND competing speech, RNNoise alone will not address the speech interference.
- RNNoise operates at 48 kHz. Raw already requires a stateful 48→16 kHz ASR conversion in M0; H1 tests RNNoise followed by that conversion. M4 adds Hush after the same single conversion boundary.

## 10. Feedback Record

| Date | Tester | Feedback | Action Taken |
|------|--------|----------|--------------|
| — | — | — | — |
