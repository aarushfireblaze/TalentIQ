# Architecture handoff

Date: 2026-09-17. Assigned task `task_156f3abe0f98`. Scope completed: documentation/contracts and executable M0 brief only. The native-capture/local-SSE choice was accepted; no redundant PRD/design approval is needed.

## Deliverables and next owner

- [Architecture contract v1](../architecture.md): precise PCM/timeline metadata, native frame boundaries, bounded queues, ASR threading, HTTP/SSE schemas, lifecycle/error behavior, mode availability and upstream pins.
- [M0 implementation brief](../plans/m0-baseline.md): exact owned paths, three sequential implementation tasks, deterministic tests, pinned real-model smoke, setup/launch commands and H0 human test script. One implementer owns M0; no overlapping application-file owners.
- This handoff records evidence and constraints. Only these three documentation files belong to this architecture worker.

Historical setup note: the PRD, text extraction and progress ledger were committed before implementation began. This document predates the current manual-worktree workflow; use `AGENTS.md` and `progress.md` for active instructions. No push, nested delegation, application edits or progress edits occurred in this architecture task.

## Decisions the implementer should preserve

Plain HTML/CSS/JavaScript; one loopback Python/Starlette/Uvicorn service; sounddevice/CoreAudio source at 48 kHz; soxr stream to 16 kHz; faster-whisper tiny.en on CTranslate2 CPU. macOS permission belongs to the launching host/process, not the browser. Unsupported 48 kHz devices fail explicitly in M0. Only Raw is available; the other three displayed modes explain that their filters are not implemented. ASR missing/load failure is visible, never substituted with mock text.

Input capture, DSP, ASR scheduling/inference and optional WAV writing are independently bounded. Stop releases capture before bounded finalization; restart cannot accept stale inference. Snapshot entries explicitly carry session_id, preserving valid historical final text; that is distinct from newly arriving stale results. Mode/gap epochs prevent windows spanning incompatible audio paths. Final native calls can hang despite thread timeouts: device release and explicit busy/error reporting take precedence over pretending a worker was safely cancelled.

Hush future boundary is 16 kHz / 160 samples per call, with a 320-sample STFT window, normalized float32. RNNoise boundary is 48 kHz / 480 samples, with explicit conversion between normalized floats and its int16-scale float API. Hush receives already-resampled 16 kHz so its internal resampling is not accidentally enabled. Neither wrapper exists in M0.

## Exact evidence obtained

1. Read the complete `docs/requirements/Voice_Filtering_System_PRD.txt` (sections 1–18) and `progress.md`. Inspected the initial repository/history; kept M0 bounded, committed only owned docs, and clarified retained transcript identity.
2. Executed `uname -m`, `sw_vers`, `python3 --version`: arm64; macOS 27.0 build 26A428; Python 3.13.2. No microphone stream or device recording was opened.
3. Queried primary PyPI release JSON for every listed direct/native dependency and checked relevant arm64/universal2 wheel filenames. CTranslate2 4.8.2 has CPython 3.13 arm64; soxr 1.1.0 has compatible abi3 arm64; sounddevice 0.5.6 supplies universal2. Verified setuptools 80.9.0 (Python >=3.9) as the local build backend pin. These are availability checks, **not** a successful install/import/resolution.
4. Queried Hugging Face model metadata and immutable config/model card/license. Hush revision `a55d932cbf6344d284ac985f21e7f6e5bc4d38a5`, ONNX bundle upstream LFS SHA256 `45632ccaa82b71bb743d6caa7c78e983fe2f2790a3af7f6ec48e6ed7ba085df6`; config confirms 16 kHz/320 FFT/160 hop. Model/source declare Apache 2.0. tiny.en revision `0d3d19a32d3338f10357c0889762bd8d64bbdeba` is declared MIT. The architecture links the exact upstream evidence.
5. Read pinned Hush deployment README, C header and Python wrapper at `9f6414e91461a8f4bdf9840c0cdcdcb7da986339`. GitHub metadata confirms the dylib path exists (10,286,912 bytes, Git blob `18ddfcb0f9d907e48640e639ed1e0125ac7392ef`); no dylib or model was executed. The guide claims Apple Silicon support and contains an outdated release link. It also documents single-session non-reentrancy and a past concurrency fix; pinned source matters.
6. Read RNNoise's actual demo at `70f1d256acd4b34a572f999a05c87bf00b67730d`: 480-sample frames, int16 samples cast to float before native processing. No RNNoise build was attempted.
7. Resolved upstream whisper.cpp commit `da54572229bcf64ba367d96c7ef15770376c4280` for the planned JFK prerecorded ASR fixture. The implementation task must fetch/validate/hash it; this worker did not run an ASR smoke or claim fixture text recognition.

Research used read-only primary HTTP queries, including curl where the web fetcher could not open raw/API URLs. System Python urllib failed certificate validation; curl with normal verification succeeded. No insecure TLS flags, package installation, model inference, audio capture, generated benchmark result or remote mutation occurred.

## Verification and remaining constraints

Documentation verification checks: balanced fenced blocks; required fields/revisions/path ownership and local prerequisite links; no executable implementation placeholder sections; whitespace/diff checks; staged commit contains only the three assigned docs. No application test suite exists in this task and none is claimed to pass. Automated tests specified in the M0 plan are future required work.

The M0 implementer must resolve/lock and validate the candidate dependencies, diagnose project-local TLS trust if setup reproduces the observed error, run the actual local-model prerecorded-WAV smoke, and deliver an independent reviewable commit. Host macOS support, microphone permission/device behavior, live transcription and the ≤1.5 s target remain unmeasured. No performance claim in the model card is local evidence.

M2 must verify Hush binary architecture/linkage/load, checksum the downloaded native artifact, confirm runtime 160-sample frame reporting, measure actual latency/alignment/flush semantics and demonstrate real deterministic WAV inference. Supplied licenses and dependency notices must accompany later redistribution; this was metadata/source inspection, not a full bundled-binary license audit. The loud-interferer/target-speaker limitation remains explicitly accepted in the PRD.

H0 follows M0 implementation and separate spec/code-quality review, using the plan's exact commands and human script. Actual user feedback is required before dependent M1 work; M2 offline preparation can proceed independently if assigned. Keep stub/unit evidence, real-model evidence and manual/live evidence separate in all milestone reports.
