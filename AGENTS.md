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

Read the current state and assigned task in `progress.md`, plus only relevant
PRD sections and code. Respect file ownership. Do not edit `progress.md` from a
task worktree; the user maintains the task board after reviewing evidence. Do
not merge another branch or advance a milestone unless the user explicitly
assigns that work.

## Token discipline

Start one fresh chat in each new task worktree. Use `progress.md` and the
relevant diff as the handoff. Send only changed
instructions on follow-ups; do not repeat project history. Read only relevant
files and specification sections. Prefer concise completion reports over
repeated terminal dumps.

Report commit, exact test result, evidence path, and blocker in the final chat.
Store large generated evidence under gitignored `artifacts/`; do not create a
new Markdown handoff. Run focused tests while editing and one full suite for
the final snapshot. Repeat checks only for new changes, failures, or unresolved
concerns.

## Human checkpoints

H0 is approved. H1 repairs and user retest are pending. Do not claim a human
checkpoint passed from automated tests. Pause dependent milestone integration
at each checkpoint until the user tests and provides feedback. Preserve the
PRD's pipeline order and never silently fall back to an unfiltered mode.
