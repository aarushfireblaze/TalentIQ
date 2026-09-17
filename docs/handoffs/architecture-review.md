# Architecture Review: Voice Filtering System

## Verdicts
- **PRD Scope Compliance**: PASS. The architecture accurately maps to the PRD requirements, including single-boundary resampling, explicitly disabled modes for the M0 baseline, separated capture/inference queues, and detailed timing/error metrics.
- **Architecture Readiness**: PASS WITH CONDITIONS. The core DSP/audio transport contract is well-defined and ready for M0 implementation. However, the ASR scheduling heuristics carry significant design limitations and empirical performance risks that must be measured during M0 to determine if architectural changes are required.

## Review Areas

### 1. Sample, Frame, and Time Contracts
- **Findings**: The architecture defines a robust `AudioFrame` contract (line 57) preserving 48kHz source timing (`seq`, `sample_start`) through resampling boundaries. Hush's exact native constraints (160 samples per call, line 46) and RNNoise's native frame constraints (480 samples, line 50) are correctly mapped without repeated conversions.
- **Status**: Compliant.

### 2. Single Resampling Boundary
- **Findings**: The architecture correctly implements PRD FR-02. It uses a single stateful `soxr.ResampleStream(48000, 16000)` (line 81) applied at the appropriate pipeline location depending on the mode, avoiding repeated resampling.
- **Status**: Compliant.

### 3. Capture and ASR Concurrency Bounds
- **Findings**: The architecture isolates the capture callback from inference and UI. It sets clear, finite bounds: a 1-second ring buffer for capture (line 119), a 1-second DSP-to-ASR ingress queue (line 120), and a maximum 8-second utterance buffer managed by an independent scheduler thread. The inference thread is properly decoupled from audio ingress.
- **Status**: Compliant.

### 4. Stop / Restart / Gap Semantics
- **Findings**: Gap semantics explicitly use an `epoch` counter (line 60) that increments at mode or gap boundaries, ensuring clean resets of stateful DSP models and resamplers. Mode switches insert a serialized boundary, finalizing the old utterance before starting a new epoch (line 153).
- **Status**: Compliant.

### 5. Retained Transcripts
- **Findings**: The snapshot state correctly defines a flat list of `transcript` segments, including historical finals spanning multiple session IDs (line 149). This satisfies the PRD requirement (5.1) that final transcripts remain visible across restarts until explicitly cleared.
- **Status**: Compliant.

### 6. Stage Failures
- **Findings**: Explicit failure modes (`STAGE_UNAVAILABLE`, `MODEL_MISSING`, `MIC_PERMISSION_DENIED`) are surfaced instead of silently bypassing. Unloaded stages correctly report `{status: 'unavailable'}` in the snapshot (line 145), fulfilling PRD FR-10.
- **Status**: Compliant.

### 7. CPU and Latency Feasibility Claims
The architecture introduces two critical areas combining design limitations and empirical risks regarding CPU and latency bounds:

**Definite Design Limitation: Static RMS Gate without VAD**
- **Evidence**: Architecture explicitly disables faster-whisper's VAD (`vad_filter=False`, line 127) and relies solely on an RMS gate baseline (`>-45 dBFS`, line 121) to detect speech and trigger utterance endpoints. 
- **Defect/Risk**: A static RMS gate treating above-threshold noise as speech is a definite design limitation. In noisy environments targeted by the PRD (T2, T3, T4), ambient noise will frequently exceed -45 dBFS, preventing the gate from closing and forcing utterances to the maximum 8 seconds. This may cause hallucinations on pure noise in Raw mode.
- **Recommendation**: Proceed with M0 to measure the baseline impact, as PRD Section 8 deprioritizes ASR optimization. Conduct specific noise-only tests to establish whether the RMS heuristic causes unacceptable Whisper hallucinations or constant 8-second forced cuts. Record these metrics prominently. Provide evidence if the pipeline cannot recover intelligible speech to justify changing to a real VAD or another scheduling approach.

**Empirical Risk: Compute Overhead from Repeated Decoding**
- **Evidence**: "Partial text is produced by repeated bounded-window decoding; this is not a natively streaming Whisper decoder." (line 32)
- **Risk**: To achieve 750ms partial updates (line 122), the architecture repeatedly re-encodes the growing utterance buffer up to 8 seconds. While bounded within an utterance, this redundant decoding creates real compute overhead that scales squarely within each 8-second window, risking the ≤1.5s latency target (PRD P-01).
- **Recommendation**: Instrument and record inference delay for both short and full 8-second windows during M0. State clearly in M0 documentation what the measured delays are to determine if the overhead consistently violates the latency goal.

## Conclusion
The architecture is approved for M0 implementation. The core data model, concurrency, and mode-switching protocols are sound. The implementer should pay strict attention to the documented metric collection to evaluate the ASR heuristic constraints in practice.
