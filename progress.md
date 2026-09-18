# Voice filtering project progress

Updated: 2026-09-18 (M1 integrated; H1 ready for human test)

## Authority and scope

The supplied PRD is the product specification: `docs/requirements/Voice_Filtering_System_PRD.docx`, with a complete text extraction beside it. The user authorized delegated implementation and asked for opportunities to test during development. The coordinator owns sequencing, decisions, review and this ledger; child agents own all program code and fixes.

Orca run: `run_74849e16ac93`. Initial repository commit: `e8bfca3`.

Required final order: microphone → RNNoise → one explicit 16 kHz resampling boundary → Hush → replaceable local ASR → transcript UI. No silent filter fallback. Model versions must be pinned. No recruiting features, cloud accounts, or public deployment.

## Milestones and human checkpoints

| Milestone | Deliverable | State | Human test |
|---|---|---|---|
| Architecture | Interfaces, dependency feasibility, scoped implementation briefs | Complete: `dace574` | No extra approval required for the supplied PRD |
| M0 | Raw mic, level meter, optional WAV, local ASR and transcript UI | Integrated and independently reviewed; H0 feedback approved | H0 recorded: mic, meter, live transcription, Stop/restart; latency remains unmeasured |
| M1 | RNNoise wrapper and live mode | Integrated at `dd347f5`; follow-up fixes `9bda8c0`, `3f5cedf`, `b65db6d`, `d0731ba`, `eda5c94`; native load smoke and 96-test suite pass | H1: compare raw vs RNNoise with fan/typing and primary voice |
| M2 | Deterministic Hush offline validation | Pending; may proceed independently after contracts | Evidence of real model inference, sample/frame semantics and output shape |
| M3–M4 | Streaming Hush and Combined path | Held for earlier checkpoints | H2: near-field voice with distant competing speaker, switch modes live |
| M5–M6 | Four-mode A/B evaluation and stable UX | Pending | H3: same clips across modes plus 10-minute session |
| M7 | T1–T6 evidence and final acceptance | Pending H3 | Final review of measured results and known limits |

Human gates require actual user feedback; automated tests never count as the user trying the product. At each checkpoint provide exact launch commands/URL, a short test script, known limitations, and a place to record feedback. Pause dependent integration while awaiting feedback. Preparatory work may continue independently.

## Coordination rules

- User direction (2026-09-17): leave the two already-running architecture and acceptance workers in this main worktree. Every NEW agent must be placed in an Orca child worktree under this main worktree. Do not launch new agents here or reuse the existing main-worktree workers for new implementation tasks.
- Freeze interfaces before parallel component implementation. Never have two agents edit the same core pipeline files concurrently.
- Each implementation task supplies meaningful tests, exact verification commands/results, a concise handoff, and commits containing only its owned files.
- Independent review has two explicit verdicts: assigned specification compliance and code/test quality. Route fixes to an implementer.
- Synthetic or stub tests establish plumbing only; they cannot prove real filtering, ASR accuracy, microphone behavior, or latency targets.
- Recording remains off by default. Model downloads are setup steps; normal operation stays local.
- No worker spawns additional workers. No push, public deployment, destructive cleanup, or unrelated changes.
- Reuse a settled worker with relevant context when its terminal and worktree are genuinely available; create a fresh child only when reuse is unavailable or unsafe. Preferred worker routes are Antigravity Pro and OpenCode MiMo v2.5; use Codex only when necessary with the Sol model.

## Current work

- Read the entire PRD and preserved the original plus searchable text in the repository.
- Confirmed this is an empty initialized repository on an Apple Silicon host.
- Confirmed Orca is ready. Finished Voice Filtering child worktrees were removed after their commits were integrated; historical external worker rows remain retained by Orca and are not reused.
- Architecture/contracts: Codex worker `task_156f3abe0f98`, dispatch `ctx_50b6ce643017`; runtime reports `gpt-6-astra`.
- Acceptance and checkpoint documents: OpenCode MiMo v2.5 worker `task_7f021e921f2a`, current dispatch `ctx_31108db79ae7`. MiMo identity verified on the terminal display. Initial dispatch `ctx_6819e53540a5` lost its prompt to a startup update dialog and ended a turn without doing the task. Coordinator fenced that attempt and retried in the same terminal after the dialog cleared; the current worker was observed reading the PRD and preparing the assigned documents.
- M0 implementation task `task_4ab0a7f16863` completed and was independently reviewed in child worktrees; its code is integrated on `main` at `c2e5ea3` and the finished worktrees are cleaned up.
- H0 gate `gate_150349ca6493` was resolved as passed from the recorded user feedback on 2026-09-18; latency remains unmeasured.
- M1 task `task_64f8c2de368e` completed in OpenCode MiMo v2.5 child `voice-m1-rnnoise` as `ctx_a7544401b75b`; implementation commit `557fb29` is integrated at `dd347f5`. Follow-up regression fixes are integrated at `9bda8c0` (make `PipelineError` raisable) and `3f5cedf` (remove real-microphone dependency from controller tests). The child handoff is `docs/handoffs/m1-rnnoise.md`. The arm64 RNNoise dylib built from the pinned source, but the bounded ctypes smoke timed out; no real RNNoise filtering claim is made.
- Antigravity CLI was discovered as `agy`; `agy models` confirms `gemini-3.1-pro-high`. Architecture risk review is now assigned through Orca to Antigravity Pro in its own child worktree (details below).
- Next: present H1 Raw/RNNoise checkpoint and wait for user feedback. The local server is running at `http://127.0.0.1:8765` with RNNoise status Ready. Do not claim RNNoise quality from automated tests alone.

## Completed preparation

- Acceptance/checkpoint documentation delivered in commit `70e726a`. All product tests remain NOT RUN. The coordinator reviewed drafts and requested corrections to Start ordering, speaker passages and fair comparisons. Worker release returned `retained` because the MiMo terminal was externally created; it is settled and has no new task.
- Documentation issues corrected by the child reconciliation task: zero drops is aspirational, H2 follows both M3/M4, and only same-recorded-input comparisons establish comparative acceptance. See `docs/handoffs/checkpoint-reconciliation.md`.
- Architecture completed in `dace574`; accepted native sounddevice capture, a local Python/SSE service, static UI and pinned local CPU Whisper baseline. Candidate dependency pins still require installation validation. Architecture worker released after its valid completion report.
- M0 builder: OpenCode MiMo v2.5, child `voice-m0-baseline`, task `task_4ab0a7f16863`, dispatch `ctx_2f1bdc5e9fd4`; base `dace574`. Child path: `/Users/aarushgupta/orca/workspaces/TalentIQ - Background filtering + AI transcribe/voice-m0-baseline`.
- Checkpoint reconciliation: Codex, child `voice-checkpoint-docs`, task `task_8a6478c74e7b`, dispatch `ctx_e2a08871a62a`; owns only acceptance/checkpoint docs and its report. This worker is resolving the documentation issues above. Base `dace574`.
- All implementation and review worktrees were children of this main worktree. Finished children have been removed; only the active M1 child remains. H0 is approved from recorded user feedback; H1–H3 remain pending.
- Antigravity Pro architecture review: child `voice-architecture-review`, task `task_faa6f9b1a089`, dispatch `ctx_15e10bd924bc`; terminal display verified Gemini 3.1 Pro high. Owns only `docs/handoffs/architecture-review.md`; no application edits.
- Independent M0 specification/code review task `task_8510b5dc7853` completed in a child worktree with both verdicts PASS; its report is integrated in `docs/handoffs/m0-review.md`.
- Antigravity review delivered in child commit `85c8942`: PRD scope PASS; architecture readiness PASS WITH CONDITIONS. Report integrated into main. Conditions are measured noise-only behavior and short/full-window ASR timings, already routed to the M0 implementer. Static RMS gating is a known limitation; local hallucination/latency failure is not yet measured. Release returned retained/external-terminal; review task is settled.
- Checkpoint reconciliation completed in child commits `a0927ec` and `59fb245`, reviewed and integrated into main. Documentation checks cover table/fence/link integrity, exact H0 commands and unrun product status. H0 is now passed from recorded user feedback; H1–H3 remain pending.

## Latest worker completion and resume handoff

- M0 worker report (`ctx_2f1bdc5e9fd4`, task `task_4ab0a7f16863`) says the implementation is committed as `b5e48d5` on branch `voice-m0-baseline`, based on `dace574`, in child worktree `/Users/aarushgupta/orca/workspaces/TalentIQ - Background filtering + AI transcribe/voice-m0-baseline`. The handoff is `docs/handoffs/m0-baseline.md` in that child.
- The worker reports 66 automated tests passing (audio 8, ASR 21, pipeline 20, service 17), `pip check` clean, and successful local model download/load/decode using faster-whisper-tiny.en int8 CPU. These results are worker-reported and still need independent review.
- The real JFK speech fixture could not be fetched because its external CDN was blocked. A synthetic WAV verified model load/decode and produced text; real speech accuracy remains unverified. The user separately tested the live microphone baseline and approved H0.
- M0 UI behavior reported: real PortAudio device enumeration, input RMS meter, Idle/Listening/Processing/Error states, partial/final transcript grouping, Copy/Clear, permission notice, and optional `--dev-recording`. RNNoise, Hush, and Combined are visibly unavailable and return `STAGE_UNAVAILABLE`; no filter implementation has been claimed.
- Independent M0 review task `task_8510b5dc7853` completed in Orca child worktree `voice-m0-review`. Verdicts: PRD/specification compliance PASS, code quality/tests/error handling PASS. Report saved to `docs/handoffs/m0-review.md`. M0 baseline has been successfully integrated into main.
- H0 gate `gate_150349ca6493` is resolved as passed. M1 task `task_64f8c2de368e` is active in child `voice-m1-rnnoise`; after its review, give the user the H1 commands and short script from `docs/checkpoints/H1-static-noise.md` plus the worker handoff.
- No product acceptance test T1–T6, latency target, real noise-only behavior, or real RNNoise/Hush inference has passed. Antigravity’s architecture review is `3a2a0eb` and is PASS WITH CONDITIONS, specifically requiring measured noise-only behavior and short/full-window ASR timings.

## Live coordination state at handoff

- Completed and integrated: architecture/contracts (`dace574`), acceptance/checkpoint plan (`70e726a`), architecture review (`3a2a0eb`), acceptance reconciliation (`18a0257`, `bd88e00`), M0 baseline implementation and review.
- Orca historical rows for completed external workers remain retained because they were externally owned; their finished child worktrees and terminals were cleaned. The failed acceptance dispatch `ctx_6819e53540a5` remains historical and is not evidence.
- No agent is authorized to start new work in the main worktree. Every new worker, including the pending M0 reviewer, must use an Orca child worktree under this main worktree. Do not reuse the two legacy main-worktree workers for implementation.
- Current sequence: H1 user checkpoint → M2 offline Hush preparation. Keep this ledger current after each gate.
