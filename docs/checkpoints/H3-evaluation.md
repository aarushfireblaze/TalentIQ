# H3 — Evaluation Checkpoint: Four-Mode A/B + 10-Minute Stability

Status: **NOT RUN**
Depends on: H2 pass + M5–M6 completion
Blocks: M7 (final acceptance)

---

## 1. Objective

Run the repeatable four-mode evaluation (T1–T4, T6) on the same test fixtures across Raw, RNNoise, Hush, and Combined. Complete the 10-minute stress test (T5). Document all results honestly, including failures and limitations. This checkpoint produces the final evaluation evidence for M7 acceptance.

## 2. What H3 Validates

| Requirement | Validated? |
|-------------|------------|
| FR-01 through FR-10 | NOT RUN (full stack re-validated) |
| P-01 — Perceived latency ≤ 1.5 s | NOT RUN |
| P-02 — 10-minute stability | NOT RUN |
| P-03 — Background noise reduction | NOT RUN |
| P-04 — Competing speech reduction | NOT RUN |
| P-05 — Primary speech retention | NOT RUN |
| P-06 — CPU-only operation | NOT RUN |
| P-07 — Mode switching | NOT RUN |

## 3. Test Scenarios

All scenarios use the reference passages and [shared scoring protocol](../acceptance.md#shared-comparison-and-scoring-protocol) in `docs/acceptance.md` §2. T1–T4 comparative acceptance requires the same immutable recorded input across modes; back-to-back live takes are exploratory only and cannot replace it. Freeze actual spoken reference counts per clip and assess primary retention separately from background intrusion rate. The background reference passage uses distinct ordinary-English words (e.g., "Please turn down the music because I am trying to study for my exam tomorrow morning at the library.") for fair Whisper intrusion attribution.

### T1 — Quiet Room

| Field | Value |
|-------|-------|
| Inputs | Primary speaker only |
| Modes to test | Raw, RNNoise, Hush, Combined |
| Comparison | Combined transcript vs Raw transcript |
| Pass criterion | Combined close to Raw; no speech damage |
| Status | NOT RUN |

### T2 — Static Noise

| Field | Value |
|-------|-------|
| Inputs | Primary speaker + fan/HVAC/keyboard |
| Modes to test | Raw, RNNoise, Hush, Combined |
| Comparison | Transcript cleanliness, aligned noise-only audio intervals and primary retention |
| Pass criterion | RNNoise and Combined outperform Raw on transcript cleanliness and recorded audio quality without speech damage |
| Status | NOT RUN |

### T3 — Competing Speaker

| Field | Value |
|-------|-------|
| Inputs | Primary speaker near mic + background speaker 3–6 feet away |
| Modes to test | Raw, RNNoise, Hush, Combined |
| Comparison | Background intrusion rate per fixed background reference count; primary retention separately |
| Pass criterion | Hush has fewer background words than Raw; Combined has materially fewer, with primary speech retained |
| Status | NOT RUN |

### T4 — Mixed Noise

| Field | Value |
|-------|-------|
| Inputs | Primary speaker + fan + nearby conversation |
| Modes to test | Raw, RNNoise, Hush, Combined |
| Comparison | Combined is strongest overall mode |
| Pass criterion | Combined is strongest overall across noise, intrusion rate and primary retention; background count alone is insufficient |
| Status | NOT RUN |

### T5 — Stress (10-Minute Stability)

| Field | Value |
|-------|-------|
| Inputs | Continuous 10-minute capture; speech in 30s on/30s off bursts; fan noise throughout; occasional background speech |
| Modes to test | Combined (primary); verify all modes individually if time permits |
| Metrics | Memory (RSS), queue depth, dropped frames, p95 latency, transcript continuity |
| Pass criterion | No crash, no runaway memory, no stuck queue and no severe latency growth (PRD T5); record actual measurements, as the PRD gives no numeric growth cutoff |
| Status | NOT RUN |

### T6 — Loud Interferer

| Field | Value |
|-------|-------|
| Inputs | Same as T3, but background speaker leans in or raises voice significantly |
| Modes to test | Raw, RNNoise, Hush, Combined |
| Comparison | Document what happens — does filtering fail gracefully? |
| Pass criterion | **Known edge case.** Document failure honestly. Do not fake success. |
| Status | NOT RUN |

## 4. Human Test Script

### Pre-Test Setup

1. Use reviewed M5/M6 implementation handoff commands for model setup, launch and replay; these future commands are not verified here. [H0](H0-baseline.md) contains prescribed, unverified M0 commands, which do not enable filters or the evaluator.
2. Confirm all models loaded (RNNoise, Hush, ASR).
3. Prepare test environment:
   - Quiet room for T1.
   - Fan/HVAC positioned for T2.
   - Second speaker positioned for T3/T4/T6.
4. Have reference passages printed or displayed for speakers.

### Test Execution Order

Execute in this order to minimize environment changes:

1. **T1 (Quiet Room)** — 5 minutes
2. **T2 (Static Noise)** — 5 minutes
3. **T3 (Competing Speaker)** — 5 minutes
4. **T4 (Mixed Noise)** — 5 minutes
5. **T5 (10-Minute Stress)** — 10 minutes
6. **T6 (Loud Interferer)** — 3 minutes

**Estimated live scenario time:** ~33 minutes, excluding fixture preparation, four-mode replay, decoding and scoring; this is not a measured runtime.

### Same-Recorded-Input Comparative Steps

For each scenario (T1–T4), use opt-in recorded fixtures; recording is off by default. Missing same-input replay leaves comparative acceptance **NOT RUN**. Live switching/re-speaking checks are separate exploratory observations and cannot populate the comparison table.

| Step | Action | Expected Result | Status |
|------|--------|----------------|--------|
| 1 | Set up the scenario and explicitly opt in to QA capture, or select a documented existing fixture | One 48 kHz mono source clip | NOT RUN |
| 2 | During capture, read primary reference; T3/T4 background speaker speaks concurrently | Actual spoken references documented, including repetitions | NOT RUN |
| 3 | Stop capture; freeze clip/hash, scored interval and reference transcripts | Fixed N_primary and N_bg; N_bg absent for T1/T2 | NOT RUN |
| 4 | Replay identical source through Raw | Independent/reset state; ASR settings recorded | NOT RUN |
| 5 | Replay source through RNNoise-only | Same source bytes and ASR settings | NOT RUN |
| 6 | Replay source through Hush-only | Same source bytes and ASR settings | NOT RUN |
| 7 | Replay source through Combined | RNNoise → one 16 kHz boundary → Hush → ASR | NOT RUN |
| 8 | Save four mode WAVs/transcripts and metrics/provenance | Rates, revisions, resets, drops and measured delay documented | NOT RUN |
| 9 | Align by measured delay, listen and attribute words with contextual review | Noise, primary phrase loss and ambiguous attribution recorded | NOT RUN |
| 10 | Score intrusions and retention separately under the shared protocol | Fixed denominators; Raw floor effects explicit | NOT RUN |
| 11 | Record stage timing/queues/losses; measure live delay separately | Offline decode speed is not live latency evidence | NOT RUN |

### T5 (Stress) Steps

| Step | Action | Expected Result | Status |
|------|--------|----------------|--------|
| 1 | Start capture in Combined mode | Status: Listening | NOT RUN |
| 2 | Speak in 30s-on/30s-off bursts for 10 minutes | Transcript appears intermittently | NOT RUN |
| 3 | Fan/HVAC noise throughout | Noise is present in audio | NOT RUN |
| 4 | Occasional background speech (2–3 times) | Record actual intrusions and primary continuity; no fresh-take comparative claim | NOT RUN |
| 5 | Monitor memory (RSS) at 30-second intervals | No unbounded growth | NOT RUN |
| 6 | Check queue depth at regular intervals | Bounded, no runaway or stuck queue | NOT RUN |
| 7 | Check dropped samples by boundary, gap resets and separate late-frame counts | Zero drops is aspirational; PRD sets no binding numeric threshold; record losses and impact | NOT RUN |
| 8 | After 10 minutes, stop | No crash; transcript complete | NOT RUN |
| 9 | Review p95 latency from optional developer panel or report/log | No severe growth from start to end | NOT RUN |

### T6 (Loud Interferer) Steps

Observe the edge case live, then replay a single recorded T6 clip through all modes for comparative findings. Fresh live takes remain exploratory; retain fixed-reference scoring and document failure honestly.

| Step | Action | Expected Result | Status |
|------|--------|----------------|--------|
| 1 | Start capture in Combined mode | Status: Listening | NOT RUN |
| 2 | Primary speaker: speak at normal volume | Primary transcript appears | NOT RUN |
| 3 | Background speaker: lean in or raise voice significantly | Background speech may overwhelm filtering | NOT RUN |
| 4 | Observe transcript behavior | Document what happens — partial suppression? Complete failure? | NOT RUN |
| 5 | Switch between modes to compare | Record live observations only; compare modes on the same recorded T6 clip | NOT RUN |
| 6 | Stop capture | Document findings honestly | NOT RUN |

## 5. Results Summary

### T1–T4 Comparison Table

Intrusion rate = `100 × B_mode / N_bg`; primary retention = `100 × P_mode / N_primary`, assessed separately against Raw and listening notes. Use N/A for background metrics in T1/T2. No PRD 90% cutoff exists. Attach clip/hash and attribution evidence; live delay is separate, never inferred from offline replay.

| Scenario | Mode | N_bg / N_primary (fixed) | B_mode | Intrusion rate (%) | P_mode / retention (%) | Live delay (s) | Notes | Status |
|----------|------|-------------|------------------|--------------|---------------|-------------|-------|--------|
| T1 | Raw | — | — | — | — | — | — | NOT RUN |
| T1 | RNNoise | — | — | — | — | — | — | NOT RUN |
| T1 | Hush | — | — | — | — | — | — | NOT RUN |
| T1 | Combined | — | — | — | — | — | — | NOT RUN |
| T2 | Raw | — | — | — | — | — | — | NOT RUN |
| T2 | RNNoise | — | — | — | — | — | — | NOT RUN |
| T2 | Hush | — | — | — | — | — | — | NOT RUN |
| T2 | Combined | — | — | — | — | — | — | NOT RUN |
| T3 | Raw | — | — | — | — | — | — | NOT RUN |
| T3 | RNNoise | — | — | — | — | — | — | NOT RUN |
| T3 | Hush | — | — | — | — | — | — | NOT RUN |
| T3 | Combined | — | — | — | — | — | — | NOT RUN |
| T4 | Raw | — | — | — | — | — | — | NOT RUN |
| T4 | RNNoise | — | — | — | — | — | — | NOT RUN |
| T4 | Hush | — | — | — | — | — | — | NOT RUN |
| T4 | Combined | — | — | — | — | — | — | NOT RUN |

### T5 Stability Metrics

| Metric | Start | End (10 min) | Growth | Status |
|--------|-------|--------------|--------|--------|
| Memory (RSS, MB) | — | — | — | NOT RUN |
| Queue depth (avg) | — | — | — | NOT RUN |
| Dropped samples by source/ASR boundary | — | — | — | NOT RUN |
| Late frames / gap resets | — | — | — | NOT RUN |
| p95 latency (ms) | — | — | — | NOT RUN |
| Transcript continuity | — | — | — | NOT RUN |
| Crashes | — | — | — | NOT RUN |

### T6 Loud Interferer Findings

| Mode | Behavior | Primary speech preserved? | Background suppressed? | Notes | Status |
|------|----------|--------------------------|----------------------|-------|--------|
| Raw | — | — | — | — | NOT RUN |
| RNNoise | — | — | — | — | NOT RUN |
| Hush | — | — | — | — | NOT RUN |
| Combined | — | — | — | — | NOT RUN |

## 6. Pass Criteria (Full)

**Binding pass criteria:**

- T1: Combined transcript is close to Raw; no speech damage.
- T2: RNNoise and Combined improve transcript cleanliness and recorded audio quality against Raw without speech damage.
- T3: Hush has fewer background words than Raw; Combined has materially fewer, with primary speech retained.
- T4: Combined is the strongest overall mode.
- T5: No crash, no unbounded memory growth, no stuck queue and no severe latency growth; attach time-series evidence. The PRD supplies no numeric severe-growth cutoff.
- T6: Honest documentation of failure behavior. Not faked as success.

**Measured targets:**

- P-01: Transcript latency feels live (target ≤ 1.5 s).
- Dropped frames: zero is aspirational; the PRD defines no binding numeric drop threshold. This does not waive T5 stability or loss reporting.
- P-06: Pipeline runs on laptop CPU without discrete GPU.

Note: PRD T1 does not demand zero dropped words or zero dropped frames. Retention is compared relative to the raw baseline.

## 7. Known Limitations Documented Here

1. **Hush is not speaker identification.** Closest/loudest speaker assumption may fail (PRD §4).
2. **Loud interferer (T6)** is a known failure case. PRD §16 explicitly says "do not fake success."
3. **Resampling artifacts** may appear at RNNoise→Hush boundary (PRD §16).
4. **ASR quality** is not the focus; filtering quality is the comparison metric.
5. **Back-to-back live takes** vary in timing, level and content; exploratory only, they cannot replace same-recorded-input comparative acceptance. Missing replay evidence leaves comparative tests NOT RUN.
6. **CPU-only constraint** — performance may vary on older laptops; target is "modern laptop CPU" (PRD P-06).

## 8. Feedback Record

| Date | Tester | Scenario | Feedback | Action Taken |
|------|--------|----------|----------|--------------|
| — | — | — | — | — |
