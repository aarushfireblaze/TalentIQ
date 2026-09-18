# H1 Resampler Repair Handoff

## Fix Description
- Modified `StreamingResampler` to maintain a FIFO of incoming `AudioFrame` metadata (`session_id`, `epoch`, `seq`, `sample_start`, `captured_ns`).
- For every 160 samples of continuous output, the exact source metadata is popped from the FIFO, perfectly preserving the 48kHz -> 16kHz mapping and original timestamps without silent fabrication.
- Explicitly reset state on discontinuity boundaries (change in `session_id`, `epoch`, or unannounced jumps in `sample_start`) and carry over the discontinuity marker to the first emitted frame after reset. This successfully purges the old resampler tail.

## Tests and Evidence
Added specific unittests in `tests/test_resampler_metadata.py` exposing metadata/delay properties:
1. Validated that a first zero-output push due to algorithmic delay correctly maps its metadata to the multi-frame output released by later pushes after 200 source frames (`test_zero_output_then_multiple_frames_released`).
2. Validated explicit state reset clears prior PCM tail and emits new-epoch data, verified against a fresh independent resampler to ensure zero state bleed (`test_explicit_reset_same_session_epoch`).
3. Validated unannounced `sample_start` gaps explicitly trigger reset (`test_same_session_unannounced_epoch_or_sample_gap`).
4. Validated unannounced `epoch` changes explicitly trigger reset (`test_same_session_unannounced_epoch_change`).
5. Validated trailing padding handles incomplete final valid samples cleanly by asserting total valid samples output matches expectation and trailing padding is precisely zeroed (`test_partial_final_padding_checked_zero`).

Scoped regression proofs executed out-of-tree against the original main resampler (`cd /tmp/voice_test && PYTHONPATH="/Users/aarushgupta/Documents/TalentIQ - Background filtering + AI transcribe/src" pytest test_resampler_metadata.py`) demonstrated failures precisely as expected (6 failed tests), confirming the coverage correctly models the repair. 

## Command Execution & Results

**Caveman Skill Read:** `.agents/skills/caveman/SKILL.md`
**Module Path:** `src/voice_filtering/audio/resample.py`

```bash
$ source .venv/bin/activate
$ python -m unittest discover tests
/Users/aarushgupta/orca/workspaces/TalentIQ - Background filtering + AI transcribe/voice-h1-resampler/tests/test_service.py:8: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  from starlette.testclient import TestClient
......................................................................................................
----------------------------------------------------------------------
Ran 102 tests in 15.133s

OK

$ pip check
No broken requirements found.
```

## Known Limitations
- The algorithmic delay of soxr is flushed upon `finish()`. Delayed chunks rely on the metadata enqueued when the samples were pushed, resulting in a correct time mapping, though the algorithmic delay itself is uncompensated in terms of wall-clock. This adheres precisely to the architecture contract.
