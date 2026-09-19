# Voice filtering project progress

Updated: 2026-09-18. This is the current handoff for the user's manual-worktree workflow. Detailed earlier history remains in Git before this revision and in `docs/handoffs/`.

## Current state

- **H0 approved. H1 failed and awaits repair plus a user retest. M2 is held.** Automated tests cannot approve a human checkpoint.
- Main contains the manual-worktree documentation update `c0681cf`. Latest integrated application change: `92174ba` (transcript history). Resampler metadata repairs are integrated as `dc871a8`, `bb0f6c9`, and `5805856`. Their focused and full test results establish plumbing, not filtering quality. See `docs/handoffs/h1-service-history.md` and `docs/handoffs/h1-resampler.md`.
- Initial H1 controls/ASR/RNNoise/controller repair is commit `3419488` in `voice-m1-rnnoise`; it is **not integrated**. Its reported 112 passing tests predate the unfinished changes below. No current H1 repair has accepted final tests, real suppression evidence, or browser retest.
- The server at `http://127.0.0.1:8765/` was started before these child repairs. Restart after integration before treating it as a preview. Do not assume its process is still running.
- H1 user feedback: Raw and RNNoise looked simultaneously active and could not be selected reliably. Background talking produced random transcript text; clear near-microphone speech was recognized. The user has **not** tested fan or typing noise without speech. Native RNNoise execution was observed, but useful suppression was not established. RNNoise is not the planned competing-speaker filter; Hush and Combined are unavailable.

## New independent worktrees to create now

Create **two new worktrees from current `main`**, one fresh Antigravity Pro chat per worktree. These branches must first bring in the shared H1 baseline commit `3419488`, then port only relevant unfinished changes from the old worktree shown below. Do not assume uncommitted edits appear in a new worktree. Keep the old worktrees intact until the new agents have inspected and carried over their useful changes. Assign only the task below; agents do not edit each other's files or merge into `main`.

| New worktree | Agent task and owned files | Old worktree to read, not edit |
|---|---|---|
| `voice-h1-controls` | Cherry-pick `3419488`; port the relevant old uncommitted edits; finish selected/pending Raw–RNNoise UI confirmation, network recovery, controller reselect/cancellation tests, and same-input replay/native evidence. Own follow-up edits only in `apps/ui/app.js`, `src/voice_filtering/pipeline/controller.py`, `tests/test_rnnoise.py`, a necessary replay script, and `docs/handoffs/h1-regressions.md`. | `voice-m1-rnnoise`: HEAD `b927e31`; uncommitted UI/controller/test edits. |
| `voice-h1-asr` | Cherry-pick `3419488`; port the relevant old uncommitted edits; finish reset-safe frame/provenance checks, immutable decode context, atomic post-decode acceptance, and blocking-decode concurrency tests. Own follow-up edits only in `src/voice_filtering/asr/whisper.py`, `tests/test_asr.py`, and `docs/handoffs/h1-asr-provenance.md`. Do not execute or commit the old scratch helper without inspection. | `voice-h1-resampler`: HEAD `ea5e45f`; uncommitted ASR/test edits and untracked `fix_test.py`. |

Existing worktree paths are under `/Users/aarushgupta/orca/workspaces/TalentIQ - Background filtering + AI transcribe/`. Paused backups against each old worktree's earlier HEAD are in `docs/handoffs/pause-2026-09-18/`. Use the live old diff as the primary reference. Do not blindly apply backups to main.

The ASR draft captures PCM/session/epoch/mode/start time under a lock, decodes outside it, then checks provenance and queues accepted events atomically. This is **unverified**. Check old local-batch frames after reset, session changes, mixed stale/fresh frames, finish context and partial duration, and callback acceptance boundaries. The controls draft has pending-state polling and cancellation changes; it is also **unverified**.

## Finish H1

1. Each new agent finishes only its task, runs focused tests and a final full suite, writes its handoff, and commits only owned follow-up files. Do not claim acoustic or browser proof from unit tests.
2. When both agents finish, create one short-lived worktree `voice-h1-release` from current `main`. Its agent reviews both diffs, applies shared baseline `3419488` **once**, then applies only the two follow-up fix commits. `ee160b1` is another copy of the baseline; do not apply it again. Run combined tests and native/model checks. Keep the two task worktrees available for any fixes.
3. Run the local service from `voice-h1-release` and inspect the browser. Prepare the [H1 script](docs/checkpoints/H1-static-noise.md): mode selection, noise-only fan/typing, near-microphone speech with noise, and same-recorded-input Raw/RNNoise comparison. Record timing and errors. Pause for the user's actual test and feedback. Do not create a new worktree for each H1 bug; route fixes to the relevant task worktree.
4. After a new task branch's useful code and evidence are committed and reviewed, remove its old source worktree only when no unique uncommitted files remain. After the user accepts H1 and the release branch is integrated, remove the three new H1 worktrees once each is clean and all commits are retained. Only then create `voice-m2-hush-offline` from updated `main` for deterministic Hush validation. Never force-remove a dirty worktree.

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
