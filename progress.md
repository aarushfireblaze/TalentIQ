# Voice filtering: worktree plan and progress

Updated: 2026-09-19. This is the only active task board. Approved requirements: `docs/requirements/Voice_Filtering_System_PRD.docx` and its searchable `.txt` copy. `README.md` has setup; `AGENTS.md` has standing agent rules. Older plans and handoffs remain in Git history.

## Worktree rules

The user creates and assigns each worktree. Give one agent one task ID below and start a fresh chat in that worktree. Agent reads `AGENTS.md`, this task, cited PRD sections, and relevant code. Agent owns only listed follow-up files. No agent creates worktrees, delegates, merges into `main`, edits this board, or approves a human checkpoint. User updates states here after reviewing commits and evidence. Agent reports commit, exact verification results, real-model or live evidence, and blockers in final chat. Store large generated evidence under gitignored `artifacts/` and report its path.

For coding tasks, run focused tests while editing; run one full suite and `pip check` on the final snapshot. Record `git status --short`. Mock tests cannot prove filtering quality. No two active agents edit the same files. Start each task only after its prerequisite. Route user-reported defects to the owning task worktree; integrate only reviewed commits.

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m pip check
```

## Current state

H0 received user approval on 2026-09-18. Live latency was not formally measured. M1 RNNoise code exists on `main`; H1 failed its first user test. Raw and RNNoise appeared active together and could not be selected reliably. Background speech produced random transcript text; clear near-microphone speech was recognized. Fan/typing noise without speech and same-input Raw/RNNoise comparison were **NOT RUN**. Native RNNoise executed, but useful suppression is **not established**. Competing-speech suppression belongs to later Hush work. M2 and later integration remain held.

`main` points to `1446da4` at this update. H1 baseline repair commit `3419488` is **not on main**. Branches `voice-m1-rnnoise` (`b927e31`) and `voice-h1-resampler` (`ea5e45f`) remain in Git, but their old worktree folders are gone. Unfinished edits survive under `docs/handoffs/pause-2026-09-18/` as draft patches and status text. Inspect before porting; never apply an entire draft blindly. `docs/handoffs/h1-paused-worktree.patch` is an older mixed draft. `ee160b1` duplicates baseline `3419488`; never integrate both.

### Worktrees to create now

| Task | Suggested worktree | Start after | State |
|---|---|---|---|
| H1-A | `voice-h1-controls` | Now, from current `main` | Done |
| H1-B | `voice-h1-asr` | Now, from current `main` | Done |
| H1-C | `voice-h1-release` | H1-A and H1-B committed and reviewed | Ready to start |
| H1 user retest | No coding worktree | H1-C launch and evidence ready | Waiting |

### H1-A: controls, controller, RNNoise evidence

Create branch from current `main`; cherry-pick `3419488` into this isolated branch. Read `docs/handoffs/pause-2026-09-18/voice-m1-rnnoise.patch` and matching status text. Port only useful unfinished changes after checking current code. Baseline touches shared files; follow-up ownership is `apps/ui/app.js`, `src/voice_filtering/pipeline/controller.py`, `tests/test_rnnoise.py`, and `scripts/replay_ab.py` only if replay needs repair. Report any necessary edit outside those paths before making it.

Deliver one clearly selected Raw or RNNoise mode; visible pending state until a switch applies at a frame boundary; same-mode reselect and queued-switch cancellation; network/command recovery; SSE reconnect from authoritative snapshot. Old-epoch transcripts must retain old mode labels. Stage failure must show an error without Raw fallback. Add focused lifecycle tests. Run native RNNoise and same-48 kHz-WAV Raw/RNNoise replay; report fixture hash, library/model identity, settings, output paths, timing and errors. If acoustic proof is unavailable, mark it **NOT RUN**. Read PRD §§5–7, 9–11, 14 M1 and 16. Exit with focused tests, final full suite, `pip check`, commit and evidence report. H1 remains pending.

### H1-B: ASR frame provenance and decode concurrency

Create branch from current `main`; cherry-pick `3419488` into this isolated branch. Read `docs/handoffs/pause-2026-09-18/voice-h1-resampler.patch` and matching status text. Port only useful unfinished changes. Do not execute old scratch helper `fix_test.py` without inspection. Follow-up ownership: `src/voice_filtering/asr/whisper.py` and `tests/test_asr.py`.

Reject stale or mixed session/epoch frames before ingest. Preserve mode, timing and valid-sample provenance through reset, finish and partial/final emission. Capture immutable decode context under lock, decode outside lock, then validate provenance and accept/publish atomically. A blocked decode followed by reset, switch, Stop or restart must not publish into a new context. Add deterministic blocking-decode and mixed-frame tests; preserve bounded queues and errors. Read PRD §§6–9, 11 and 14 M1. Exit with focused tests, final full suite, `pip check`, commit and evidence report. H1 remains pending.

### H1-C: integrate and prepare retest

Create from current `main` only after H1-A and H1-B commits are reviewed. Apply shared baseline `3419488` **once**, then only reviewed follow-up commits. Resolve overlap explicitly. Do not apply `ee160b1` or whole draft patches. Own only integration conflicts and narrow cross-component tests. Record input commits. Run full suite, `pip check`, native RNNoise/model checks and same-input replay on this exact snapshot. Launch service from this worktree and inspect browser at `http://127.0.0.1:8765/`; restart any older server on that port first. Report launch command, integration commit, evidence paths and limits. Integration into `main` requires user assignment.

For H1 retest, user checks one selected mode, Raw-to-RNNoise-to-Raw switching, Stop/restart, network/error recovery, fan/HVAC and typing with and without near-microphone speech. Compare Raw/RNNoise on one immutable 48 kHz mono recording; separate live takes are exploratory. Record aligned audio/transcripts, primary retention, processing time, gaps/drops, fixture hash and model/settings. H1 stays **pending** until user explicitly accepts it.

## Later worktrees, in order

Create each after its stated gate, from latest user-approved integrated `main`. Names are suggestions. Each is one bounded assignment. Sequential tasks may own the same files at different times; never concurrently.

| Task / suggested worktree | Start after | Agent assignment and exit evidence | State |
|---|---|---|---|
| M2 `voice-m2-hush-offline` | H1 accepted and integrated | Build isolated Hush adapter and deterministic 16 kHz WAV harness. Own new `src/voice_filtering/audio/hush.py`, Hush tests and setup/fixture scripts; no controller/UI edits. Pin `weya-ai/hush` revision `a55d932cbf6344d284ac985f21e7f6e5bc4d38a5` and native source commit `9f6414e91461a8f4bdf9840c0cdcdcb7da986339`. Verify artifact SHA256, arm64 linkage/load, C ABI, 160-sample hop, finite output, reset/flush, measured alignment/timing and license notices. Real native inference plus focused/full tests required. | Held |
| M3 `voice-m3-hush-stream` | M2 reviewed and integrated | Add Hush-only live path through one stateful 48-to-16 kHz conversion. Own Hush follow-up, controller/service and integration tests. Preserve timing, epochs, 160-sample hops, bounded queues, explicit errors and metrics. Show live mode, deterministic replay, real timing and focused/full tests. | Held |
| M4 `voice-m4-combined` | M3 reviewed and integrated | Add Combined path: 48 kHz capture, RNNoise, **one** 16 kHz conversion, Hush, ASR. Own controller/service/UI and integration tests in this sequential worktree. Reset stage/provenance on mode switch; no silent fallback. Show same-input four-mode replay, measured alignment, drops, real models and focused/full tests. Prepare H2. | Held |
| H2 user test | M4 reviewed, integrated and launched | User checks near primary speech plus second speaker 3–6 feet away at lower/moderate volume; mixed fan and conversation; live switching and same-input four-mode comparison. Record background intrusions and primary retention separately. User accepts or assigns repairs before M5. | Held |
| M5 `voice-m5-evaluator` | H2 accepted and integrated | Build repeatable A/B evaluator in `scripts/` and evaluator tests. Feed one immutable 48 kHz source through four independent/reset paths with identical ASR settings. Save aligned WAVs/transcripts, hashes, model versions, timings, gaps/drops and scoring inputs. Reproduce T1–T4 reports; focused/full tests. | Held |
| M6 `voice-m6-ux-stability` | M5 reviewed and integrated | Harden existing device selector, status/errors, copy/clear, recording opt-in and recovery. Own UI/service and tests sequentially. Instrument actual 10-minute live run: memory, queues, drops, late frames, partial latency and stage p95. Focused/full tests and run report prepare H3. | Held |
| H3 user test | M6 reviewed, integrated and launched | User runs T1–T6 on final four-mode snapshot, including 10-minute session. Record feedback and route repairs before M7. | Held |
| M7 `voice-m7-acceptance` | H3 accepted and integrated | Verify clean setup, exact launch, T1–T6, model/license notices, known limits and all PRD §15 criteria. Own `README.md` and final evidence artifacts; user records final state on this board. Full suite, `pip check`, real/live evidence and user sign-off. | Held |

## Copy-paste prompts for worktree agents

Create the named worktree yourself, open a fresh agent chat inside it, and paste its prompt. Give an agent only one prompt. H1/H2/H3 user tests have no agent prompt. Do not start a held task before its gate passes.

### H1-A — `voice-h1-controls` (create now)

```text
You own task H1-A in this worktree. Read AGENTS.md, the H1-A and Shared acceptance rules sections of progress.md, and the cited PRD sections. Start from main, cherry-pick 3419488, then inspect docs/handoffs/pause-2026-09-18/voice-m1-rnnoise.patch; port only useful draft changes. Finish Raw/RNNoise selection, pending switch state, cancellation, network recovery, controller tests, and real native/same-input replay evidence. Follow H1-A file ownership. Run focused tests, one final full suite, and pip check. Commit your work and report commit IDs, exact test results, evidence paths, and blockers. Do not edit progress.md, merge into main, or claim H1 passed.
```

### H1-B — `voice-h1-asr` (create now)

```text
You own task H1-B in this worktree. Read AGENTS.md, the H1-B and Shared acceptance rules sections of progress.md, and the cited PRD sections. Start from main, cherry-pick 3419488, then inspect docs/handoffs/pause-2026-09-18/voice-h1-resampler.patch; port only useful draft changes. Fix ASR frame provenance and decode/reset concurrency only in H1-B owned files, with deterministic blocking-decode tests. Run focused tests, one final full suite, and pip check. Commit your work and report commit IDs, exact test results, evidence paths, and blockers. Do not edit progress.md, merge into main, or claim H1 passed.
```

### H1-C — `voice-h1-release` (after H1-A and H1-B review)

```text
You own task H1-C in this worktree. Read AGENTS.md, the H1-C and Shared acceptance rules sections of progress.md, and the reviewed H1-A/H1-B diffs. Start from current main. Apply baseline 3419488 once, then only the two reviewed follow-up commits; do not apply duplicate ee160b1 or draft patches. Resolve integration overlap, run the final full suite and pip check, verify native RNNoise and same-input replay, then launch and inspect this exact build in the browser. Report applied commits, commands, results, evidence paths, and remaining limits. Prepare the H1 user retest, but do not merge into main, edit progress.md, or claim H1 passed.
```

### M2 — `voice-m2-hush-offline` (after H1 acceptance)

```text
You own task M2 in this worktree. Read AGENTS.md, the M2 row and Shared acceptance rules in progress.md, PRD sections 4, 6–7, 9–11, 14 M2, and 16. Build only the isolated offline Hush adapter and deterministic 16 kHz fixture tests. Verify the pinned native artifact, ABI, 160-sample hop, actual inference, reset/flush, alignment, timing, and license notices. Do not edit controller or UI. Run focused tests, one final full suite, and pip check. Commit and report exact native evidence, test results, commit, and blockers. Do not edit progress.md or merge into main.
```

### M3 — `voice-m3-hush-stream` (after M2 integration)

```text
You own task M3 in this worktree. Read AGENTS.md, the M3 row and Shared acceptance rules in progress.md, PRD sections 5–7, 9, 11, 14 M3, and 16. Add Hush-only live streaming with one stateful 48-to-16 kHz boundary, 160-sample hops, bounded queues, timing/epoch preservation, stage metrics, and explicit failures. Stay within the M3 owned area. Prove deterministic replay and real-model timing; run focused tests, one final full suite, and pip check. Commit and report evidence, test results, commit, and blockers. Do not edit progress.md or merge into main.
```

### M4 — `voice-m4-combined` (after M3 integration)

```text
You own task M4 in this worktree. Read AGENTS.md, the M4 row and Shared acceptance rules in progress.md, PRD sections 5–7, 9–11, 14 M4, and 16. Add Combined live mode in the required RNNoise, single resampling boundary, Hush, ASR order. Update controller, service, UI, and integration tests; preserve mode provenance and explicit failure states. Show real-model, same-input four-mode replay with measured alignment and drops. Run focused tests, one final full suite, and pip check. Commit and report evidence, test results, commit, and blockers. Prepare H2 for the user; do not edit progress.md, merge into main, or claim H2 passed.
```

### M5 — `voice-m5-evaluator` (after H2 acceptance)

```text
You own task M5 in this worktree. Read AGENTS.md, the M5 row and Shared acceptance rules in progress.md, PRD sections 9–11 and 14 M5. Build a reproducible four-mode A/B evaluator for the same immutable 48 kHz source with reset paths and identical ASR settings. Save aligned audio, transcripts, hashes, model versions, timing, gaps/drops, and scoring inputs for T1–T4. Keep edits in evaluator scripts and tests unless a concrete integration need is reported. Run focused tests, one final full suite, and pip check. Commit and report reproducible commands, results, evidence paths, and blockers. Do not edit progress.md or merge into main.
```

### M6 — `voice-m6-ux-stability` (after M5 integration)

```text
You own task M6 in this worktree. Read AGENTS.md, the M6 row and Shared acceptance rules in progress.md, PRD sections 5–6, 9–11, and 14 M6. Harden device selection, status/errors, copy/clear, recording opt-in, and recovery in the existing UI/service. Run and measure a real 10-minute live session: memory, queue depths, drops, late frames, partial latency, and stage p95. Run focused tests, one final full suite, and pip check. Commit and report commands, test and live-run results, evidence paths, and blockers. Prepare H3 for the user; do not edit progress.md, merge into main, or claim H3 passed.
```

### M7 — `voice-m7-acceptance` (after H3 acceptance)

```text
You own task M7 in this worktree. Read AGENTS.md, the M7 row and Shared acceptance rules in progress.md, and PRD sections 10, 14–16. Verify clean local setup and exact startup commands; consolidate T1–T6 results, model/license notices, known limitations, and every PRD definition-of-done item. Update README.md and final evidence only. Run the final full suite and pip check, then report exact commands, results, real/live evidence paths, commit, and remaining blockers. The user records final progress and sign-off. Do not edit progress.md, merge into main, or claim a user checkpoint passed without user feedback.
```

## Shared acceptance rules

**Pipeline:** Raw = capture to 16 kHz ASR; RNNoise = 48 kHz RNNoise then 16 kHz ASR; Hush = 16 kHz Hush then ASR; Combined = RNNoise, one explicit 16 kHz conversion, Hush, ASR. Capture never waits on ASR or UI. Recording is off by default; normal use is local. Missing models, incompatible devices/rates and stage failures must show errors. Hush assumes intended speaker is nearest/loudest; it does not verify identity.

**Fair comparison:** T1–T4 require the same immutable 48 kHz mono clip per compared mode, independent/reset state and identical ASR revision/settings. Record hash, device/OS processing, rates, measured alignment delay, gaps/drops, exact primary/background reference transcripts and scored interval. H1 needs Raw/RNNoise replay before M5; H2 needs all four modes after M4. Live re-speaking tests usability only. Without replay, comparative acceptance is **NOT RUN**.

**Scores:** Freeze reference words before scoring. Background intrusion rate = `100 × attributable background output words / fixed background reference words`; N/A without background speech and may exceed 100% on repeated ASR words. Primary retention = `100 × correctly retained primary reference words / fixed primary reference words`; compare against Raw and listen for erased phrases. Review ambiguous words. If Raw has zero background intrusions, obtain another clip before claiming improvement. PRD has no 90% retention cutoff, numeric intrusion reduction or binding dropped-frame threshold. Partial-text delay target is ≤1.5 s; a 10-minute run must have no crash, runaway memory, stuck queue or severe latency growth.

**Scenarios:** T1 quiet primary speech: Combined preserves Raw-like intelligibility. T2 primary plus fan/HVAC/typing: RNNoise/Combined reduce noise without speech damage. T3 primary near mic plus distant competing speech: Hush/Combined reduce background words. T4 mixed static noise and conversation: Combined strongest overall, with primary retention. T5 ten minutes intermittent speech/noise: measure stability, queues, memory and latency. T6 loud/close interferer: document Hush failure honestly as a known limitation.

**Evidence types:** Fake-source tests prove interface/concurrency only; native checks prove actual load/inference on this host; same-input replay proves controlled comparison; human tests prove device permission, perceived quality, UI behavior and checkpoint acceptance. Record these separately. H0 approved. H1, H2 and H3 need actual user feedback.

## Milestone ledger

| Milestone | Result | Blocker |
|---|---|---|
| M0 / H0 | M0 integrated; H0 user approved | Live latency not formally measured. |
| M1 / H1 | M1 code integrated; H1 failed first test | H1-A/B/C repairs, same-input proof and user retest pending. |
| M2 | Held | H1 acceptance and real offline Hush proof. |
| M3–M4 / H2 | Held | M2, streaming Hush, Combined and user test. |
| M5–M6 / H3 | Held | H2, evaluator, stability and user test. |
| M7 | Held | H3 and final T1–T6 evidence. |

User updates a task state with date, commit, exact final test result, real/live evidence path, blocker and checkpoint decision. Never convert **NOT RUN** to passed without required evidence.
