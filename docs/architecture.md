# Voice Filtering MVP architecture

Contract version: 1. Researched 2026-09-17. Authority: the complete [PRD](requirements/Voice_Filtering_System_PRD.txt) and current [progress](../progress.md). The PRD is approved; this is an implementation contract, not a new approval gate. M0 implements only the raw baseline. No filtering, microphone capture, package installation, or model inference was performed during this architecture task.

## Stack and capture decision

Use Python 3.13, sounddevice/CoreAudio capture, NumPy PCM buffers, stateful python-soxr conversion, faster-whisper/CTranslate2 CPU ASR, and Starlette/Uvicorn serving plain HTML, CSS and JavaScript on `http://127.0.0.1:8765`. Use JSON HTTP commands and server-sent events (SSE); no React, Node build, Electron, cloud ASR, Web Speech API, or binary audio over the UI transport is needed. One Uvicorn process/worker; do not use reload while capturing.

| Capture option | Advantages | Costs / decision |
|---|---|---|
| Native sounddevice/CoreAudio | Device enumeration and callback clock stay in service; same source feeds deterministic WAV replay and later four-mode comparison; no browser audio DSP | macOS permission belongs to the launching host/process, which may appear as Orca, Terminal or Python. **Selected.** Start triggers first access; UI explains the OS prompt. |
| Browser getUserMedia + AudioWorklet | Familiar browser permission and device UI | Requires PCM upload, browser-to-service clock mapping, actual-rate negotiation, disabling/verifying echo cancellation/noise suppression/automatic gain, and tab lifecycle handling. A valid later source adapter, not the M0 default. |
| Swift/CoreAudio desktop host | Direct native controls and permission integration | Adds a second language, app packaging and build/signing concerns before proving the audio chain. Defer. |

Use `query_devices()` for input devices and `check_input_settings(device=..., channels=1, dtype='float32', samplerate=48000)` before opening. M0 supports devices accepting 48 kHz mono; reject others with `UNSUPPORTED_SAMPLE_RATE`, displaying the selected device and requested format. Do not silently select a different microphone. Device IDs are service-lifetime opaque strings backed by PortAudio indices plus host/name validation; refresh after removal, never persist an index across launches. Change device only while idle. A future source adapter may explicitly normalize other hardware rates to 48 kHz; it must report that conversion.

No microphone opens at service startup, device enumeration, page load, or test collection. Native permission failures are not reliably distinguishable from all PortAudio device-open errors: report `MIC_PERMISSION_DENIED` only when confirmed; otherwise `AUDIO_DEVICE_ERROR` with the native detail and macOS Settings → Privacy & Security → Microphone guidance. Do not claim permission is granted merely because enumeration worked. Raw means no application RNNoise/Hush/browser DSP; OS/hardware processing and selected macOS microphone mode remain possible and must be recorded during comparisons.

## Dependencies and upstream evidence

These are exact **candidate pins verified to exist**, not a tested environment lock. The implementer resolves them inside `.venv`, runs import/model tests and freezes the complete transitive graph into `requirements.lock.txt`; retain these direct pins unless an observed conflict requires a documented change. Host observed here: `arm64`, macOS `27.0` build `26A428`, Python `3.13.2`. Binary wheel availability is compatibility evidence, not proof of operation on this macOS build.

| Dependency | Candidate pin | Primary evidence |
|---|---|---|
| sounddevice | 0.5.6 | [PyPI release metadata](https://pypi.org/pypi/sounddevice/0.5.6/json): universal2 macOS wheel; [installation guide](https://python-sounddevice.readthedocs.io/en/0.5.6/installation.html): pip bundles PortAudio on macOS. |
| NumPy / soxr | 2.5.3 / 1.1.0 | [NumPy metadata](https://pypi.org/pypi/numpy/2.5.3/json), [soxr metadata](https://pypi.org/pypi/soxr/1.1.0/json): compatible arm64 wheels; [streaming API](https://python-soxr.readthedocs.io/en/latest/soxr.html) supports persistent state, delay reporting and final flush. |
| faster-whisper / CTranslate2 | 1.2.1 / 4.8.2 | [release metadata](https://pypi.org/pypi/faster-whisper/1.2.1/json), [CTranslate2 wheels](https://pypi.org/pypi/ctranslate2/4.8.2/json): CPython 3.13 arm64 wheel; [platform support](https://opennmt.net/CTranslate2/installation.html). CPU backend selected, not MPS. |
| Starlette / Uvicorn | 1.6.0 / 0.53.0 | [Starlette metadata](https://pypi.org/pypi/starlette/1.6.0/json), [Uvicorn metadata](https://pypi.org/pypi/uvicorn/0.53.0/json): Python >=3.10, pure Python distributions. Use base Uvicorn, without optional extras. |
| huggingface-hub | 1.32.0 | [metadata](https://pypi.org/pypi/huggingface-hub/1.32.0/json), Python >=3.10; setup downloads exact snapshots into this project. |
| faster-whisper native transitives | onnxruntime 1.30.0; av 18.1.0; tokenizers 0.23.2 | [ORT](https://pypi.org/pypi/onnxruntime/1.30.0/json), [PyAV](https://pypi.org/pypi/av/18.1.0/json), [tokenizers](https://pypi.org/pypi/tokenizers/0.23.2/json) expose compatible arm64 wheels (ORT/PyAV require macOS >=14). Freeze the resolver's remaining dependencies as well. |

Default ASR artifact: `Systran/faster-whisper-tiny.en` revision `0d3d19a32d3338f10357c0889762bd8d64bbdeba`, [immutable model card](https://huggingface.co/Systran/faster-whisper-tiny.en/tree/0d3d19a32d3338f10357c0889762bd8d64bbdeba), declared MIT. English-only M0 is explicit in UI/setup. Use `WhisperModel(local_path, device='cpu', compute_type='int8', cpu_threads=4, num_workers=1, local_files_only=True)`, verifying supported CPU compute types at startup. No silent model/backend replacement; unsupported int8 reports `ASR_LOAD_FAILED` with supported types. [Upstream usage](https://github.com/SYSTRAN/faster-whisper/tree/v1.2.1) documents lazy segment generators: consume `list(segments)` in the ASR thread to actually execute inference. Partial text is produced by repeated bounded-window decoding; this is not a natively streaming Whisper decoder. No latency claim is established yet.

## Hush and RNNoise: pinned future boundaries

Hush identity is **Weya AI `weya-ai/hush`**, architecture `DfNetSE`, built from DeepFilterNet; do not confuse it with unrelated products called Hush. Model revision `a55d932cbf6344d284ac985f21e7f6e5bc4d38a5`; [config](https://huggingface.co/weya-ai/hush/blob/a55d932cbf6344d284ac985f21e7f6e5bc4d38a5/config.json) specifies 16,000 Hz, FFT 320, hop 160, 32 ERB bands, 64 DF bins, order 5, lookahead 0. Thus analysis window is **20 ms**, hop **10 ms**; do not call a 320-sample window a 10 ms input frame.

| Artifact | Immutable identity / inspected fact |
|---|---|
| Native ONNX bundle | `onnx/advanced_dfnet16k_model_best_onnx.tar.gz` at the HF revision above; 8,558,968 bytes; upstream LFS SHA256 `45632ccaa82b71bb743d6caa7c78e983fe2f2790a3af7f6ec48e6ed7ba085df6`. |
| PyTorch checkpoint | `model_best.ckpt`, 9,229,701 bytes; upstream LFS SHA256 `a2221e335c7de2c3453b422bf7f3c609723e453f4ca29c86137fd707d62f841b`. |
| Native source/library repository | `pulp-vision/Hush` commit `9f6414e91461a8f4bdf9840c0cdcdcb7da986339`; [deployment guide](https://github.com/pulp-vision/Hush/blob/9f6414e91461a8f4bdf9840c0cdcdcb7da986339/deployment/README.md), [C header](https://github.com/pulp-vision/Hush/blob/9f6414e91461a8f4bdf9840c0cdcdcb7da986339/deployment/include/weya_nc.h). |
| Apple Silicon binary | `deployment/lib/libweya_nc.dylib` exists at that commit per GitHub API: 10,286,912 bytes, Git blob `18ddfcb0f9d907e48640e639ed1e0125ac7392ef`. This is a Git blob ID, **not** a file SHA256. Compute SHA256 after downloading at M2. |
| License | Both [model LICENSE](https://huggingface.co/weya-ai/hush/blob/a55d932cbf6344d284ac985f21e7f6e5bc4d38a5/LICENSE) and [source LICENSE](https://github.com/pulp-vision/Hush/blob/9f6414e91461a8f4bdf9840c0cdcdcb7da986339/LICENSE) declare Apache License 2.0. Preserve supplied texts/notices, including vendored DeepFilter/ONNX dependencies when distributing; metadata inspection is not an audit of all binary dependencies. |

The native C ABI loads a model once and creates a stateful session. Call `weya_nc_session_create(model, 16000, 100.0)`, assert reported input/model sample rates are 16,000 and `weya_nc_get_frame_length(session)==160`, then feed exactly 160 contiguous normalized float32 samples per call. The returned float is an SNR estimate, not an error code. Validate handles, dimensions and finite output. Set every ctypes `argtypes`/`restype` from the header (pointer defaults can truncate handles). One DSP thread owns each session; upstream says sessions are independent, while one session is not reentrant. Free sessions before model. Reset on gaps/new sessions/mode epochs. Do **not** pass 48 kHz into this library: it would invoke its internal resampler and obscure our explicit conversion boundary.

Upstream claims CPU-only real-time inference, <1 ms processing per 10 ms audio and about 20 ms algorithmic latency; none is measured here. The model-card PyTorch example trims `fft_size-hop_size=160` samples; this does not establish total native streaming delay. M2 must measure impulse/alignment behavior, flush/tail handling, actual library dependencies/minimum macOS, architecture via `file`, `otool -L`, load success, deterministic output and finite shape. The deployment guide's release link still contains an upstream placeholder, despite a binary existing in the repository; use the pinned repository path and verify bytes. PyTorch fallback requires DeepFilterLib feature extraction and matching source, not arbitrary FFT features; it is a separately reported spike if native deployment fails. No dependency or binary was downloaded/executed for this research.

RNNoise future source pin: `xiph/rnnoise` commit `70f1d256acd4b34a572f999a05c87bf00b67730d`. [Upstream example](https://github.com/xiph/rnnoise/blob/70f1d256acd4b34a572f999a05c87bf00b67730d/examples/rnnoise_demo.c) uses 480 samples at 48 kHz, float buffers in int16 amplitude units. Wrapper converts normalized float32 ×32768 into RNNoise and divides output by 32768, validating/clipping only at documented boundaries. Assert native frame size 480. [Repository](https://github.com/xiph/rnnoise) declares BSD-3-Clause; its build can download model data, so M1 pins model bytes/checksum as well as source. Apple arm64 build is **unverified**, and x86-specific build flags must not be copied onto this host.

## Audio contract

Source rate is 48,000 Hz mono. Internal samples are C-contiguous NumPy float32 of shape `(n,)`, finite normalized PCM, nominal range [-1,1]. A frame is immutable after publication; consumers cannot retain a reused callback buffer. Clamp and count clipping at integer WAV/native boundaries; NaN/Inf is an error, not silence. Wire transport carries no PCM. WAV QA output is mono little-endian PCM16, with sample rate in the header.

```python
@dataclass(frozen=True)
class AudioFrame:
    session_id: str           # UUID per Start
    epoch: int                # 0 initially; increments at mode/gap boundaries
    seq: int                  # original 10 ms source-frame sequence, starts 0
    sample_start: int         # source timeline in 48 kHz samples, including gaps
    captured_ns: int          # monotonic timestamp of first input sample
    sample_rate: int          # 48000 before conversion; 16000 after it
    pcm: NDArray[np.float32]  # 480 or 160 samples
    valid_samples: int        # excludes padding on final frame
    discontinuity: bool      # true on first frame after a known gap
```

The source emits epoch 0; the controller stamps the active epoch before DSP, incrementing it after a gap or future mode switch. `seq` and `sample_start` never compress dropped time; a normal frame has `sample_start=seq*480`, and both survive processing/resampling. `captured_ns = session_t0_ns + sample_start*1_000_000_000//48000`. Map the first callback ADC timestamp onto `time.monotonic_ns()` using `inputBufferAdcTime-currentTime`; record timestamp source and callback arrival jitter. If PortAudio's clock is unusable, mark `timestamp_source='estimated'` and estimate first sample time from callback arrival minus frame duration. A device overflow of unknown duration ends the session with `AUDIO_DEVICE_ERROR` rather than fabricating a precise missing-sample count. Wall-clock UTC is for filenames only. JSON monotonic ns values are decimal strings, avoiding JS integer precision loss; UI shows relative ms.

Pipeline paths:

```text
Raw:      48k source ───────────────→ stateful 48k→16k → ASR
RNNoise:  48k source → RNNoise      → stateful 48k→16k → ASR
Hush:     48k source ───────────────→ stateful 48k→16k → Hush → ASR
Combined: 48k source → RNNoise      → stateful 48k→16k → Hush → ASR
```

Use one `soxr.ResampleStream(48000,16000,1,dtype='float32',quality='HQ')` per active path/epoch. It may return variable output lengths: reblock its output to 160 samples while keeping a FIFO of source frame metadata. Do not independently resample each frame, round every chunk, or attach callback-arrival time to delayed output. Report `resampler_delay_samples` and stage algorithmic delay separately from signal timestamps. At end, call final flush, emit only the true input-duration equivalent, then pad a final short frame with `valid_samples`; trim padding for ASR/WAV. Gaps discard pending resampler tail, reset state and re-anchor metadata at the next source position. Future A/B replay feeds the **same immutable 48 kHz clip** into four independent paths with identical ASR settings; align outputs by measured stage delay and record resets/drops. Never compare four separately spoken recordings as if they were identical inputs.

## Python component boundaries

Implement public contracts in `src/voice_filtering/contracts.py`. Dataclasses/protocols use standard typing; test doubles live under tests only.

```python
class AudioSource(Protocol):
    def start(self, *, device_id: str, session_id: str) -> None: ...
    def read_frame(self, timeout_s: float) -> AudioFrame | None: ...
    def stop(self) -> None: ...  # idempotent; releases device

class FrameProcessor(Protocol):  # NoiseSuppressor or SpeakerSuppressor
    def reset(self) -> None: ...
    def process(self, frame: AudioFrame) -> AudioFrame: ...
    def close(self) -> None: ...

class Transcriber(Protocol):
    def start(self, session_id: str, epoch: int) -> None: ...
    def push_audio(self, frame: AudioFrame) -> None: ... # nonblocking enqueue
    def finish(self, timeout_s: float = 5.0) -> bool: ...
    def reset(self, session_id: str, epoch: int) -> None: ...
    def close(self) -> None: ...

class PipelineController(Protocol):
    def start(self, device_id: str, mode: str, record: bool) -> dict: ...
    def stop(self) -> dict: ...
    def switch_mode(self, mode: str) -> dict: ...
    def clear_transcript(self) -> dict: ...
    def snapshot(self) -> dict: ...
```

Source timeout returns None only while running with no frame available; failures raise `PipelineError(code,stage,message,recoverable)` and explicit EOF is a source state, not infinite empty frames. Model load belongs to service startup's background worker; stream `start/reset` never reload weights. `FrameProcessor` validates expected rate/length and preserves metadata; filters remain absent in M0, not identity implementations with misleading names. The resampler has its own variable-output adapter, not `FrameProcessor`'s one-in/one-out promise.

## Threads, bounds and overload behavior

| Owner / queue | Bound | Behavior |
|---|---|---|
| PortAudio callback → source ring | 100 × 480 samples (1 s) | Copy into bounded slots, increment counters, never infer/log/write disk/wait. On overflow drop oldest whole frame; next consumed frame carries exact gap and epoch reset. |
| DSP thread → ASR ingress | 100 × 160 samples (1 s) | Nonblocking offer; on overflow drop oldest and reset utterance at gap; count dropped samples separately from source loss. |
| ASR scheduler utterance buffer | 8 s audio + 200 ms pre-roll | Scheduler handles ingress independently of inference. RMS gate is an explicitly labeled baseline heuristic, not a speaker filter. Start at >-45 dBFS, end after 600 ms below threshold; force finalize at 8 s. |
| Scheduler → inference | 1 active decode; 1 replaceable partial; 4 final jobs | Refresh partial at 750 ms cadence after at least 1 s speech. New partial replaces pending partial; final supersedes same utterance partial. Finals are FIFO and immutable. Full final queue raises `ASR_OVERLOAD`, stops capture and reports unfinished audio; never silently loses final speech. |
| DSP → optional WAV writer | 200 source frames (2 s) | Separate writer; on overflow disable recording and report `RECORDING_OVERFLOW`, mark file incomplete. Never slow capture. |
| Event subscriber | 128 pending events/client | Coalesce metrics and same-segment partials; if still full disconnect slow client; reconnect from authoritative snapshot. Capture never waits on UI. |
| Snapshot/transcript | 1,000 segments or 1 MiB text | At cap stop capture with `TRANSCRIPT_LIMIT` and preserve text; no unbounded history or silent truncation. |

ASR scheduler is a light thread; a single separate inference thread owns the Whisper model. Consume the transcribe generator there, never on the callback, DSP thread or ASGI loop. Decode `float32` 16 kHz arrays with `language='en', beam_size=1, temperature=0, condition_on_previous_text=False, vad_filter=False`. All windows belong to an utterance ID. Each partial **replaces** that utterance's previous text; final is a complete replacement and emitted once. No concatenating overlapping partials, and no fixed-window overlap masquerading as deduplication. Forced 8-second cuts can split words; report this M0 limitation. Suppress empty/whitespace events; energy gating is imperfect and silence hallucinations remain an empirical test.

Metrics update once per second, level at most 10 Hz: source/ASR/recording queue depths and capacities, dropped samples per boundary, late frames (>100 ms at DSP dequeue), callback status, input/output rates, RMS/peak dBFS, clipping, per-stage mean/p95 duration from a bounded last-1,000 observation window, ASR decode time, newest-audio-to-partial delay, utterance-end-to-final delay, and partial-first-to-final interval. Report unavailable filter timings as null, never zero measured inference. Track resampling delay. Target ≤1.5 s partial delay and 10-minute stability are acceptance goals, not proven properties.

## HTTP, events and UI state

Bind only `127.0.0.1:8765`, serve the UI and API from the same origin, with no permissive CORS. Validate Host and mutating Origin (when present), require JSON plus `X-Voice-Filtering: 1` on commands, reject foreign origins/hosts. No account/auth system is introduced. Commands are serialized by controller lock; no callback acquires that lock.

| Endpoint | Contract |
|---|---|
| `GET /api/state` | Full authoritative snapshot described below. |
| `GET /api/devices` | `{devices:[{id,name,host_api,max_input_channels,default_sample_rate}],default_device_id}`; no microphone open. |
| `GET /api/events` | SSE; first event `snapshot`, then typed JSON events; 15 s comment heartbeat. Reconnect always replaces local state using snapshot, not historical event replay. |
| `POST /api/start` | `{device_id,mode:'raw',record:false}` → 202 snapshot in `starting`; 409 if busy; 422 invalid mode/device; unavailable stage → 409. |
| `POST /api/stop` | `{}` → 202 snapshot in `stopping`, or 200 if already idle/error with device released. |
| `POST /api/mode` | `{mode}` → 200 snapshot if accepted; 409 with `STAGE_UNAVAILABLE` otherwise. M0 only accepts raw. |
| `POST /api/transcript/clear` | `{}` → 200 cleared snapshot; idle only, otherwise 409 `INVALID_STATE`. |

Every SSE JSON object: `{v:1,event_id:int,type:string,session_id:string|null,epoch:int,emitted_ns:string,payload:object}`. `event_id` monotonically increases during a service lifetime; a fresh snapshot resets client assumptions after server restart. Types: `snapshot`, `state`, `stage`, `level`, `metrics`, `transcript`, `gap`, `error`. The snapshot is `{state,session_id,epoch,mode,device_id,recording,stages,transcript,last_error,metrics}`. `stages` keys are `capture,rnnoise,hush,asr`; each is `{status,reason,model_revision}` where status is `unavailable|loading|ready|active|failed|bypassed`. `ready` means actually loaded/validated; selected raw's absent filters remain `unavailable`, not `bypassed`.

M0 snapshot: `mode='raw'`; RNNoise `{status:'unavailable',reason:'Not implemented in M0',model_revision:null}` and Hush likewise. Display all four options with the other three disabled and explanatory text. Missing ASR model is `unavailable` plus `MODEL_MISSING`; Start is disabled. A backend mode request cannot bypass these checks. Never silently fall back to Raw or fabricated ASR text.

Transcript payload (also the entry shape in snapshot `transcript`): `{session_id,segment_id,revision,kind:'partial'|'final',text,start_ms,end_ms,mode,epoch,final_reason}`; times are relative to original session sample timeline, not model execution time. The identity key is `(session_id,segment_id)`; segment_id is a UUID and revision increments per segment. Ignore older revisions and a partial after a final. Newly arriving inference may mutate only the currently accepted session/epoch (or the explicitly pending finalization boundary); discard stale results after cancellation/restart. Snapshot `transcript` is a flat list of these entries, including retained committed finals with their original session_id; those historical finals are valid snapshot state and must not be rejected merely because their session differs from the active one. Group entries by session_id in the UI. Pending partials are removed on failed/expired finalization, with a visible error. `final_reason` is null for partials, otherwise `silence|max_duration|stop|mode_switch`. Error payload: `{code,stage,message,recoverable}`. Stable codes include the errors above plus `ASR_LOAD_FAILED`, `ASR_INFERENCE_FAILED`, `ASR_FLUSH_TIMEOUT`, `MODEL_MISSING`, `INVALID_STATE`, `STAGE_UNAVAILABLE`, `RECORDING_FAILED` and `STAGE_FAILED`. HTTP error envelope is `{error:{code,stage,message,recoverable}}`; no stack traces in UI.

Internal states: `loading → idle → starting → listening → stopping → idle`, plus `error`. UI labels: Idle, Listening, Processing (loading/starting/stopping), Error; retain detailed substatus. Listening can coexist with ASR processing: a partial decode does not pretend the microphone stopped. Model readiness occurs before Start. Device open failure closes partial resources and goes to error. Stop first closes capture, drains at most bounded queues, flushes the resampler and final utterance, allows 5 s for final inference, then emits idle. On timeout discard stale results, emit `ASR_FLUSH_TIMEOUT`, leave ASR unavailable/busy until the existing worker exits; never start a second inference thread to work around a hung native call. Capture must remain released even then. Retry Start only when device/model resources are healthy.

Restart generates a new session UUID and epoch 0, resets DSP/ASR state; previous final transcript remains visible with its session grouping until Clear. Limit counts across retained sessions. A future mode switch validates availability first, inserts a serialized boundary, finalizes old utterance, resets DSP buffers/state and starts new epoch at the next 10 ms source boundary. No ASR window spans modes; old-epoch finalization is committed at the boundary before accepting new results. Runtime filter failure stops capture with explicit stage error; no automatic raw bypass. M0 has no active filter switch to simulate.

Browser unload closes SSE; if no subscriber returns within 5 s, stop capture and finalize. Shutdown/KeyboardInterrupt uses the same stop path, then joins workers and frees model resources; native calls cannot be force-killed safely from Python threads. Do not report clean shutdown if an inference worker fails to exit.

## Recording and evidence boundary

Normal Start defaults `record=false`. Permit `record=true` only with service `--dev-recording`; show recording visibly. Writer saves `artifacts/captures/<UTC>-<session-id>/raw.wav` (48 kHz) and `asr-input.wav` (16 kHz raw-resampled) plus `metadata.json`; stop recording automatically at 60 s and surface that state while capture/ASR continue. Metadata includes device, model revision, mode, rates, timestamps, gaps and clipping. Never name M0 output `hush.wav` or `combined.wav`. No audio playback/monitoring loop in M0. Runtime transcripts are memory-only; QA files are user opt-in and gitignored.

Automated fake-source/fake-transcriber tests establish transport, timing bookkeeping, capacity and lifecycle only. A separate real-model WAV smoke test must load the pinned ASR and consume decoded segments. Human H0 alone establishes actual permission/device behavior, live speech experience and feedback. M2 alone can establish this host's real Hush load/inference. T1–T6 and four-mode measurements remain subsequent milestones.
