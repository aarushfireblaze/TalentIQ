# H0 — Baseline Checkpoint: Raw Mic + Live ASR

Status: **NOT RUN**
Depends on: M0 completion (architecture contracts + implementation)
Blocks: H1, H2, H3

---

## 1. Objective

Establish a known-working baseline: microphone capture → raw audio → ASR → live transcript UI. No filtering. This checkpoint proves the end-to-end plumbing works before any noise suppression is added.

## 2. What H0 Validates

| Requirement | Validated? |
|-------------|------------|
| FR-01 — Microphone capture | NOT RUN |
| FR-02 — Canonical audio format | NOT RUN |
| FR-05 — Streaming ASR | NOT RUN |
| FR-06 — Real-time UI | NOT RUN |
| FR-07 — Bypass modes (Raw only at this stage) | NOT RUN |
| FR-08 — Error handling | NOT RUN |
| P-01 — Perceived latency ≤ 1.5 s | NOT RUN |
| P-06 — CPU-only operation | NOT RUN |

## 3. Human Test Script

### Launch

**Note:** Exact launch commands depend on architecture decisions (not yet finalized). This checkpoint will be updated with concrete commands after architecture handoff. The expected launch source is `README.md` in the repo root.

1. Open terminal in the project directory.
2. Follow README setup instructions (to be provided by architecture worker).
3. Launch the application.
4. Open the UI in a browser or desktop window.

### Test Steps

| Step | Action | Expected Result | Status |
|------|--------|----------------|--------|
| 1 | Grant microphone permission when prompted | App gains mic access; no error | NOT RUN |
| 2 | Select microphone input device from dropdown | Correct device is selected | NOT RUN |
| 3 | Press Start | Status changes to "Listening"; level meter activates | NOT RUN |
| 4 | Observe live input level meter while speaking | Meter moves in response to voice (only after Start) | NOT RUN |
| 5 | Speak a short passage (30 seconds): "The quick brown fox jumps over the lazy dog. She sells seashells by the seashore. The rain in Spain stays mainly in the plain." | Transcript appears in the panel as you speak | NOT RUN |
| 6 | Stop speaking for 10 seconds | Transcript pauses; no runaway text | NOT RUN |
| 7 | Observe transcript latency | Text appears within ~1.5 seconds of speech | NOT RUN |
| 8 | Press Stop | Status changes to "Idle"; final transcript remains visible | NOT RUN |
| 9 | Click Copy Transcript | Transcript text is copied to clipboard | NOT RUN |
| 10 | Paste into a text editor and verify | Full transcript text is pasted | NOT RUN |
| 11 | Click Clear Transcript | Transcript panel is emptied | NOT RUN |
| 12 | Restart recording (press Start again) | New session begins cleanly | NOT RUN |
| 13 | Speak for 30 seconds, then stop | Second transcript is correct | NOT RUN |
| 14 | Check developer panel (if available) for latency metrics | Per-frame timing and queue depth are displayed | NOT RUN |

### Error Scenarios

| Step | Action | Expected Result | Status |
|------|--------|----------------|--------|
| E1 | Deny microphone permission at launch | Error message: "Microphone permission denied" (FR-08) | NOT RUN |
| E2 | Disconnect microphone during recording | Error message indicating device failure (FR-08) | NOT RUN |
| E3 | Select incompatible audio device | Error or graceful fallback with message | NOT RUN |

## 4. Automated Plumbing Tests

These verify wiring, not real audio quality.

| Test | What it checks | Status |
|------|---------------|--------|
| Unit: AudioSource emits frames | Mock mic source produces timestamped PCM frames | NOT RUN |
| Unit: Transcriber accepts frames | Transcriber interface receives audio and emits TranscriptEvents | NOT RUN |
| Unit: Pipeline starts and stops | PipelineController transitions through Idle→Listening→Idle | NOT RUN |
| Integration: Frame flow end-to-end | Raw mode: mock source → pipeline → transcriber → event stream | NOT RUN |
| Unit: Error events surface | Missing mic permission triggers error event | NOT RUN |

## 5. Pass Criteria

**Binding pass criteria (must pass for H0 to pass):**
- Mic capture works on the target laptop after pressing Start.
- Transcript appears in the UI during recording.
- No crashes during start/stop/restart cycle.
- Copy and Clear transcript controls function.
- Error messages appear for permission denial and device failure.

**Desired targets (measured relative to raw baseline; not hard pass/fail gates):**
- Transcript latency feels live (target ≤ 1.5 s; PRD P-01).
- Primary speech retention is comparable to raw input (no aggressive word erasure).
- Developer panel shows timing metrics (if implemented).

Note: PRD T1 does not demand zero dropped words or zero dropped frames. Retention is compared relative to the raw baseline — filtered modes should preserve primary speech at a rate comparable to raw.

## 6. Known Limitations at This Stage

- No filtering is active; raw audio goes straight to ASR.
- Background noise and competing speakers will produce poor transcript quality — this is expected and will be addressed in H1/H2.
- ASR quality depends on the chosen model; raw baseline transcript is the comparison reference for later checkpoints.

## 7. Feedback Record

| Date | Tester | Feedback | Action Taken |
|------|--------|----------|--------------|
| — | — | — | — |
