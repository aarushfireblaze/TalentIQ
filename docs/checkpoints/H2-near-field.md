# H2 — Near-Field & Background Speaker Checkpoint: Hush / Combined

Status: **NOT RUN**
Depends on: H1 pass + M3–M4 completion
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

1. **Record once in Raw mode** with both speakers for 60 seconds. Save as `raw_t3.wav`.
2. **Replay the same WAV** through each of the three filtered modes:
   - RNNoise-only → `rnnoise_t3.wav`
   - Hush-only → `hush_t3.wav`
   - Combined → `combined_t3.wav`
3. Transcribe all four recordings with the same ASR model.
4. Count words in the transcript that match the background reference passage.
5. Count words that match the primary reference passage.
6. Compare: background word count should be lowest in Combined; primary word count should be preserved across all modes.

**Critical:** Replaying the same recorded WAV through each mode is the only way to ensure identical input. Live re-speaking the passage introduces different timing, volume, and inflection — it is NOT the same input and is not a fair comparison. When live replay is not feasible, record back-to-back sessions (same positions, same volume) within 60 seconds and note this as a limitation.

## 5. Human Test Script

### Launch

**Note:** Exact launch commands depend on architecture decisions. Update after architecture handoff.

1. Launch the application with RNNoise and Hush enabled.
2. Confirm both models loaded (no error in status).
3. Have primary speaker and background speaker in position.

### Test Steps

| Step | Action | Expected Result | Status |
|------|--------|----------------|--------|
| 1 | Start recording in Raw mode | Both speakers are transcribed; transcript is mixed | NOT RUN |
| 2 | Primary speaker: speak reference passage for 30 seconds | Primary words appear in transcript | NOT RUN |
| 3 | Background speaker: speak reference passage concurrently | Background words also appear in transcript (Raw mode) | NOT RUN |
| 4 | Switch to Hush-only mode (live) | Mode indicator changes; background speech is reduced in transcript | NOT RUN |
| 5 | Repeat speech for 30 seconds | Primary words preserved; fewer background words | NOT RUN |
| 6 | Switch to Combined mode (live) | Mode indicator changes; both noise and background speech reduced | NOT RUN |
| 7 | Repeat speech for 30 seconds | Primary words preserved; background words are minimal or absent | NOT RUN |
| 8 | Switch back to Raw mode | Both speakers appear in transcript again | NOT RUN |
| 9 | Stop recording | Final transcript visible | NOT RUN |
| 10 | Listen to saved WAVs (if A/B recording enabled) | Combined.wav has least background speech; primary voice present | NOT RUN |
| 11 | Check developer panel for Hush timing metrics | Per-frame processing time displayed | NOT RUN |

### Error Scenarios

| Step | Action | Expected Result | Status |
|------|--------|----------------|--------|
| E1 | Start with Hush model file missing/renamed | Error message: "Hush model not available" (FR-10) | NOT RUN |
| E2 | Start with Hush model file corrupted | Error message indicating model load failure | NOT RUN |
| E3 | Start with both RNNoise and Hush models missing | Both error messages appear; no silent fallback | NOT RUN |

## 6. Automated Tests

| Test | What it checks | Status |
|------|---------------|--------|
| Unit: Hush wrapper processes 16 kHz frames | Mock 16 kHz PCM frame in → enhanced frame out | NOT RUN |
| Unit: Hush wrapper output shape matches input | Output frame length equals input frame length | NOT RUN |
| Integration: RNNoise → resample → Hush path | Combined pipeline produces output frames | NOT RUN |
| Unit: Mode switch Raw↔Hush↔Combined | PipelineController.switch_mode toggles correctly | NOT RUN |
| Unit: Hush model missing error | Missing model file triggers FR-10 error event | NOT RUN |
| Integration: Four-mode comparison on same fixture | Same WAV processed through all four modes; output files saved | NOT RUN |

## 7. Latency / Timing Collection

| Metric | How to collect | Status |
|--------|---------------|--------|
| Hush per-frame processing time (avg) | Instrument wrapper, log mean | NOT RUN |
| Hush per-frame processing time (p95) | Instrument wrapper, log 95th percentile | NOT RUN |
| End-to-end latency (Hush-only mode) | Timestamp capture → transcript display | NOT RUN |
| End-to-end latency (Combined mode) | Timestamp capture → transcript display | NOT RUN |
| Resample boundary timing | Time the 48 kHz → 16 kHz conversion at RNNoise/Hush boundary | NOT RUN |
| Dropped frames during mode switch | Count frames lost during live mode switch | NOT RUN |

## 8. Quantitative Collection: Background Word Count

For each mode, count transcript words attributable to the background speaker:

| Mode | Total Words | Background Words | Background % | Primary Words Preserved | Status |
|------|-------------|------------------|--------------|------------------------|--------|
| Raw | — | — | — | — | NOT RUN |
| RNNoise-only | — | — | — | — | NOT RUN |
| Hush-only | — | — | — | — | NOT RUN |
| Combined | — | — | — | — | NOT RUN |

**Pass criterion:** Combined has the lowest Background %. Primary Words Preserved should be ≥90% of Raw in all filtered modes (no aggressive speech erasure).

## 9. Pass Criteria

- Hush-only mode produces fewer background-speaker words than Raw.
- Combined mode produces the fewest background-speaker words overall.
- Primary speaker's transcript is preserved — no phrase erasure.
- Mode switching works without restart or crash.
- Error messages appear when Hush model is unavailable.
- Developer panel shows Hush timing metrics.

## 10. Known Limitations at This Stage

- **Hush is not identity verification.** It assumes the closest/loudest speaker is the target. If the background speaker is louder or closer, Hush may not suppress them correctly (PRD §4, §16).
- **T6 — Loud interferer:** When the background speaker becomes very loud or very close, Hush may fail to suppress them. This is a known edge case to be documented honestly in H3, not faked as success.
- Resampling at the RNNoise→Hush boundary should be tested here for the first time. Any artifacts from resampling will be visible in the Combined output.
- ASR quality is secondary; the comparison is about filtering quality, not ASR optimization.

## 11. Feedback Record

| Date | Tester | Feedback | Action Taken |
|------|--------|----------|--------------|
| — | — | — | — |
