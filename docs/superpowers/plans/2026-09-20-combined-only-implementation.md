# Combined-only voice filtering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose one Combined voice-filtering path and remove project-agent artifacts.

**Architecture:** Controller fixes session mode to `combined` and always runs RNNoise, one resampling boundary, Hush, then ASR. Service removes runtime mode changes; UI removes path selection. RNNoise and Hush remain private pipeline dependencies.

**Tech Stack:** Python 3, Starlette, vanilla JavaScript, unittest.

**Spec:** `docs/superpowers/specs/2026-09-20-combined-only-design.md`

## Global Constraints

- Pipeline order is RNNoise at 48 kHz, one conversion to 16 kHz, Hush, then ASR.
- Users cannot select Raw, RNNoise-only, or Hush-only paths.
- A missing RNNoise or Hush stage stops startup with an explicit error.
- Recording and device selection remain available.
- Delete `.agents/`, `AGENTS.md`, and `progress.md`.

## Review Focus

- Legacy `mode` input to `/api/start` cannot select an unfiltered path.
- `/api/mode` is absent.
- Missing RNNoise or Hush prevents capture.
- UI contains no mode selector or mode-switch request.

---

### Task 1: Fixed Combined controller and service

**Files:**

- Modify: `src/voice_filtering/pipeline/controller.py`
- Modify: `src/voice_filtering/service.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_service.py`

**Interfaces:** `PipelineControllerImpl.start(device_id, mode, record)` returns a response with `mode == "combined"`; `POST /api/mode` is removed.

- [ ] Write tests where `controller.start("0", "raw", False)` returns `combined`, missing stages reject startup, and `POST /api/mode` returns 404.
- [ ] Run `.venv/bin/python -m unittest tests.test_pipeline tests.test_service -v`; observe mode-selection failure.
- [ ] Fix controller mode to `combined`, remove mode-switch state and service route, preserve explicit stage failures.
- [ ] Re-run focused tests; observe passing behavior.
- [ ] Commit controller/service change.

### Task 2: Combined-only UI and documentation

**Files:**

- Modify: `apps/ui/index.html`
- Modify: `apps/ui/app.js`
- Modify: `README.md`
- Create: `tests/test_ui_source.py`

**Interfaces:** UI consumes fixed service state and issues no `/api/mode` request.

- [ ] Write source test asserting HTML excludes `name="mode"` and JavaScript excludes `/api/mode`.
- [ ] Run `.venv/bin/python -m unittest tests.test_ui_source -v`; observe mode-control failure.
- [ ] Remove selector, switching code, and transcript mode tags; retain device choice, recording opt-in, status/errors, copy/clear, and metrics. Update README to document combined-only operation.
- [ ] Re-run UI test; observe passing behavior.
- [ ] Commit UI/documentation change.

### Task 3: Artifact removal and release check

**Files:**

- Delete: `.agents/`
- Delete: `AGENTS.md`
- Delete: `progress.md`

- [ ] Remove tracked requested files and folders.
- [ ] Verify their absence and verify `apps/` and `src/` have no `value="raw"`, `value="rnnoise"`, `value="hush"`, or `/api/mode`.
- [ ] Run `.venv/bin/python -m unittest discover -s tests -v` and `.venv/bin/python -m pip check`.
- [ ] Commit deletions and push all commits to `origin`.
