# H1-B ASR provenance and decode/reset repair

## Scope and commits

- Started from `main` at `1446da4` and cherry-picked shared H1 baseline `3419488` as `7c0044f`.
- Inspected `docs/handoffs/pause-2026-09-18/voice-h1-resampler.patch`. Ported its lock-scoped utterance extraction, outside-lock decode, and atomic event acceptance concepts. Reworked its frame filtering and timing; did not apply the patch wholesale or execute its scratch helper.
- Follow-up changes are limited to `src/voice_filtering/asr/whisper.py`, `tests/test_asr.py`, and this handoff.

## Changes and evidence

- `push_audio` rejects frames with a different session or epoch under the scheduler lock. `run_step` rechecks each drained frame, including a generation number, before adding it to an utterance. A reset with unchanged session and epoch still invalidates frames drained before reset.
- Utterance extraction captures copied PCM, session, epoch, mode, generation, start time, end time, and final reason under one lock. Decode runs outside the lock. A result enters the final queue only if all captured provenance still matches, with validation and queue append in one critical section. The callback runs after lock release so a callback can call `reset` without deadlock. Acceptance occurs at queue append; a reset after that point does not retract an accepted callback.
- End time uses valid sample counts and each frame's sample rate. Start time retains the existing 48 kHz source sample clock used by resampler metadata. The draft's `len(frames) * 10 ms` calculation overstated a padded final frame.
- Deterministic tests block decode or frame analysis with events to cover reset during decode, drained old frames, mixed stale and fresh ingress, reset with unchanged identity, callback reentry, and partial-frame duration. The new duration and drained-frame tests failed against the baseline before implementation. The unchanged-identity test also failed before its generation check.

## Verification

- `.venv/bin/python -m unittest -q tests.test_asr`: 26 tests, OK. Process exit 0. `soxr` printed a nanobind reference leak warning on interpreter exit.
- `.venv/bin/python -m unittest discover -s tests -v`: 118 tests, 2 failures, process exit 1. Failures: `test_rnnoise.TestModeProvenance.test_mode_switch_updates_event_provenance` and `test_rnnoise.TestModeProvenance.test_stale_decode_rejected_on_reset_during_inflight`. Both tests reset to epoch 1, but their `_silence_frames` helper at `tests/test_rnnoise.py:473` hardcodes `epoch=0`. The scheduler correctly rejects those stale silence frames, so no final event appears. `tests/test_rnnoise.py` belongs to H1 controls and was not edited here. Full run also printed Starlette's `httpx` deprecation warning and the `soxr` nanobind leak warning.
- `.venv/bin/python -m pip check`: `No broken requirements found.` Process exit 0. Pip warned that its cache directory was not writable.
- `git diff --check`: no whitespace errors.

## Blocker and limits

- H1 controls owner must update the two `tests/test_rnnoise.py` cases to supply epoch 1 silence frames, then rerun the combined full suite. Do not relax ASR provenance filtering to satisfy stale test data.
- No acoustic suppression, model inference, or browser checkpoint proof was produced by these unit tests. H1 remains pending user retest.
