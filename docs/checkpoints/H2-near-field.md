# H2 — Near-Field & Background Speaker Checkpoint: Hush / Combined

Status: **NOT RUN**
Depends on: H1 pass + M2 real offline validation + both M3 streaming Hush AND M4 Combined implemented
Blocks: H3

---

## 1. Objective

Validate Hush speaker suppression and the Combined (RNNoise → Hush) pipeline against the raw baseline. Test with a near-field primary speaker and a distant competing speaker. Confirm Hush preserves the dominant speaker while reducing background speech intrusions in the transcript.

## 2. What H2 Validates

| Requirement | Validated? |
|-------------|------------|
| FR-04 — Hush stage | NOT RUN |
| FR-07 — Bypass modes (all four: Raw, RNNoise, Hush, Combined) | NOT RUN |
| FR-10 — No silent fallback | NOT RUN |
| P-04 — Competing speech reduction | NOT RUN |
| P-05 — Primary speech retention | NOT RUN |
| P-07 — Mode switching without restart | NOT RUN |

## 3. Test Inputs

| Input | Description |
|-------|-------------|
| Primary speaker | Person at normal laptop mic distance (1–2 feet) |
| Background speaker | Second person at 3–6 feet away, speaking concurrently at lower-to-moderate volume |
| Primary reference passage | "The quick brown fox jumps over the lazy dog. She sells seashells by the seashore. The rain in Spain stays mainly in the plain." (30 seconds) |
| Background reference passage | "Please turn down the music because I am trying to study for my exam tomorrow morning at the library." (distinct ordinary-English words for Whisper attribution) |

## 4. Fair Same-Clip Comparison Method

Explicitly opt in to development recording (off by default), or use a documented recorded fixture. Each mode receives the same 48 kHz source with independent state and identical ASR settings.

1. **Record once in Raw mode** with both speakers for 60 seconds. Save as `raw_t3.wav`.
2. **Replay the same WAV** through each of the three filtered modes:
   - RNNoise-only → `rnnoise_t3.wav`
   - Hush-only → `hush_t3.wav`
   - Combined → `combined_t3.wav`
3. Transcribe all four recordings with the same ASR model.
4. Freeze the actual spoken background/primary reference word counts for the clip and attribute transcript words with contextual alignment, not naive matching of shared words.
5. Score background intrusions using the fixed background reference denominator and primary retention separately using [the shared protocol](../acceptance.md#shared-comparison-and-scoring-protocol).
6. Compare Hush and Combined against Raw while checking primary intelligibility and phrase retention; record fixture hash, ASR settings, measured delays, resets and drops.

**Critical:** Replaying the same recorded WAV through each mode is the only way to ensure identical input. Live re-speaking the passage introduces different timing, volume, and inflection — it is NOT the same input and is not a fair comparison. Back-to-back live takes are exploratory only and cannot replace same-recorded-input comparative acceptance. If replay is unavailable, comparative acceptance remains **NOT RUN**. Early replay support is required here; M5 later completes the evaluator.

## 5. Human Test Script

### Launch

**NOT YET VERIFIED:** Architecture contract v1 and [H0](H0-baseline.md) prescribe the baseline service. Use reviewed M3/M4 handoff commands for filter setup and replay; M0 commands do not provide Hush or Combined.

1. Launch the application with RNNoise and Hush enabled.
2. Confirm both models loaded (no error in status).
3. Have primary speaker and background speaker in position.

### Live Lifecycle / Exploratory Steps

Fresh live takes check usability and switching only. Filtering comparisons for H2 acceptance require the recorded-input evidence in §4 and separate retention scoring in §8.

| Step | Action | Expected Result | Status |
|------|--------|----------------|--------|
| 1 | Start capture in Raw mode | Status Listening; record actual baseline output | NOT RUN |
| 2 | Primary speaker: speak reference passage for 30 seconds | Primary words appear in transcript | NOT RUN |
| 3 | Background speaker: speak reference passage concurrently | Record any attributable background intrusions; absence is a floor effect, not suppression evidence | NOT RUN |
| 4 | Switch to Hush-only mode (live) | Mode indicator changes; observe background speech without treating a fresh take as a comparison | NOT RUN |
| 5 | Repeat speech for 30 seconds | Record primary/background observations for this exploratory take | NOT RUN |
| 6 | Switch to Combined mode (live) | Mode indicator changes; validate lifecycle; compare audio quality using §4 | NOT RUN |
| 7 | Repeat speech for 30 seconds | Record observations; do not presume suppression or retention | NOT RUN |
| 8 | Switch back to Raw mode | Raw indicator returns; retained finals and new transcript remain consistent | NOT RUN |
| 9 | Stop capture | Final transcript visible | NOT RUN |
| 10 | Listen to the same-input WAVs produced in §4 | Assess Hush/Combined background suppression against Raw and primary intelligibility separately | NOT RUN |
| 11 | Check Hush timing metrics in the optional developer panel or report/log | Per-frame processing time displayed | NOT RUN |

### Error Scenarios

| Step | Action | Expected Result | Status |
|------|--------|----------------|--------|
| E1 | Start with Hush model file missing/renamed | Explicit Hush stage-unavailable reason; affected modes rejected (FR-10) | NOT RUN |
| E2 | Start with Hush model file corrupted | Error message indicating model load failure | NOT RUN |
| E3 | Start with both RNNoise and Hush models missing | Both stage-unavailable reasons visible; affected modes rejected; no silent fallback | NOT RUN |

## 6. Automated Tests

| Test | What it checks | Status |
|------|---------------|--------|
| Unit: Hush wrapper processes 16 kHz frames | Injected backend receives 160-sample float32 hops at 16 kHz (20 ms analysis window, 10 ms hop); validate call/reset contract, not enhancement | NOT RUN |
| Unit: Hush wrapper output shape matches input | 160 finite output samples with preserved source metadata; padding/valid_samples, real delay and tail handling assessed separately | NOT RUN |
| Integration: RNNoise → resample → Hush path | Assert RNNoise 480/48k → one stateful resampler/reblock → Hush 160/16k → ASR, with duration/clock/gap handling | NOT RUN |
| Unit: Mode switch Raw↔Hush↔Combined | Check stage availability, serialized boundary, epoch/state reset, old-utterance finalization and rejection of stale inference | NOT RUN |
| Unit: Hush model missing error | Missing model/library exposes stage-unavailable reason; runtime failure stops capture with explicit error, never silent Raw fallback | NOT RUN |
| Integration: Four-mode comparison on same fixture | Identical immutable source, independent states/identical ASR settings, correct output metadata and alignment; fake output files prove wiring only | NOT RUN |

Mock output, even nonzero and correctly shaped, cannot prove real suppression. M2 must separately validate pinned native Hush loading, finite deterministic output, actual frame size, measured delay/alignment and flush/tail behavior. Real same-input audio/transcript comparison is needed for suppression; all such product checks are **NOT RUN**.

## 7. Latency / Timing Collection

| Metric | How to collect | Status |
|--------|---------------|--------|
| Hush per-frame processing time (avg) | Instrument wrapper, log mean | NOT RUN |
| Hush per-frame processing time (p95) | Instrument wrapper, log 95th percentile | NOT RUN |
| End-to-end latency (Hush-only mode) | Timestamp capture → transcript display | NOT RUN |
| End-to-end latency (Combined mode) | Timestamp capture → transcript display | NOT RUN |
| Resample boundary timing | Time the 48 kHz → 16 kHz conversion at RNNoise/Hush boundary | NOT RUN |
| Dropped frames during mode switch | Record dropped samples by boundary and gap resets separately from late frames; zero is aspirational, with no PRD numeric threshold | NOT RUN |

## 8. Quantitative Collection: Background Word Count

For each mode, use fixed `N_bg` and `N_primary` from the same scored source interval. Background intrusion rate is `100 × B_mode / N_bg`; primary retention is `100 × P_mode / N_primary`. Never divide by mode-dependent output length. Ambiguous attribution and Raw floor effects are handled by the shared protocol.

| Mode | N_bg / N_primary (fixed) | B_mode | Intrusion rate (%) | P_mode / primary retention (%) | Status |
|------|-------------|------------------|--------------|------------------------|--------|
| Raw | — | — | — | — | NOT RUN |
| RNNoise-only | — | — | — | — | NOT RUN |
| Hush-only | — | — | — | — | NOT RUN |
| Combined | — | — | — | — | NOT RUN |

**Pass criterion:** Hush has fewer background intrusions than Raw and Combined has materially fewer (PRD T3/P-04), with primary speech understandable/transcribable and no normal phrase erasure. Report both intrusion rates and separate retention against Raw; the PRD supplies no 90% retention cutoff. Lowest background count alone does not establish quality.

## 9. Pass Criteria

- Hush-only mode produces fewer background-speaker words than Raw.
- Combined mode produces materially fewer background-speaker words than Raw on identical recorded input; T3 does not require it to beat Hush-only.
- Primary speaker's transcript is preserved — no phrase erasure.
- Mode switching works without restart or crash.
- Error messages appear when Hush model is unavailable.
- Hush timing metrics are collected; an optional developer panel or a report/log may expose them.

## 10. Known Limitations at This Stage

- **Hush is not identity verification.** It assumes the closest/loudest speaker is the target. If the background speaker is louder or closer, Hush may not suppress them correctly (PRD §4, §16).
- **T6 — Loud interferer:** When the background speaker becomes very loud or very close, Hush may fail to suppress them. This is a known edge case to be documented honestly in H3, not faked as success.
- Stateful 48→16 kHz conversion is already required at M0/H0 and M1/H1. H2 revalidates its RNNoise→Hush placement and measured Combined alignment; inspect for resampling artifacts.
- ASR quality is secondary; the comparison is about filtering quality, not ASR optimization.

## 11. Feedback Record

| Date | Tester | Feedback | Action Taken |
|------|--------|----------|--------------|
| — | — | — | — |
