# Project agent instructions

## Caveman communication

Every coordinator, implementer, investigator, and reviewer must read
`.agents/skills/caveman/SKILL.md` before starting work. Apply Caveman **full** to
chat and worker status reports throughout the session, unless the user changes
the mode. Do not depend on automatic skill discovery or a `/caveman` command.

Keep technical facts, negative constraints, exact errors, numbers, units, and
verification evidence. Clarity takes priority over compression. Write code,
comments, documentation, handoff files, and commit messages in normal English,
as required by the skill. Higher-priority runtime instructions still apply.

For existing child worktrees lacking the skill, read the coordinator-provided
absolute skill path, then bring this instruction file and the skill into the
child using the coordinator's specified documentation commit. Do not create a
different skill or silently skip it. Report the path actually read.

## Worker placement and ownership

The root orchestrates; child agents implement and fix program code. Every new
worker belongs in an Orca child worktree under the main worktree. Reuse workers
with relevant context when safe. Spawn only when necessary. Favor Antigravity
Pro for coding; use OpenCode MiMo v2.5 less for coding. Use Codex only when
necessary, with Sol. Workers must not spawn other workers.

Read `progress.md` and the assigned task brief. Respect file ownership and the
live Orca dispatch preamble. Process and acknowledge the complete inbox batch
at natural checkpoints. Do not reuse lifecycle IDs from previous dispatches.

## Human checkpoints

H0 is approved. H1 repairs and user retest are pending. Do not claim a human
checkpoint passed from automated tests. Pause dependent milestone integration
at each checkpoint until the user tests and provides feedback. Preserve the
PRD's pipeline order and never silently fall back to an unfiltered mode.
