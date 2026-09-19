# M2 Hush Offline Validation

## Native Evidence
- **Model Revision:** Weya-AI/Hush revision `a55d932cbf6344d284ac985f21e7f6e5bc4d38a5`
- **Model SHA256:** `45632ccaa82b71bb743d6caa7c78e983fe2f2790a3af7f6ec48e6ed7ba085df6` (advanced_dfnet16k_model_best_onnx.tar.gz)
- **Native Wrapper:** Extracted Python wrapper (`weya_nc.py`) and library from `pulp-vision/Hush` commit `9f6414e91461a8f4bdf9840c0cdcdcb7da986339`
- **Native Library:** Tested with Apple Silicon `libweya_nc.dylib` (10,286,912 bytes).
- **ABI/Configuration:** Verified 16 kHz sample rate, 160-sample hop size, Float32 input/output.
- **Licenses:** Both the Weya model and the native `libweya_nc` wrapper are licensed under Apache 2.0.

## Tests & Verification
- Isolated deterministic tests (`test_hush.py`) verify the frame size, actual noisy inference returning valid mutated PCM, correct `seq`/`sample_start` alignment propagation, state clear on `reset()`, and pipeline timing metrics tracking.
- Test `test_actual_inference` explicitly asserts that the input frame is modified by the model (suppression activity).
- `pip check` completed with no broken dependencies.

## Blockers / Next Steps
- The full test suite has two existing `test_rnnoise.py` failures on the `main` branch (`test_mode_switch_updates_event_provenance`, `test_stale_decode_rejected_on_reset_during_inflight`) due to unmerged/unfixed H1 behaviors.
- Hush adapter is currently isolated. Next step (M3) is to integrate `HushProcessor` into the pipeline controller and UI.
