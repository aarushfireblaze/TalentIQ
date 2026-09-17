# Acceptance Plan — Handoff Document

Status: **NOT RUN**
Owner: acceptance/checkpoint documentation worker; reconciled against architecture contract v1
Created: 2026-09-17

---

## 1. Scope

This document defines the complete acceptance plan for the Voice Filtering System MVP. It maps PRD requirements to milestones and human checkpoints, defines test inputs and comparison methodology, and provides concrete human test scripts.

## 2. Document Inventory

| Document | Purpose | Path |
|----------|---------|------|
| Acceptance Matrix | Requirement-to-milestone mapping, T1–T6 definitions, qualitative criteria | `docs/acceptance.md` |
| H0 Checkpoint | Baseline: Raw mic + live ASR | `docs/checkpoints/H0-baseline.md` |
| H1 Checkpoint | Static noise: RNNoise A/B | `docs/checkpoints/H1-static-noise.md` |
| H2 Checkpoint | Near-field + background speaker: Hush/Combined | `docs/checkpoints/H2-near-field.md` |
| H3 Checkpoint | Four-mode evaluation + 10-minute stability | `docs/checkpoints/H3-evaluation.md` |
| This document | Acceptance plan and handoff summary | `docs/handoffs/acceptance-plan.md` |
| Reconciliation report | Documentation changes, exact checks and commit evidence | `docs/handoffs/checkpoint-reconciliation.md` |

## 3. Execution Order

```
Architecture contract v1 → M0 implementation + independent review → H0
H0 → M1 + same-input Raw/RNNoise evidence → H1
H1 → M2 offline validation → M3 streaming Hush AND M4 Combined → H2
H2 → M5 evaluator + M6 UX/stability → H3
H3 → M7 final acceptance
```

**H2 requires both M3 and M4 implemented; M4 cannot follow H2.** Minimal same-recorded-input replay/evidence is needed at H1/H2 before the full M5 evaluator. The coordinator may independently authorize offline M2 preparation without releasing dependent human gates. All product tests remain **NOT RUN**; documentation reconciliation proves no milestone implementation.

**Human gates require actual user feedback.** Automated tests never count as the user trying the product.

## 4. Test Type Classification

| Category | Examples | What they prove | Limitation |
|----------|----------|----------------|------------|
| Automated plumbing | Unit tests for wrappers, pipeline start/stop, mode switching | Wiring is correct; interfaces work | Do NOT prove real filtering, ASR accuracy, or latency |
| Real model tests | Pinned native RNNoise/Hush WAVs; separate real ASR smoke | Actual loading, finite shape, frame/rate contracts and alignment; suppression requires same-input audio/transcript evidence | Nonzero output alone proves no suppression; offline timing does not prove live latency |
| User-observed results | Human test scripts in H0–H3 | Real-world filtering quality, latency, usability | Subjective; requires actual user participation |

**Critical rule:** Synthetic or stub tests establish plumbing only. They cannot prove real filtering, ASR accuracy, microphone behavior, or latency targets.

## 5. Input Definitions Summary

| Test | Primary Input | Background Input | Reference Words (Primary) | Reference Words (Background) |
|------|--------------|-----------------|--------------------------|------------------------------|
| T1 | Speaker only | None | Fixed 30s passage | N/A |
| T2 | Speaker + fan/HVAC/keyboard | Non-speech noise | Fixed 30s passage | N/A (noise is non-speech) |
| T3 | Speaker near mic | Second speaker 3–6 ft away | Fixed 30s passage | "Please turn down the music..." (English passage) |
| T4 | Speaker + fan + conversation | Both T2 + T3 inputs | Fixed 30s passage | "Please turn down the music..." (English passage) |
| T5 | Continuous 10min with bursts | Fan + occasional speech | Same passages | Same passages |
| T6 | Speaker near mic | Very loud/close second speaker | Fixed 30s passage | "Please turn down the music..." (English passage) |

## 6. Comparison Method

For all A/B comparisons:

1. Freeze one immutable 48 kHz mono source clip/hash and the actual spoken references for its scored interval, including repetitions.
2. Process identical source bytes through each mode with independent/reset state and identical ASR model revision/settings; document alignment, drops and gaps.
3. Attribute background transcript words by contextual alignment and audio review; mark ambiguous words separately.
4. Compute background intrusion rate = `100 × background-attributable words / fixed background reference words (N_bg)`, never divided by output length. No background speech means N/A; Raw with no intrusions is a floor effect, not proof of improvement.
5. Assess primary retention separately = `100 × correctly retained primary reference tokens / fixed primary reference words (N_primary)`, matching each reference token once. Compare against Raw and listen for intelligibility/normal phrase erasure; the PRD defines no 90% cutoff.
6. Apply scenario criteria across audio, intrusion rate and primary retention together using [the shared protocol](../acceptance.md#shared-comparison-and-scoring-protocol).

**Fairness requirement:** Same recorded clip and ASR settings. Back-to-back live takes are exploratory only and cannot replace same-recorded-input comparative acceptance; without replay, comparative acceptance remains **NOT RUN**. Live switching checks establish lifecycle behavior separately.

## 7. Latency / Timing Collection Points

| Stage | Metric | Collection Method |
|-------|--------|-------------------|
| Capture → display | End-to-end partial-text delay | Timestamp frame capture, timestamp transcript display |
| RNNoise | Per-frame processing time (avg, p95) | Instrument wrapper |
| Hush | Per-frame processing time (avg, p95) | Instrument wrapper |
| ASR | Partial-to-final delay | Timestamp ASR events |
| Pipeline | Dropped samples / late frames | Count loss separately at source/ASR boundaries and record gap resets; late means >100 ms at DSP dequeue per architecture |
| Pipeline | Queue depth | Sample at regular intervals |
| System | Memory (RSS) | Sample at 30-second intervals |

Zero dropped frames is aspirational; the PRD has no binding numeric drop threshold. T5 still requires no crash, runaway memory, stuck queue or severe latency growth. Offline timing and mock queues do not establish live latency or the human ten-minute stress result.

## 8. Qualitative Evaluation Criteria

These are observed acceptance criteria evaluated by the human tester during H0–H3. The PRD does not define numeric targets for:

- Primary speech intelligibility
- Subjective responsiveness (record alongside the separate numeric P-01 target of ≤1.5 s)
- UI clarity (mode labels, error messages)
- Error message helpfulness

Record observations in the Feedback Record sections of each checkpoint document.

## 9. Honest Limitations

The following are **known limitations** per the PRD. They must be documented in final results, not masked:

1. **Hush is not speaker identification.** Closest/loudest speaker assumption (PRD §4).
2. **Loud interferer (T6)** is a documented failure case (PRD §16).
3. **Resampling artifacts** possible at RNNoise→Hush boundary (PRD §16).
4. **No perfect source separation** — this is explicitly a non-goal (PRD §3.2).
5. **Mobile optimization** is out of scope (PRD §3.2).
6. **ASR is secondary** — filtering quality is the comparison, not ASR accuracy (PRD §8).

## 10. Prescribed Launch and Verification Boundary

Architecture contract v1 and `docs/plans/m0-baseline.md` prescribe exact M0 setup, launch and real-ASR smoke commands, reproduced in [H0](../checkpoints/H0-baseline.md). They are **NOT YET VERIFIED**, not evidence that M0 exists. The implementation README/handoff must supply actual verified setup results; later filter/replay commands belong to the corresponding implementation handoffs.

H0 uses native macOS permission for the launching Orca/Terminal/Python host/process. Capture opens only after Start, never at service/page load or device enumeration; device changes and Clear are idle-only. No browser microphone permission or silent device/rate fallback is prescribed. Recording is off by default; explicit opt-in with `--dev-recording` produces only raw/asr-input WAVs in M0.

Deterministic tests assert architecture contracts: 480-sample 48 kHz RNNoise frames/scaling, one stateful resampling boundary, 160-sample 16 kHz Hush hops, metadata/duration/reset semantics, bounded queues and serialized mode epochs. Mocks verify wiring only; neither nonzero mock output nor a correctly shaped real frame proves useful suppression.

## 11. Coordination Notes

- Architecture worker (Codex) owns interfaces, contracts, and technical decisions.
- This reconciliation owns only docs/acceptance.md, the four H0–H3 checkpoint documents, docs/handoffs/acceptance-plan.md and docs/handoffs/checkpoint-reconciliation.md.
- Do not modify architecture docs, code, dependencies, or progress.md.
- This task is document reconciliation only: do not run setup, launch, model or microphone commands; keep every product test NOT RUN.
- No subagents, no code, no microphone recording, no pushes or unrelated edits.
