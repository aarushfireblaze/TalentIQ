# Voice filtering project progress

Updated: 2026-09-17

## Authority and scope

The supplied PRD is the product specification: `docs/requirements/Voice_Filtering_System_PRD.docx`, with a complete text extraction beside it. The user authorized delegated implementation and asked for opportunities to test during development. The coordinator owns sequencing, decisions, review and this ledger; child agents own all program code and fixes.

Orca run: `run_74849e16ac93`. Initial repository commit: `e8bfca3`.

Required final order: microphone → RNNoise → one explicit 16 kHz resampling boundary → Hush → replaceable local ASR → transcript UI. No silent filter fallback. Model versions must be pinned. No recruiting features, cloud accounts, or public deployment.

## Milestones and human checkpoints

| Milestone | Deliverable | State | Human test |
|---|---|---|---|
| Architecture | Interfaces, dependency feasibility, scoped implementation briefs | Starting | No extra approval required for the supplied PRD |
| M0 | Raw mic, level meter, optional WAV, local ASR and transcript UI | Pending architecture | H0: select mic, speak, stop/restart, copy/clear, inspect transcript and delay |
| M1 | RNNoise wrapper and live mode | Held until H0 feedback | H1: compare raw vs RNNoise with fan/typing and primary voice |
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

## Current work

- Read the entire PRD and preserved the original plus searchable text in the repository.
- Confirmed this is an empty initialized repository on an Apple Silicon host.
- Confirmed Orca is ready and OpenCode exposes MiMo v2.5. Checking available launch routes for the requested agent mix.
- Architecture/contracts: Codex worker `task_156f3abe0f98`, dispatch `ctx_50b6ce643017`; runtime reports `gpt-6-astra`.
- Acceptance and checkpoint documents: OpenCode MiMo v2.5 worker `task_7f021e921f2a`, current dispatch `ctx_31108db79ae7`. MiMo identity verified on the terminal display. Initial dispatch `ctx_6819e53540a5` lost its prompt to a startup update dialog and ended a turn without doing the task. Coordinator fenced that attempt and retried in the same terminal after the dialog cleared; the current worker was observed reading the PRD and preparing the assigned documents.
- M0 implementation is queued as task `task_4ab0a7f16863`, dependent on the architecture task. Its implementer will own code; coordinator does not program.
- M1 is represented by task `task_64f8c2de368e`, blocked by human gate `gate_150349ca6493`. Do not resolve without user feedback or explicit waiver.
- Antigravity is installed as a desktop app but a supported supervised CLI launch route has not been established. Do not claim Antigravity review occurred. Codex covers architecture now.
- Next: accept architecture/contracts and acceptance documents, then delegate M0 implementation and independent review.
