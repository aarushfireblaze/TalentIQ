(function() {
    'use strict';

    let eventSource = null;
    let currentState = 'idle';
    let currentSessionId = '';
    let currentMode = 'raw';
    let lastConfirmedMode = 'raw';
    let transcript = [];
    let devices = [];

    const statusEl = document.getElementById('status');
    const deviceSelect = document.getElementById('device');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const meterEl = document.getElementById('meter');
    const meterDbEl = document.getElementById('meterDb');
    const transcriptEl = document.getElementById('transcript');
    const copyBtn = document.getElementById('copyBtn');
    const clearBtn = document.getElementById('clearBtn');
    const asrStatusEl = document.getElementById('asrStatus');
    const errorBanner = document.getElementById('errorBanner');
    const permissionNotice = document.getElementById('permissionNotice');
    const rnnoiseRadio = document.getElementById('rnnoiseRadio');
    const rnnoiseLabel = document.getElementById('rnnoiseLabel');
    const rnnoiseStatusEl = document.getElementById('rnnoiseStatus');
    const rnnoiseInfoEl = document.getElementById('rnnoiseInfo');
    const rnnoiseMetricsEl = document.getElementById('rnnoiseMetrics');
    const metricsSection = document.getElementById('metricsSection');
    const rawLabel = document.getElementById('rawLabel');
    const rawStatus = document.getElementById('rawStatus');

    function init() {
        fetchDevices();
        fetchState();
        connectSSE();
        startBtn.addEventListener('click', handleStart);
        stopBtn.addEventListener('click', handleStop);
        copyBtn.addEventListener('click', handleCopy);
        clearBtn.addEventListener('click', handleClear);

        document.querySelectorAll('input[name="mode"]').forEach(radio => {
            radio.addEventListener('change', handleModeChange);
        });
    }

    async function fetchState() {
        try {
            const resp = await fetch('/api/state');
            const snap = await resp.json();
            applySnapshot(snap);
        } catch (e) {
            console.error('Failed to fetch initial state:', e);
        }
    }

    async function fetchDevices() {
        try {
            const resp = await fetch('/api/devices');
            const data = await resp.json();
            devices = data.devices || [];
            deviceSelect.innerHTML = '';
            if (devices.length === 0) {
                deviceSelect.innerHTML = '<option value="">No devices found</option>';
            } else {
                devices.forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d.id;
                    opt.textContent = d.name;
                    if (d.id === data.default_device_id) opt.selected = true;
                    deviceSelect.appendChild(opt);
                });
                deviceSelect.disabled = false;
            }
        } catch (e) {
            console.error('Failed to fetch devices:', e);
        }
    }

    function connectSSE() {
        if (eventSource) eventSource.close();
        eventSource = new EventSource('/api/events');

        eventSource.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                handleEvent(data);
            } catch (e) {
                console.error('Failed to parse event:', e);
            }
        };

        eventSource.onerror = function() {
            startBtn.disabled = true;
            updateStatus('error');
            showError('Disconnected from server. Reconnecting...');
        };

        eventSource.onopen = function() {
            hideError();
            if (currentState === 'idle') {
                startBtn.disabled = false;
            }
        };
    }

    function handleEvent(event) {
        switch (event.type) {
            case 'snapshot':
                applySnapshot(event.payload);
                break;
            case 'state':
                updateStatus(event.payload.state);
                break;
            case 'level':
                updateMeter(event.payload.rms_dbfs, event.payload.peak_dbfs);
                break;
            case 'transcript':
                handleTranscriptEvent(event.payload);
                break;
            case 'error':
                showError(event.payload.message);
                break;
        }
    }

    function applySnapshot(snap) {
        updateStatus(snap.state);
        currentSessionId = snap.session_id || '';
        currentMode = snap.mode || 'raw';
        lastConfirmedMode = currentMode;

        if (snap.stages) {
            if (snap.stages.asr) {
                asrStatusEl.textContent = snap.stages.asr.status;
                asrStatusEl.className = snap.stages.asr.status === 'ready' || snap.stages.asr.status === 'active' ? '' : 'unavailable';
            }
            if (snap.stages.rnnoise) {
                const rn = snap.stages.rnnoise;
                rnnoiseInfoEl.textContent = rn.status;
                rnnoiseInfoEl.className = (rn.status === 'ready' || rn.status === 'active') ? '' : 'unavailable';

                if (rn.status === 'ready' || rn.status === 'active') {
                    rnnoiseRadio.disabled = false;
                    rnnoiseLabel.classList.remove('disabled');
                    rnnoiseStatusEl.textContent = rn.status === 'active' ? 'Processing' : 'Available';
                    rnnoiseStatusEl.className = 'mode-status';
                } else if (rn.status === 'failed') {
                    rnnoiseRadio.disabled = true;
                    rnnoiseLabel.classList.add('disabled');
                    rnnoiseLabel.classList.remove('active');
                    rnnoiseStatusEl.textContent = 'Failed: ' + (rn.reason || 'unknown');
                    rnnoiseStatusEl.className = 'mode-status unavailable';
                } else {
                    rnnoiseRadio.disabled = true;
                    rnnoiseLabel.classList.add('disabled');
                    rnnoiseLabel.classList.remove('active');
                    rnnoiseStatusEl.textContent = rn.reason || 'Unavailable';
                    rnnoiseStatusEl.className = 'mode-status unavailable';
                }
            }
        }

        if (snap.metrics) {
            const m = snap.metrics;
            if (m.rnnoise_avg_ms != null) {
                metricsSection.style.display = '';
                rnnoiseMetricsEl.textContent = 'avg=' + m.rnnoise_avg_ms.toFixed(2) + 'ms p95=' + (m.rnnoise_p95_ms != null ? m.rnnoise_p95_ms.toFixed(2) : '--') + 'ms frames=' + (m.rnnoise_total_frames || 0);
            }
        }

        document.querySelectorAll('input[name="mode"]').forEach(r => {
            if (r.value === currentMode) r.checked = true;
        });

        updateModeSelection();
        updatePendingMode(snap.pending_mode);

        if (snap.transcript) {
            transcript = snap.transcript;
            renderTranscript();
        }

        updateButtons();
    }

    function updateStatus(state) {
        currentState = state;
        statusEl.textContent = state.charAt(0).toUpperCase() + state.slice(1);
        statusEl.className = 'status ' + state;
        updateButtons();
        updateModeSelection();
        permissionNotice.style.display = 'none';
    }

    function updateButtons() {
        const isIdle = currentState === 'idle';
        const isError = currentState === 'error';
        startBtn.disabled = !isIdle && !isError;
        stopBtn.disabled = isIdle || currentState === 'stopping';
        clearBtn.disabled = !isIdle;
        deviceSelect.disabled = !isIdle;
    }

    function updateModeSelection() {
        const isListening = currentState === 'listening';
        if (currentMode === 'raw') {
            rawLabel.classList.add('active');
            rawLabel.classList.remove('disabled');
            rawStatus.textContent = isListening ? 'Processing' : 'Selected';
            rawStatus.className = 'mode-status active';
            rnnoiseLabel.classList.remove('active');
            if (!rnnoiseRadio.disabled) {
                rnnoiseStatusEl.textContent = 'Available';
                rnnoiseStatusEl.className = 'mode-status';
            }
        } else if (currentMode === 'rnnoise') {
            rnnoiseLabel.classList.add('active');
            rnnoiseStatusEl.textContent = isListening ? 'Processing' : 'Selected';
            rnnoiseStatusEl.className = 'mode-status active';
            rawLabel.classList.remove('active');
            rawStatus.textContent = 'Available';
            rawStatus.className = 'mode-status';
        }
    }

    function updatePendingMode(pending) {
        if (!pending) return;
        if (pending === 'rnnoise') {
            rnnoiseLabel.classList.remove('active');
            rnnoiseStatusEl.textContent = 'Switching...';
            rnnoiseStatusEl.className = 'mode-status';
        } else if (pending === 'raw') {
            rawLabel.classList.remove('active');
            rawStatus.textContent = 'Switching...';
            rawStatus.className = 'mode-status';
        }
    }

    function updateMeter(rmsDbfs, peakDbfs) {
        const normalized = Math.max(0, Math.min(100, (rmsDbfs + 60) * (100 / 60)));
        meterEl.style.width = normalized + '%';
        meterDbEl.textContent = rmsDbfs.toFixed(1) + ' dB';
    }

    function handleTranscriptEvent(payload) {
        const idx = transcript.findIndex(t =>
            t.session_id === payload.session_id && t.segment_id === payload.segment_id
        );
        if (payload.kind === 'final') {
            if (idx >= 0) {
                transcript[idx] = payload;
            } else {
                transcript.push(payload);
            }
        } else if (payload.kind === 'partial') {
            const existingPartial = transcript.findIndex(t =>
                t.session_id === payload.session_id && t.kind === 'partial'
            );
            if (existingPartial >= 0) {
                transcript[existingPartial] = payload;
            } else {
                transcript.push(payload);
            }
        }
        renderTranscript();
    }

    function renderTranscript() {
        if (transcript.length === 0) {
            transcriptEl.innerHTML = '<div class="transcript-placeholder">No transcript yet. Press Start to begin.</div>';
            return;
        }

        const grouped = {};
        transcript.forEach(entry => {
            if (!grouped[entry.session_id]) grouped[entry.session_id] = [];
            grouped[entry.session_id].push(entry);
        });

        let html = '';
        for (const [sessionId, entries] of Object.entries(grouped)) {
            html += '<div class="transcript-session-group">';
            entries.forEach(entry => {
                const cls = entry.kind === 'partial' ? 'partial' : 'final';
                const text = escapeHtml(entry.text);
                const modeTag = entry.mode && entry.mode !== 'raw' ? ' [' + entry.mode + ']' : '';
                html += '<div class="transcript-entry ' + cls + '">' + text + '<span class="mode-tag">' + modeTag + '</span></div>';
            });
            html += '</div>';
        }
        transcriptEl.innerHTML = html;
        transcriptEl.scrollTop = transcriptEl.scrollHeight;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async function handleStart() {
        hideError();
        const deviceId = deviceSelect.value || '0';
        const mode = currentMode || 'raw';
        try {
            const resp = await fetch('/api/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Voice-Filtering': '1'
                },
                body: JSON.stringify({
                    device_id: deviceId,
                    mode: mode,
                    record: false
                })
            });
            const data = await resp.json();
            if (data.error) {
                showError(data.error.message);
            } else {
                if (data.mode) currentMode = data.mode;
                updateStatus(data.state || 'listening');
                applySnapshot(data);
            }
        } catch (e) {
            showError('Failed to start: ' + e.message);
        }
    }

    async function handleStop() {
        try {
            const resp = await fetch('/api/stop', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Voice-Filtering': '1'
                },
                body: '{}'
            });
            const data = await resp.json();
            updateStatus(data.state || 'idle');
        } catch (e) {
            showError('Failed to stop: ' + e.message);
        }
    }

    async function handleClear() {
        try {
            const resp = await fetch('/api/transcript/clear', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Voice-Filtering': '1'
                },
                body: '{}'
            });
            const data = await resp.json();
            if (data.error) {
                showError(data.error.message);
            } else {
                transcript = [];
                renderTranscript();
            }
        } catch (e) {
            showError('Failed to clear: ' + e.message);
        }
    }

    function handleCopy() {
        const text = transcript.map(t => t.text).join('\n');
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).catch(() => {
                fallbackCopy(text);
            });
        } else {
            fallbackCopy(text);
        }
    }

    function fallbackCopy(text) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.left = '-9999px';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
        } catch (e) {
            console.error('Copy failed:', e);
        }
        document.body.removeChild(textarea);
    }

    async function handleModeChange(e) {
        const mode = e.target.value;
        currentMode = mode;
        try {
            const resp = await fetch('/api/mode', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Voice-Filtering': '1'
                },
                body: JSON.stringify({ mode: mode })
            });
            const data = await resp.json();
            if (data.error) {
                showError(data.error.message);
                e.target.checked = false;
                currentMode = lastConfirmedMode;
                document.querySelectorAll('input[name="mode"]').forEach(r => {
                    if (r.value === currentMode) r.checked = true;
                });
                updateModeSelection();
            } else {
                applySnapshot(data);
            }
        } catch (e) {
            showError('Failed to switch mode: ' + e.message);
        }
    }

    function showError(message) {
        errorBanner.textContent = message;
        errorBanner.style.display = 'block';
    }

    function hideError() {
        errorBanner.style.display = 'none';
    }

    document.addEventListener('DOMContentLoaded', init);
})();
