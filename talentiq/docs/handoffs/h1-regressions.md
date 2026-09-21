# H1 Controls & RNNoise Selection Repair

## Changes Made

- **UI Polling & Network Recovery**: Modified `apps/ui/app.js` to correctly poll the `/api/state` endpoint when a mode change is pending. Added `fetchState()` on SSE reconnection (`eventSource.onopen`) to ensure the client stays synchronized with the server's state after a network drop.
- **Controller Pending State Cancellation**: Updated `src/voice_filtering/pipeline/controller.py` so that switching back to the *current* mode while a switch is pending clears the pending mode instead of queuing a no-op switch.
- **Tests**: Expanded `tests/test_rnnoise.py` to cover re-selecting the same mode, cancelling a queued switch, and ensuring `pending_mode` is handled correctly. These tests pass.
- **Same-Input Replay Evidence**: Verified `scripts/replay_ab.py` works. Ran it using `tests/fixtures/generated/noisy_speech.wav` generated from `jfk.wav` by adding noise. The script processes the file through both `raw` and `rnnoise` pipeline modes sequentially, measuring timing, metrics, and transcription differences.

## Evidence

- A/B Replay evidence is recorded in `artifacts/replay/ab-report.json`.
- UI successfully selects modes cleanly without locking up.
- Disconnecting and reconnecting SSE fully re-syncs state.
- All unit tests in `test_rnnoise.py` pass.
