# Acceptance Matrix — Voice Filtering System MVP

Updated: 2026-09-17
Status: **NOT RUN** — aligned with architecture contract v1 and the prescribed M0 plan; implementation and product behavior are not verified by this document reconciliation.

---

## 1. Requirement-to-Milestone Mapping

| Req ID | Requirement | Milestone(s) | Checkpoint(s) | Test Type |
|--------|-------------|---------------|----------------|-----------|
| FR-01 | Microphone capture | M0 | H0 | Automated plumbing + user-observed |
| FR-02 | Canonical audio format (48 kHz source, one 16 kHz boundary per path) | M0–M4 | H0–H2 | Automated plumbing + real model |
| FR-03 | RNNoise stage | M1 | H1 | Real model + user-observed |
| FR-04 | Hush stage, including Combined order | M2–M4 | H2 | Real model + user-observed |
| FR-05 | Streaming ASR | M0 | H0 | Automated plumbing + user-observed |
| FR-06 | Real-time UI | M0 | H0 | User-observed |
| FR-07 | Bypass modes (Raw/RNNoise/Hush/Combined) | M0–M4 | H0–H2 | Automated plumbing + user-observed |
| FR-08 | Error handling | M0 | H0 | Automated plumbing + user-observed |
| FR-09 | Opt-in raw/ASR-input recording; later four-mode QA | M0–M5 | H0–H3 | Automated plumbing + user-observed |
| FR-10 | No silent fallback | M0–M4 | H0–H2 | Automated plumbing + user-observed |
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
| FR-10 — No silent fallback | M0, M1, M3, M4, M7 | Each new stage must prove it does not silently pretend filtering is active when its model is unavailable |
| P-01 — Perceived latency ≤ 1.5 s | M0, M1, M3, M4, M7 | Each stage adds processing time; latency must be re-measured with full pipeline |
| P-06 — CPU-only operation | M0, M1, M3, M4, M7 | Combined pipeline load may exceed CPU capacity; must verify at each stage |

## 2. Test Input Definitions (T1–T6)

### Shared comparison and scoring protocol

Comparative acceptance for T1–T4 requires the same immutable recorded 48 kHz mono source clip in every mode, with independent/reset pipeline state and identical ASR model revision/settings. Record fixture identity/hash, device and OS microphone processing, sample rates, measured alignment delay, gaps/drops and reference transcripts. H1 compares Raw/RNNoise; H2 requires M3 **and** M4 implemented and compares all four modes; H3 repeats the full matrix with M5 tooling. If replay/evidence is unavailable, comparative acceptance remains **NOT RUN**. Back-to-back live takes are exploratory only; they cannot replace same-recorded-input comparative acceptance. Live mode-switch checks separately establish lifecycle behavior.

Freeze the actual spoken primary and background reference transcripts for each clip before scoring, including repetitions and the exact scored interval; the sample passages below are prompts, not a claim of 30 seconds of speech. Align normalized transcript words to those references with human review. Attribute shared/ambiguous words by context and audio; record unresolved words separately rather than crediting them to either speaker automatically.

- Let `N_bg` be the fixed number of background reference words spoken in the scored clip and `B_mode` the number of transcript words attributable to that speaker. Report **background intrusion rate = 100 × B_mode / N_bg**. Use the same `N_bg` for every mode, never the output transcript length. Count repeated background intrusions and document alignment rules; the rate may exceed 100% if ASR duplicates words. For T1/T2 with no background speech, report N/A, not zero percent.
- Let `N_primary` be the fixed primary reference word count and `P_mode` the correctly retained primary reference tokens, matched once each. Report **primary retention = 100 × P_mode / N_primary** separately and compare it with Raw; also listen for intelligibility and erased normal phrases. Do not use reduced total output as evidence of improvement. The PRD sets no 90% retention cutoff or numeric intrusion-reduction threshold.
- If Raw has no attributable background intrusions, that clip cannot demonstrate fewer intrusions. Report the floor effect and obtain another documented same-input fixture before claiming the competing-speech criterion.

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
- **Background reference:** None (non-speech noise); compare aligned noise-only intervals and listen to recorded audio while assessing primary retention separately. Overall RMS reduction alone cannot prove useful suppression.
- **Collection:** `raw.wav`, `rnnoise.wav`, `combined.wav` and transcripts from the same recorded source via the shared protocol. H1 covers Raw/RNNoise only; Combined is assessed after M4.
- **Pass criterion:** RNNoise and Combined outperform Raw on transcript cleanliness. Recorded audio quality shows noise reduction without speech damage.

### T3 — Competing Speaker
- **Inputs:** Primary speaker near laptop + second person several feet away speaking concurrently.
- **Setup:** Primary speaker at normal mic distance. Second speaker at 3–6 feet away at lower-to-moderate volume.
- **Primary reference words:** Fixed passage (same as T1/T2).
- **Background reference words:** Second speaker uses a distinct passage in ordinary English (e.g., "Please turn down the music because I am trying to study for my exam tomorrow morning at the library.") to enable word-level attribution via Whisper.
- **Collection:** Raw transcript, Hush transcript, Combined transcript. Count background intrusions against the fixed background reference and primary retention separately using the shared protocol.
- **Pass criterion:** Combined inserts materially fewer background-speaker words than Raw. Hush-only shows improvement over Raw.

### T4 — Mixed Noise
- **Inputs:** Primary speaker + fan + nearby conversation.
- **Setup:** Combine T2 and T3 noise sources simultaneously.
- **Primary reference words:** Same fixed passage.
- **Background reference words:** Same as T3.
- **Collection:** All four mode transcripts. Qualitative comparison.
- **Pass criterion:** Combined is the strongest overall mode considering static noise, background intrusion rate and primary retention together; lowest intrusion alone is insufficient.

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
| Dropped/late audio frames | Record dropped samples separately at source/ASR boundaries, discontinuities and late frames (>100 ms at DSP dequeue per architecture); do not conflate loss with lateness | Zero is aspirational; PRD specifies no binding numeric threshold |
| Queue depth between stages | Sample depth/capacity at regular intervals | Bounded; no runaway or stuck queue |
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

Sequence: M0 → H0 → M1 → H1 → M2 → M3 **and M4** → H2 → M5–M6 → H3 → M7. M4 must precede H2; early replay support is needed for H1/H2 even though the complete evaluator is M5.

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
