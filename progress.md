# Voice filtering project progress

Updated: 2026-09-18. This is the current handoff for the user's manual-worktree workflow. Detailed earlier history remains in Git before this revision and in `docs/handoffs/`.

## Current state

- **H0 approved. H1 failed and awaits repair plus a user retest. M2 is held.** Automated tests cannot approve a human checkpoint.
- Main branch HEAD before this documentation update: `dc5002c`. Latest integrated application change: `92174ba` (transcript history). Resampler metadata repairs are integrated as `dc871a8`, `bb0f6c9`, and `5805856`. Their focused and full test results establish plumbing, not filtering quality. See `docs/handoffs/h1-service-history.md` and `docs/handoffs/h1-resampler.md`.
- Initial H1 controls/ASR/RNNoise/controller repair is commit `3419488` in `voice-m1-rnnoise`; it is **not integrated**. Its reported 112 passing tests predate the unfinished changes below. No current H1 repair has accepted final tests, real suppression evidence, or browser retest.
- The server at `http://127.0.0.1:8765/` was started before these child repairs. Restart after integration before treating it as a preview. Do not assume its process is still running.
- H1 user feedback: Raw and RNNoise looked simultaneously active and could not be selected reliably. Background talking produced random transcript text; clear near-microphone speech was recognized. The user has **not** tested fan or typing noise without speech. Native RNNoise execution was observed, but useful suppression was not established. RNNoise is not the planned competing-speaker filter; Hush and Combined are unavailable.

## Existing worktrees: use these, create no replacements

Each worktree has uncommitted edits. Open one fresh agent chat inside each existing worktree. Prefer Antigravity Pro for coding. Give each chat this file, its local diff, and only its task below. The user manually assigns tasks and decides when to integrate; agents do not start coordination runs or edit each other's files.

| Worktree / suggested display name | Current state | Task and owned files |
|---|---|---|
| `voice-m1-rnnoise` / **H1 controls** | HEAD `3419488`; uncommitted `apps/ui/app.js`, `src/voice_filtering/pipeline/controller.py`, `tests/test_rnnoise.py` | Finish selected/pending Raw–RNNoise UI confirmation, network recovery, controller reselect/cancellation regression tests, and same-input replay/native evidence. Own only those files plus a necessary replay script and `docs/handoffs/h1-regressions.md`. Do not edit ASR, service, or resampler. |
| `voice-h1-resampler` / **H1 ASR race** | HEAD `ee160b1`; uncommitted `src/voice_filtering/asr/whisper.py`, `tests/test_asr.py`; untracked scratch `fix_test.py` | Finish reset-safe frame/provenance checks, immutable decode context, atomic post-decode acceptance, and blocking-decode concurrency tests. Own only the ASR files and `docs/handoffs/h1-asr-provenance.md`. Do not execute or commit the scratch helper without inspection. Do not edit UI, controller, service, or resampler. The worktree name is historical; do not move or replace it while dirty. |

Existing worktree paths are under `/Users/aarushgupta/orca/workspaces/TalentIQ - Background filtering + AI transcribe/`. Paused backups against each child's own HEAD are in `docs/handoffs/pause-2026-09-18/`. Original edits remain in the worktrees; do not blindly apply backups to main.

The ASR draft captures PCM/session/epoch/mode/start time under a lock, decodes outside it, then checks provenance and queues accepted events atomically. This is **unverified**. Check old local-batch frames after reset, session changes, mixed stale/fresh frames, finish context and partial duration, and callback acceptance boundaries. The controls draft has pending-state polling and cancellation changes; it is also **unverified**.

## Finish H1

1. Have each worktree agent finish only its task, run focused tests and a final full suite, write its handoff, and commit only owned files. Do not claim acoustic or browser proof from unit tests.
2. Review both diffs. On main, integrate the logical H1 baseline `3419488` **once**, then the two follow-up fix commits. `ee160b1` is a cherry-pick of that baseline on the ASR worktree; do not apply it again. Resolve any conflicts using the reviewed file ownership, then run combined tests and native/model checks.
3. Restart the local service from the integrated version and inspect the browser. Prepare the [H1 script](docs/checkpoints/H1-static-noise.md): mode selection, noise-only fan/typing, near-microphone speech with noise, and same-recorded-input Raw/RNNoise comparison. Record timing and errors. Pause for the user's actual test and feedback.
4. Only after H1 feedback is accepted, consider one new worktree named `voice-m2-hush-offline` for deterministic Hush model validation. Do not start Hush or Combined implementation as part of the H1 repairs.

## Product constraints and checkpoints

The approved specification is `docs/requirements/Voice_Filtering_System_PRD.docx`, with searchable text beside it. Required final signal path: microphone, RNNoise, one explicit 16 kHz resampling boundary, Hush, replaceable local ASR, transcript UI. Never silently fall back to an unfiltered mode. Model versions are pinned. Normal operation is local; recording is off by default.

| Milestone | State | Human checkpoint |
|---|---|---|
| M0 Raw baseline | Integrated; H0 approved from user feedback | Mic, meter, transcription, Stop/restart worked; latency not formally measured |
| M1 RNNoise | Implemented; H1 failed/retest pending | Raw versus RNNoise under static noise and primary speech |
| M2 Hush offline | Held | Real model load, deterministic frame/output evidence |
| M3–M4 Hush streaming and Combined | Held | H2: near-field voice with distant competing speaker |
| M5–M6 evaluation and UX | Pending | H3: same clips across modes and ten-minute session |
| M7 final acceptance | Pending | T1–T6 evidence and known limits |

Human checkpoints require actual user feedback. At each one provide the launch command/URL, a short test script, known limitations, and a place to record feedback. Keep synthetic, real-model, and live-user evidence separate.
