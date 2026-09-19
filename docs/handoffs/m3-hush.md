# M3 Hush Streaming Integration Handoff

## Completed Work
- Added `hush` mode to `PipelineControllerImpl` and injected `HushProcessor` into the pipeline.
- Added Hush model latency metrics (`avg_ms`, `p95_ms`) and availability status reporting.
- Updated UI (`apps/ui/index.html` and `apps/ui/app.js`) to support Hush selection, display Hush availability status, and render Hush timing metrics exactly like RNNoise.
- Added pipeline tests for Hush acceptance and updated service tests to handle the new stage.

## Test Results
- **Full Test Suite (`pytest tests/`)**: 9 tests failed out of 128 total.
- **Failures**: The failing tests (`tests/test_hush.py` and some in `tests/test_rnnoise.py`, `tests/test_service.py`) all stem from the absence of the Hush native library (`libweya_nc.dylib`) and its ONNX model bundle (`advanced_dfnet16k_model_best_onnx.tar.gz`).
- **Pip Check (`pip check`)**: Failed due to global environment conflicts (`s3fs`, `streamlit`, `numba` requiring different versions than installed). These are external to the project's direct `requirements.lock.txt`.

## Evidence
- Commits: `2e41359` (feat: integrate hush into live streaming pipeline and UI).
- Real-model timing could not be verified because the native library and models are missing from the environment.
- Explicit failures are implemented: The UI correctly queries the status and displays "Failed: Library not found at..." or "Hush processor not injected".

## Blockers
- **Missing Hush Models and Native Library**: M2 (Hush offline) is listed as "Held", meaning the `libweya_nc.dylib` and `advanced_dfnet16k_model_best_onnx.tar.gz` are not available in the workspace or main branch. `scripts/setup_models.py` only fetches `faster-whisper-tiny.en`. Without these artifacts, deterministic replay and real-model timing cannot be proven.

## Next Steps for User
1. Provide the Hush native library and ONNX model or an automated way to fetch them.
2. Review the UI integration on `http://127.0.0.1:8765/`.
3. Clear the M2 dependency block to allow full M3 test acceptance.
