# Acceptance Plan — Handoff Document

Status: **NOT RUN**
Owner: OpenCode MiMo v2.5 (acceptance/checkpoint worker)
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

## 3. Execution Order

```
Architecture contracts (Codex) ──→ M0 implementation ──→ H0 (human gate)
                                                            │
                                                    M1 implementation ──→ H1 (human gate)
                                                            │
                                                    M2–M3 implementation ──→ H2 (human gate)
                                                            │
                                                    M4–M6 implementation ──→ H3 (human gate)
                                                            │
                                                    M7 ──→ Final acceptance
```

**Human gates require actual user feedback.** Automated tests never count as the user trying the product.

## 4. Test Type Classification

| Category | Examples | What they prove | Limitation |
|----------|----------|----------------|------------|
| Automated plumbing | Unit tests for wrappers, pipeline start/stop, mode switching | Wiring is correct; interfaces work | Do NOT prove real filtering, ASR accuracy, or latency |
| Real model tests | RNNoise on noise WAV, Hush on speech WAV | Models load and produce output | Do NOT prove real-time performance or user experience |
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

1. Record or replay the same audio clip through each mode.
2. Transcribe with the same ASR model.
3. Count background-attributable words using reference passage matching.
4. Count primary-attributable words.
5. Compute background % = (background words / total words) × 100.
6. Compare across modes.

**Fairness requirement:** Same clip, same ASR, same conditions. When live replay is not available, back-to-back recordings with held-constant conditions are acceptable (noted as limitation).

## 7. Latency / Timing Collection Points

| Stage | Metric | Collection Method |
|-------|--------|-------------------|
| Capture → display | End-to-end partial-text delay | Timestamp frame capture, timestamp transcript display |
| RNNoise | Per-frame processing time (avg, p95) | Instrument wrapper |
| Hush | Per-frame processing time (avg, p95) | Instrument wrapper |
| ASR | Partial-to-final delay | Timestamp ASR events |
| Pipeline | Dropped/late frames | Count frames past deadline in ring buffer |
| Pipeline | Queue depth | Sample at regular intervals |
| System | Memory (RSS) | Sample at 30-second intervals |

## 8. Qualitative Evaluation Criteria

These are observed acceptance criteria evaluated by the human tester during H0–H3. The PRD does not define numeric targets for:

- Primary speech intelligibility
- Transcript "liveness" (subjective impression of responsiveness)
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

## 10. README as Launch Source

Exact startup commands, dependencies, and setup steps will be defined in `README.md` by the architecture/implementation workers. This acceptance plan links to README as the canonical launch source. Human test scripts will be updated with concrete commands after architecture contracts are finalized.

## 11. Coordination Notes

- Architecture worker (Codex) owns interfaces, contracts, and technical decisions.
- Acceptance worker (this worker) owns only docs/acceptance.md, docs/checkpoints/*.md, and docs/handoffs/acceptance-plan.md.
- Do not modify architecture docs, code, dependencies, or progress.md.
- Do not run startup commands until architecture is known.
- No subagents, no code, no microphone recording, no pushes or unrelated edits.
