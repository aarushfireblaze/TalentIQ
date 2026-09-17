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

All scenarios use the same reference passages defined in `docs/acceptance.md` §2. The background reference passage uses distinct ordinary-English words (e.g., "Please turn down the music because I am trying to study for my exam tomorrow morning at the library.") for fair Whisper intrusion attribution.

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
| Comparison | Transcript cleanliness; audio waveform noise reduction |
| Pass criterion | RNNoise and Combined outperform Raw on transcript cleanliness |
| Status | NOT RUN |

### T3 — Competing Speaker
| Field | Value |
|-------|-------|
| Inputs | Primary speaker near mic + background speaker 3–6 feet away |
| Modes to test | Raw, RNNoise, Hush, Combined |
| Comparison | Background word count per mode |
| Pass criterion | Combined has fewer background words than Raw |
| Status | NOT RUN |

### T4 — Mixed Noise
| Field | Value |
|-------|-------|
| Inputs | Primary speaker + fan + nearby conversation |
| Modes to test | Raw, RNNoise, Hush, Combined |
| Comparison | Combined is strongest overall mode |
| Pass criterion | Combined has lowest background word count and cleanest transcript |
| Status | NOT RUN |

### T5 — Stress (10-Minute Stability)
| Field | Value |
|-------|-------|
| Inputs | Continuous 10-minute capture; speech in 30s on/30s off bursts; fan noise throughout; occasional background speech |
| Modes to test | Combined (primary); verify all modes individually if time permits |
| Metrics | Memory (RSS), queue depth, dropped frames, p95 latency, transcript continuity |
| Pass criterion | No crash, no runaway memory, no stuck queue; latency growth measured but not a hard gate |
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

1. Launch application (exact commands TBD after architecture handoff).
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

**Total estimated time:** ~33 minutes per full evaluation run.

### Per-Scenario Steps

For each scenario (T1–T4):

| Step | Action | Expected Result | Status |
|------|--------|----------------|--------|
| 1 | Set up noise sources per scenario | Environment matches scenario description | NOT RUN |
| 2 | Start recording in Raw mode | Status: Listening | NOT RUN |
| 3 | Primary speaker: read reference passage for 30 seconds | Primary transcript appears | NOT RUN |
| 4 | Background speaker (T3/T4/T6): speak concurrently | Background words appear in Raw transcript | NOT RUN |
| 5 | Switch to RNNoise-only | Mode indicator changes | NOT RUN |
| 6 | Repeat speech for 30 seconds | Transcript reflects RNNoise filtering | NOT RUN |
| 7 | Switch to Hush-only | Mode indicator changes | NOT RUN |
| 8 | Repeat speech for 30 seconds | Transcript reflects Hush filtering | NOT RUN |
| 9 | Switch to Combined | Mode indicator changes | NOT RUN |
| 10 | Repeat speech for 30 seconds | Transcript reflects Combined filtering | NOT RUN |
| 11 | Stop recording | Final transcript visible | NOT RUN |
| 12 | Save/export WAVs if A/B mode enabled | Four WAV files per scenario | NOT RUN |
| 13 | Record metrics from developer panel | Timing, dropped frames, queue depth | NOT RUN |

### T5 (Stress) Steps

| Step | Action | Expected Result | Status |
|------|--------|----------------|--------|
| 1 | Start recording in Combined mode | Status: Listening | NOT RUN |
| 2 | Speak in 30s-on/30s-off bursts for 10 minutes | Transcript appears intermittently | NOT RUN |
| 3 | Fan/HVAC noise throughout | Noise is present in audio | NOT RUN |
| 4 | Occasional background speech (2–3 times) | Background words appear but are reduced | NOT RUN |
| 5 | Monitor memory (RSS) at 30-second intervals | No unbounded growth | NOT RUN |
| 6 | Check queue depth at regular intervals | Bounded, no growth trend | NOT RUN |
| 7 | Check dropped frame count | Zero or minimal | NOT RUN |
| 8 | After 10 minutes, stop | No crash; transcript complete | NOT RUN |
| 9 | Review p95 latency from developer panel | No severe growth from start to end | NOT RUN |

### T6 (Loud Interferer) Steps

| Step | Action | Expected Result | Status |
|------|--------|----------------|--------|
| 1 | Start recording in Combined mode | Status: Listening | NOT RUN |
| 2 | Primary speaker: speak at normal volume | Primary transcript appears | NOT RUN |
| 3 | Background speaker: lean in or raise voice significantly | Background speech may overwhelm filtering | NOT RUN |
| 4 | Observe transcript behavior | Document what happens — partial suppression? Complete failure? | NOT RUN |
| 5 | Switch between modes to compare | Note which modes handle loud interferer best | NOT RUN |
| 6 | Stop recording | Document findings honestly | NOT RUN |

## 5. Results Summary

### T1–T4 Comparison Table

| Scenario | Mode | Total Words | Background Words | Background % | Primary Words | Latency (s) | Notes | Status |
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
| Dropped frames | — | — | — | NOT RUN |
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
- T2: RNNoise and Combined produce cleaner transcripts than Raw.
- T3: Combined has fewer background words than Raw.
- T4: Combined is the strongest overall mode.
- T5: No crash, no unbounded memory growth, no stuck queue.
- T6: Honest documentation of failure behavior. Not faked as success.

**Desired targets (measured relative to raw baseline):**
- P-01: Transcript latency feels live (target ≤ 1.5 s).
- P-02: 10-minute session shows no severe latency growth.
- P-06: Pipeline runs on laptop CPU without discrete GPU.

Note: PRD T1 does not demand zero dropped words or zero dropped frames. Retention is compared relative to the raw baseline.

## 7. Known Limitations Documented Here

1. **Hush is not speaker identification.** Closest/loudest speaker assumption may fail (PRD §4).
2. **Loud interferer (T6)** is a known failure case. PRD §16 explicitly says "do not fake success."
3. **Resampling artifacts** may appear at RNNoise→Hush boundary (PRD §16).
4. **ASR quality** is not the focus; filtering quality is the comparison metric.
5. **Back-to-back recordings** (when live replay is not available) introduce slight environmental variability.
6. **CPU-only constraint** — performance may vary on older laptops; target is "modern laptop CPU" (PRD P-06).

## 8. Feedback Record

| Date | Tester | Scenario | Feedback | Action Taken |
|------|--------|----------|----------|--------------|
| — | — | — | — | — |
