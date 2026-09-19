# Project agent instructions

## Caveman communication

Every agent working in this repository must read
`.agents/skills/caveman/SKILL.md` before starting work. Apply Caveman **full** to
chat and status reports throughout the session, unless the user changes
the mode. Do not depend on automatic skill discovery or a `/caveman` command.

Keep technical facts, negative constraints, exact errors, numbers, units, and
verification evidence. Clarity takes priority over compression. Write code,
comments, documentation, handoff files, and commit messages in normal English,
as required by the skill. Higher-priority runtime instructions still apply.

If an older worktree lacks the skill, read it from the main worktree at
`/Users/aarushgupta/Documents/TalentIQ - Background filtering + AI transcribe/.agents/skills/caveman/SKILL.md`.
Do not create a different skill or silently skip it.

## Manual worktree workflow

The user creates and assigns worktrees manually. Agents must not spawn other
agents or start automated coordination runs. Use one agent per worktree and one
bounded task per agent. Never have two agents edit
the same files concurrently. Favor Antigravity Pro for coding; use OpenCode
MiMo v2.5 less for coding. Use Codex only when necessary, with Sol.

Read the current state in `progress.md`, the assigned task, and only relevant
specification sections. Respect file ownership. Do not merge another branch or
advance a milestone unless the user explicitly assigns that work.

## Token discipline

Start fresh chats in existing worktrees when old chats have become expensive.
Use the worktree's code and `progress.md` as the handoff. Send only changed
instructions on follow-ups; do not repeat project history. Read only relevant
files and specification sections. Prefer concise completion reports over
repeated terminal dumps.

Save detailed evidence in the task handoff file and report its path, commit,
test result, and blocker. Run focused tests while editing and one full suite
for the final snapshot. Repeat checks only for new changes, failures, or
unresolved concerns.

## Human checkpoints

H0 is approved. H1 repairs and user retest are pending. Do not claim a human
checkpoint passed from automated tests. Pause dependent milestone integration
at each checkpoint until the user tests and provides feedback. Preserve the
PRD's pipeline order and never silently fall back to an unfiltered mode.
