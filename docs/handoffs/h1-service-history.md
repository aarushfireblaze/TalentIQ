# H1 Service History Handoff

## Fix Description
- Narrowed the factory callback wiring in `create_app` (`src/voice_filtering/service.py`) to properly route accepted typed `TranscriptEvent`s into the controller history before publishing to the `EventHub`.
- Preserved existing event schema, bounding, deduplication, and all snapshot timing metrics by delegating directly to `controller.add_transcript_event` and `hub.publish_transcript` in sequence.

## Tests and Evidence
Reverted previous duplicated `make_app` test fixtures and added an HTTP integration test (`test_integration_event_routing_and_history` in `tests/test_service.py`) that uses the real `create_app` with patched constructors for `CaptureSource`, `WhisperASR`, and `RNNoiseProcessor`.
1. Emitted a typed `TranscriptEvent` via the factory callback path (`on_transcript`).
2. Verified `hub.subscribe` published exactly once (with expected JSON envelope structure).
3. Verified `GET /api/state` retained accepted event fields (text, mode, session_id, epoch).
4. Verified `Stop` preserved committed history.
5. Verified mode switch/restart preserved committed history.
6. Verified clear empties history.

## Command Execution & Results

**Caveman Skill Read:** `/Users/aarushgupta/orca/workspaces/TalentIQ - Background filtering + AI transcribe/voice-h1-resampler/.agents/skills/caveman/SKILL.md`
**Module Path:** `/Users/aarushgupta/orca/workspaces/TalentIQ - Background filtering + AI transcribe/voice-h1-resampler/src/voice_filtering/service.py`

```bash
$ source .venv/bin/activate
$ python -m unittest discover -s tests -v
/Users/aarushgupta/orca/workspaces/TalentIQ - Background filtering + AI transcribe/voice-h1-resampler/tests/test_service.py:8: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  from starlette.testclient import TestClient
.........................................................................................................
----------------------------------------------------------------------
Ran 105 tests in 20.057s

OK

$ pip check
No broken requirements found.
```

## Known Limitations
- The integration test fakes `CaptureSource`, `WhisperASR`, and `RNNoiseProcessor` to prevent blocking microphone threads during testing, which correctly validates integration routing but provides no acoustic evidence.
- Human H1 remains pending; M2 held. True end-to-end OS dependency testing inside the test suite is deferred to actual acoustic tests.
