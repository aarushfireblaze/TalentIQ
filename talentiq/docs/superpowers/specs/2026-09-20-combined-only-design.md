# Combined-only voice filtering

## Goal

Ship one microphone path: RNNoise at 48 kHz, one conversion to 16 kHz,
Hush, then ASR. Users cannot select raw, RNNoise-only, or Hush-only paths.

## Scope

Delete `.agents/`, `AGENTS.md`, and `progress.md`. Remove project-planning
references from README and retain only product setup and operation guidance.

The service always starts the Combined pipeline. The UI has no mode control and
does not display per-transcript mode tags. `POST /api/mode` is removed. A
`mode` field in `POST /api/start` is ignored for compatibility; the response
always reports `combined`.

RNNoise and Hush remain as internal modules. They are required by the single
Combined pipeline and are not independently selectable. Startup fails with an
explicit stage error when either filter is unavailable. No raw fallback exists.

## Controller and service

`PipelineControllerImpl` has one fixed `combined` mode. It validates both
filters and ASR before capture starts, initializes each stage once per session,
and processes each captured frame in order: RNNoise, resampler, Hush, ASR.
Mode-switch state, public switching behavior, and separate-filter execution
branches are removed.

The service no longer exposes `/api/mode`. `/api/start` preserves device and
recording inputs, but does not accept a selectable runtime path.

## UI

The UI describes the active path as Combined filtering. It retains device
selection, Start/Stop, status/error presentation, recording opt-in, transcript
copy and clear controls, and stage metrics. It does not render radio buttons or
issue mode-switch requests.

## Tests

Controller tests prove startup uses Combined, rejects startup when either
filter is unavailable, runs filters in RNNoise-to-Hush order across exactly one
resampling boundary, and reports `combined` transcript provenance. Service
tests prove `/api/start` returns Combined regardless of a legacy mode field and
`/api/mode` returns 404. UI source tests prove no mode selector or mode endpoint
request remains.

Remove tests whose purpose is separate Raw, RNNoise-only, Hush-only, or runtime
mode-switch behavior. Keep unit tests for the internal RNNoise and Hush modules.

## Acceptance checks

Run focused controller, service, and UI-source tests; then run the full suite
and `pip check`. Confirm the tracked tree no longer contains `.agents/`,
`AGENTS.md`, or `progress.md`. Push the resulting commit to the configured
`origin` remote.
