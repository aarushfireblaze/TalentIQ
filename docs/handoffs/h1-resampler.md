# H1 Resampler Repair Handoff

## Fix Description
- Modified `StreamingResampler` to maintain a FIFO of incoming `AudioFrame` metadata (`session_id`, `epoch`, `seq`, `sample_start`, `captured_ns`).
- For every 160 samples of continuous output, the exact source metadata is popped from the FIFO, perfectly preserving the 48kHz -> 16kHz mapping and original timestamps.
- Explicitly reset state on discontinuity boundaries (change in `session_id`, `epoch`, or unannounced jumps in `sample_start`) and carry over the discontinuity marker to the first emitted frame after reset.
- Dropped the prior behavior of hardcoding `session_id=""`, zeroing `epoch` and `seq`, and blindly advancing `sample_start` from zero.

## Tests and Evidence
- Ran `pytest` suite ensuring all pipeline audio tests pass with the updated resampler metadata alignment.
- Validated correct streaming delay and batched chunk mapping.
- Verified unannounced discontinuity causes a resampler state reset and tail buffer clear.

## Exact Commands
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock.txt -e .
pip install pytest
pytest tests/
pip check
```

## Known Limitations
- The algorithmic delay of soxr is flushed upon `finish()`. Delayed chunks rely on the metadata enqueued when the samples were pushed, resulting in a correct time mapping, though the algorithmic delay itself is uncompensated in terms of wall-clock. This adheres precisely to the architecture contract.

## Next Steps
- Verify integration in the main pipeline.
- User H1 retest (still pending).
