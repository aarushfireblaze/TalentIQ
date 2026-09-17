# Acceptance Matrix — Voice Filtering System MVP

Updated: 2026-09-17
Status: **NOT RUN** — awaiting architecture contracts and M0 implementation

---

## 1. Requirement-to-Milestone Mapping

| Req ID | Requirement | Milestone(s) | Checkpoint(s) | Test Type |
|--------|-------------|---------------|----------------|-----------|
| FR-01 | Microphone capture | M0 | H0 | Automated plumbing + user-observed |
| FR-02 | Canonical audio format (16 kHz boundary) | M0 | H0 | Automated plumbing |
| FR-03 | RNNoise stage | M1 | H1 | Real model + user-observed |
| FR-04 | Hush stage | M2–M3 | H2 | Real model + user-observed |
| FR-05 | Streaming ASR | M0 | H0 | Automated plumbing + user-observed |
| FR-06 | Real-time UI | M0 | H0 | User-observed |
| FR-07 | Bypass modes (Raw/RNNoise/Hush/Combined) | M0–M4 | H0–H2 | Automated plumbing + user-observed |
| FR-08 | Error handling | M0 | H0 | Automated plumbing + user-observed |
| FR-09 | Local recording for QA | M1 | H1 | Automated plumbing |
| FR-10 | No silent fallback | M1–M3 | H1–H2 | Automated plumbing + user-observed |
| P-01 | Perceived latency ≤ 1.5 s | M0 | H0 | User-observed |
| P-02 | 10-minute stability | M6 | H3 | Automated + user-observed |
| P-03 | Background noise reduction | M1 | H1 | Real model + user-observed |
| P-04 | Competing speech reduction | M3–M4 | H2 | Real model + user-observed |
| P-05 | Primary speech retention | M1–M4 | H1–H2 | Real model + user-observed |
| P-06 | CPU-only operation | M0 | H0 | User-observed |
| P-07 | Mode switching without restart | M0–M4 | H0–H2 | Automated plumbing + user-observed |

## 1b. Cross-Milestone Revalidation

Some requirements must be revalidated at each integration milestone because the full pipeline changes:

| Req ID | Revalidated at | Why |
|--------|---------------|-----|
| FR-08 — Error handling | M0, M1, M3, M4, M7 | Each new stage (RNNoise, Hush, Combined) introduces new failure modes (model missing, load failure, resampling error) |
| FR-10 — No silent fallback | M1, M3, M4, M7 | Each new stage must prove it does not silently pretend filtering is active when its model is unavailable |
| P-01 — Perceived latency ≤ 1.5 s | M0, M1, M3, M4, M7 | Each stage adds processing time; latency must be re-measured with full pipeline |
| P-06 — CPU-only operation | M0, M1, M3, M4, M7 | Combined pipeline load may exceed CPU capacity; must verify at each stage |

## 2. Test Input Definitions (T1–T6)

### T1 — Quiet Room
- **Inputs:** Primary speaker only, quiet room.
- **Setup:** Single person speaking at normal conversational volume into laptop mic. No background noise sources.
- **Primary reference words:** Use a fixed 30-second passage (e.g., "The quick brown fox jumps over the lazy dog. She sells seashells by the seashore. The rain in Spain stays mainly in the plain.") to ensure same-clip comparison.
- **Collection:** Raw transcript, Combined transcript, qualitative listening notes.
- **Pass criterion:** Combined transcript is close to Raw; filtering must not noticeably damage speech. Primary speech retention is comparable to raw baseline (no aggressive word erasure).

### T2 — Static Room Noise
- **Inputs:** Primary speaker + fan/HVAC/keyboard noise.
- **Setup:** Position laptop near a running fan or HVAC vent at moderate level. Typing on keyboard during speech.
- **Primary reference words:** Same fixed passage as T1 for comparison.
- **Background reference:** Fan noise is non-speech; measure audio waveform RMS reduction in noise bands.
- **Collection:** Raw.wav, RNNoise.wav, Combined.wav. **Same-clip comparison required:** record once in Raw mode, then replay the same WAV through each filtered mode. When live replay is not feasible, record back-to-back sessions in identical conditions (same speaker, same noise level, same position) within 60 seconds and note this as a limitation. Transcript from each mode.
- **Pass criterion:** RNNoise and Combined outperform Raw on transcript cleanliness. Recorded audio quality shows noise reduction without speech damage.

### T3 — Competing Speaker
- **Inputs:** Primary speaker near laptop + second person several feet away speaking concurrently.
- **Setup:** Primary speaker at normal mic distance. Second speaker at 3–6 feet away at lower-to-moderate volume.
- **Primary reference words:** Fixed passage (same as T1/T2).
- **Background reference words:** Second speaker uses a distinct passage in ordinary English (e.g., "Please turn down the music because I am trying to study for my exam tomorrow morning at the library.") to enable word-level attribution via Whisper.
- **Collection:** Raw transcript, Hush transcript, Combined transcript. Count words attributable to background speaker in each.
- **Pass criterion:** Combined inserts materially fewer background-speaker words than Raw. Hush-only shows improvement over Raw.

### T4 — Mixed Noise
- **Inputs:** Primary speaker + fan + nearby conversation.
- **Setup:** Combine T2 and T3 noise sources simultaneously.
- **Primary reference words:** Same fixed passage.
- **Background reference words:** Same as T3.
- **Collection:** All four mode transcripts. Qualitative comparison.
- **Pass criterion:** Combined is the strongest overall mode. Background word count is lowest in Combined.

### T5 — Stress (10-Minute Stability)
- **Inputs:** Continuous 10-minute capture with intermittent speech and noise.
- **Setup:** Speaker talks in bursts (30 seconds on, 30 seconds off) for 10 minutes. Fan/HVAC noise throughout. Occasional background speech.
- **Collection:** Memory usage over time, queue depth, dropped frames, processing latency (p95), transcript continuity.
- **Pass criterion:** No crash, no runaway memory, no stuck queue, no severe latency growth. Transcript remains continuous.

### T6 — Loud Interferer
- **Inputs:** Second speaker temporarily becomes very loud or very close to mic.
- **Setup:** Same as T3, but background speaker leans in or raises voice significantly.
- **Collection:** Transcript behavior during loud interference. Document what happens — does Hush/Combined fail gracefully? Does it retain some primary speech?
- **Pass criterion:** **Known edge case.** Document failure behavior honestly. Do not fake success. PRD explicitly says this is a limitation.

## 3. Latency / Timing / Dropped-Frame Collection

| Metric | How to collect | Target |
|--------|---------------|--------|
| End-to-end partial-text delay | Timestamp audio frame capture, timestamp transcript display | ≤ 1.5 s (P-01) |
| RNNoise per-frame processing time | Instrument wrapper; log avg and p95 | No target in PRD; baseline to be established |
| Hush per-frame processing time | Instrument wrapper; log avg and p95 | No target in PRD; baseline to be established |
| ASR partial-to-final delay | Timestamp ASR partial emit vs final emit | Baseline to be established |
| Dropped/late audio frames | Count frames that arrive after deadline in ring buffer | 0 target |
| Queue depth between stages | Sample queue depth at regular intervals | Bounded; no growth over time |
| Memory usage over 10 minutes | Sample RSS at 30-second intervals | No unbounded growth |

## 4. Qualitative Criteria (Observed Acceptance Criteria)

The PRD does not define numeric targets for these criteria. They are observed acceptance criteria evaluated by the human tester during H0–H3. Record observations honestly in the Feedback Record sections.

| Criterion | How to evaluate | Notes |
|-----------|----------------|-------|
| Primary speech intelligibility | User listens to processed audio and reads transcript | Must be understandable; suppression must not erase normal phrases |
| Transcript feels "live" | User subjective impression of responsiveness | Should not feel noticeably delayed |
| Mode labels are clear | User can identify which mode is active | UI must clearly indicate Raw/RNNoise/Hush/Combined |
| Error messages are helpful | Simulate failure (e.g., rename model file) | User should understand what went wrong |
| Copy/clear transcript works | User copies transcript text, clears panel | Functional check |

## 5. Honest Loud-Interferer Limitations

Per PRD Section 4 and 16:
- Hush is **not** a target-speaker identity-verification system.
- MVP assumes the intended speaker is the person **closest to and most acoustically dominant** at the laptop microphone.
- If a background person is louder or much closer, Hush may not preserve the intended identity.
- T6 explicitly documents this edge case. Results must honestly report what happens, including failure.
- Future mitigation: enrolled speaker verification/conditioning (out of MVP scope).

## 6. Test Status Summary

| Test | Status | Result | Date | Notes |
|------|--------|--------|------|-------|
| T1 — Quiet Room | NOT RUN | — | — | — |
| T2 — Static Noise | NOT RUN | — | — | — |
| T3 — Competing Speaker | NOT RUN | — | — | — |
| T4 — Mixed Noise | NOT RUN | — | — | — |
| T5 — Stress (10 min) | NOT RUN | — | — | — |
| T6 — Loud Interferer | NOT RUN | — | — | — |

## 7. Milestone Acceptance Status

| Milestone | Description | Status | Human Gate |
|-----------|-------------|--------|------------|
| M0 | Raw mic + ASR + transcript UI | NOT RUN | H0 pending |
| M1 | RNNoise wrapper + live mode | NOT RUN | H1 pending |
| M2 | Hush offline validation | NOT RUN | — |
| M3 | Hush streaming | NOT RUN | H2 pending |
| M4 | Combined pipeline | NOT RUN | H2 pending |
| M5 | A/B evaluator | NOT RUN | H3 pending |
| M6 | UX hardening | NOT RUN | H3 pending |
| M7 | Final T1–T6 acceptance | NOT RUN | Final review |

## 8. Definition of Done Checklist (per PRD §15)

- [ ] New developer can follow README and run MVP locally
- [ ] Mic capture, RNNoise, Hush, and ASR work in one continuous session
- [ ] Raw / RNNoise / Hush / Combined modes available and clearly labeled
- [ ] Combined mode produces fewer competing-speaker intrusions than Raw (T3)
- [ ] Combined mode reduces static-noise impact (T2)
- [ ] Primary speech remains intelligible (T1–T4)
- [ ] 10-minute stress test completes without crash or unbounded latency (T5)
- [ ] Failure states are surfaced explicitly (FR-08, FR-10)
- [ ] Benchmark/test results and known limitations documented
- [ ] progress.md shows all MVP milestones complete with verification commands
