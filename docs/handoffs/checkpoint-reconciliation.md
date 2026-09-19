# Checkpoint documentation reconciliation handoff

Date: 2026-09-17
Documentation reconciliation: complete; every product test was **NOT RUN** at the time of writing. See [progress.md](../../progress.md) for current milestone status.
Reconciliation commit: `a0927ecc1850dd2898b7aa699c4881a7a0cbe64b` (`docs: reconcile voice filtering acceptance with architecture`). This report followed in a documentation-only commit so it could name the immutable reconciliation commit. Both commits were later integrated.

## Scope and findings

Read the complete PRD text, `docs/architecture.md`, `docs/plans/m0-baseline.md` and all six existing owned acceptance/checkpoint documents. Updated only `docs/acceptance.md`, `docs/checkpoints/H0-baseline.md`, `docs/checkpoints/H1-static-noise.md`, `docs/checkpoints/H2-near-field.md`, `docs/checkpoints/H3-evaluation.md` and `docs/handoffs/acceptance-plan.md`; this new report is the seventh owned path.

- H2 now explicitly requires M2 offline validation plus both M3 streaming Hush and M4 Combined; the handoff sequence places M4 before H2. H1/H2 require early same-input replay evidence even though the complete evaluator is M5.
- All comparative acceptance requires identical recorded input and ASR settings with independent/reset state. Back-to-back live takes are exploratory only; missing replay evidence leaves comparative acceptance NOT RUN.
- Background intrusion rates use fixed spoken background reference counts, with primary retention scored separately against fixed primary references and Raw. Shared words, repeated speech, ambiguous attribution, absent background speech and Raw floor effects are explicit. Removed the unsupported 90% retention cutoff and the claim that T3 requires Combined to beat Hush-only.
- Zero dropped frames is aspirational, with no binding PRD numeric threshold. Loss and lateness are measured separately. Restored the PRD T5 requirement against severe latency growth without inventing a numeric cutoff.
- H0 describes native macOS permission for launching Orca/Terminal/Python, capture only after Start, idle-only device/Clear controls, honest errors/unavailable modes and explicit development-recording opt-in. Exact prescribed M0 setup/launch and verification commands are marked NOT YET VERIFIED.
- Mock tests assert frame/rate/scaling, stateful resampling, metadata, queues and lifecycle contracts; nonzero output does not prove suppression. Real model loading, same-input quality, live latency and human feedback remain distinct evidence. Resampling starts in M0 and is revalidated in H1/H2; the developer panel remains optional.

## Exact documentation checks performed

All checks below concern text and Git state only. No application setup, package install, model download/inference, product test, UI launch or microphone access occurred. No code, README, architecture/plan, progress ledger or requirements were changed; no subagents or push were used.

1. `git diff --check` — exit 0, no whitespace errors.
2. `git diff --stat`, `git diff --numstat`, `git status --short` and scoped `git diff -- docs/acceptance.md docs/checkpoints/H0-baseline.md docs/checkpoints/H1-static-noise.md docs/checkpoints/H2-near-field.md docs/checkpoints/H3-evaluation.md docs/handoffs/acceptance-plan.md` — manually reviewed changes against the PRD/architecture/plan; only the six owned existing paths changed before the reconciliation commit.
3. The exact read-only Python check below — exit 0; output: `DOC CHECK OK: 6 documents; 166 NOT RUN table cells; 9 local links; balanced fences/tables; exact H0 commands; obsolete contradictions absent; changed paths owned`.
4. `git diff --cached --check` — exit 0; `git diff --cached --name-only` — exactly the six owned existing documents before committing `a0927ec`.
5. `git rev-parse HEAD` after the reconciliation commit — `a0927ecc1850dd2898b7aa699c4881a7a0cbe64b`.

```bash
python3 - <<'PY'
from pathlib import Path
import re
import subprocess
files = [Path('docs/acceptance.md'), *sorted(Path('docs/checkpoints').glob('H[0-3]-*.md')), Path('docs/handoffs/acceptance-plan.md')]
assert len(files) == 6
status_cells = links = 0
for path in files:
    text = path.read_text()
    assert 'Status: **NOT RUN**' in text, path
    assert len(re.findall(r'^```', text, re.M)) % 2 == 0, path
    width = status_index = None
    for line in text.splitlines():
        if not line.startswith('|'):
            width = status_index = None
            continue
        cells = [cell.strip() for cell in line.strip('|').split('|')]
        if width is None:
            width = len(cells)
            status_index = next((i for i, cell in enumerate(cells) if cell in ('Status', 'Validated?')), None)
            continue
        assert len(cells) == width, (path, line)
        if set(''.join(cells)) <= set('-: '):
            continue
        if status_index is not None:
            assert cells[status_index].startswith('NOT RUN'), (path, line)
            status_cells += 1
    for target in re.findall(r'\]\(([^)]+)\)', text):
        if '://' not in target:
            assert (path.parent / target.split('#')[0]).exists(), (path, target)
            links += 1
    for obsolete in ('background words / total words', 'Background %', '0 target', '≥90%', 'Zero or minimal', 'not a hard gate', 'resampling is not yet tested', 'M4–M6 implementation'):
        assert obsolete not in text, (path, obsolete)
plan = Path('docs/plans/m0-baseline.md').read_text()
h0 = Path('docs/checkpoints/H0-baseline.md').read_text()
launch = re.findall(r'```bash\n(.*?)```', h0, re.S)[0]
assert launch in plan, 'H0 launch must exactly match prescribed M0 block'
for line in re.findall(r'```bash\n(.*?)```', h0, re.S)[1].splitlines():
    assert line in plan, ('unmatched prescribed verification line', line)
owned = {str(p) for p in files} | {'docs/handoffs/checkpoint-reconciliation.md'}
changed = subprocess.check_output(['git','diff','--name-only'], text=True).splitlines()
assert set(changed) <= owned, changed
print(f'DOC CHECK OK: {len(files)} documents; {status_cells} NOT RUN table cells; {links} local links; balanced fences/tables; exact H0 commands; obsolete contradictions absent; changed paths owned')
PY
```

## Remaining work

At the time of this handoff, the documentation commits required review and integration, and all product statuses remained NOT RUN. M0 existence, setup success, real ASR behavior, physical microphone/permission behavior, filter implementation/quality, live latency and T1–T6 results were not established by this documentation task. Implementation evidence and actual human H0 feedback were required before dependent product work; later checkpoints need real same-recorded-input comparisons and live stability evidence.

This historical report records documentation checks only. Current task ownership and checkpoints are defined in `AGENTS.md` and `progress.md`.
