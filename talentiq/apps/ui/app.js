(function() {
    'use strict';

    let eventSource = null;
    let currentState = 'idle';
    let transcript = [];

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
    const rnnoiseInfoEl = document.getElementById('rnnoiseInfo');
    const hushInfoEl = document.getElementById('hushInfo');
    const rnnoiseMetricsEl = document.getElementById('rnnoiseMetrics');
    const hushMetricsEl = document.getElementById('hushMetrics');
    const metricsSection = document.getElementById('metricsSection');
    const errorBanner = document.getElementById('errorBanner');
    const permissionNotice = document.getElementById('permissionNotice');
    const recordCheckbox = document.getElementById('recordCheckbox');

    function init() {
        fetchDevices();
        fetchState();
        connectSSE();
        startBtn.addEventListener('click', handleStart);
        stopBtn.addEventListener('click', handleStop);
        copyBtn.addEventListener('click', handleCopy);
        clearBtn.addEventListener('click', handleClear);
    }

    async function fetchState() {
        try {
            applySnapshot(await (await fetch('/api/state')).json());
        } catch (error) {
            showError('Failed to fetch service state: ' + error.message);
        }
    }

    async function fetchDevices() {
        try {
            const data = await (await fetch('/api/devices')).json();
            const devices = data.devices || [];
            deviceSelect.innerHTML = '';
            if (!devices.length) {
                deviceSelect.innerHTML = '<option value="">No devices found</option>';
                return;
            }
            devices.forEach(device => {
                const option = document.createElement('option');
                option.value = device.id;
                option.textContent = device.name;
                option.selected = device.id === data.default_device_id;
                deviceSelect.appendChild(option);
            });
            deviceSelect.disabled = false;
        } catch (error) {
            showError('Failed to load devices: ' + error.message);
        }
    }

    function connectSSE() {
        if (eventSource) eventSource.close();
        eventSource = new EventSource('/api/events');
        eventSource.onmessage = event => {
            try {
                handleEvent(JSON.parse(event.data));
            } catch (error) {
                showError('Failed to parse service event: ' + error.message);
            }
        };
        eventSource.onopen = () => {
            hideError();
            fetchState();
        };
        eventSource.onerror = () => {
            updateStatus('error');
            showError('Disconnected from service. Reconnecting...');
        };
    }

    function handleEvent(event) {
        if (event.type === 'snapshot') applySnapshot(event.payload);
        if (event.type === 'state') updateStatus(event.payload.state);
        if (event.type === 'level') updateMeter(event.payload.rms_dbfs);
        if (event.type === 'transcript') handleTranscriptEvent(event.payload);
        if (event.type === 'error') showError(event.payload.stage + ': ' + event.payload.message);
    }

    function applySnapshot(snapshot) {
        updateStatus(snapshot.state);
        updateStageStatus(snapshot.stages || {});
        updateMetrics(snapshot.metrics || {});
        if (snapshot.transcript) {
            transcript = snapshot.transcript;
            renderTranscript();
        }
        if (snapshot.last_error) showError(snapshot.last_error.stage + ': ' + snapshot.last_error.message);
    }

    function updateStageStatus(stages) {
        updateInfo(asrStatusEl, stages.asr);
        updateInfo(rnnoiseInfoEl, stages.rnnoise);
        updateInfo(hushInfoEl, stages.hush);
    }

    function updateInfo(element, stage) {
        if (!stage) return;
        element.textContent = stage.reason ? stage.status + ': ' + stage.reason : stage.status;
        element.className = stage.status === 'ready' || stage.status === 'active' ? '' : 'unavailable';
    }

    function updateMetrics(metrics) {
        const hasRNNoiseMetrics = metrics.rnnoise_avg_ms != null;
        const hasHushMetrics = metrics.hush_avg_ms != null;
        metricsSection.style.display = hasRNNoiseMetrics || hasHushMetrics ? '' : 'none';
        if (hasRNNoiseMetrics) rnnoiseMetricsEl.textContent = formatMetrics(metrics.rnnoise_avg_ms, metrics.rnnoise_p95_ms, metrics.rnnoise_total_frames);
        if (hasHushMetrics) hushMetricsEl.textContent = formatMetrics(metrics.hush_avg_ms, metrics.hush_p95_ms, metrics.hush_total_frames);
    }

    function formatMetrics(average, p95, frames) {
        return 'avg=' + average.toFixed(2) + 'ms p95=' + (p95 == null ? '--' : p95.toFixed(2)) + 'ms frames=' + (frames || 0);
    }

    function updateStatus(state) {
        currentState = state;
        statusEl.textContent = state.charAt(0).toUpperCase() + state.slice(1);
        statusEl.className = 'status ' + state;
        permissionNotice.style.display = 'none';
        startBtn.disabled = state !== 'idle' && state !== 'error';
        stopBtn.disabled = state === 'idle' || state === 'stopping';
        clearBtn.disabled = state !== 'idle';
        deviceSelect.disabled = state !== 'idle';
    }

    function updateMeter(rmsDbfs) {
        meterEl.style.width = Math.max(0, Math.min(100, (rmsDbfs + 60) * (100 / 60))) + '%';
        meterDbEl.textContent = rmsDbfs.toFixed(1) + ' dB';
    }

    function handleTranscriptEvent(payload) {
        const index = transcript.findIndex(entry => entry.session_id === payload.session_id && entry.segment_id === payload.segment_id);
        if (index >= 0) transcript[index] = payload;
        else transcript.push(payload);
        renderTranscript();
    }

    function renderTranscript() {
        if (!transcript.length) {
            transcriptEl.innerHTML = '<div class="transcript-placeholder">No transcript yet. Press Start to begin.</div>';
            return;
        }
        transcriptEl.innerHTML = transcript.map(entry => '<div class="transcript-entry ' + (entry.kind === 'partial' ? 'partial' : 'final') + '">' + escapeHtml(entry.text) + '</div>').join('');
        transcriptEl.scrollTop = transcriptEl.scrollHeight;
    }

    function escapeHtml(text) {
        const element = document.createElement('div');
        element.textContent = text;
        return element.innerHTML;
    }

    async function handleStart() {
        hideError();
        try {
            const response = await fetch('/api/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-Voice-Filtering': '1'},
                body: JSON.stringify({device_id: deviceSelect.value || '0', record: recordCheckbox.checked})
            });
            const data = await response.json();
            if (data.error) {
                showError(data.error.message);
                if (data.error.code === 'AUDIO_DEVICE_ERROR') permissionNotice.style.display = 'block';
                return;
            }
            applySnapshot(data);
        } catch (error) {
            showError('Failed to start: ' + error.message);
        }
    }

    async function handleStop() {
        try {
            applySnapshot(await (await fetch('/api/stop', {method: 'POST'})).json());
        } catch (error) {
            showError('Failed to stop: ' + error.message);
        }
    }

    async function handleClear() {
        try {
            const data = await (await fetch('/api/transcript/clear', {method: 'POST'})).json();
            if (data.error) showError(data.error.message);
            else {
                transcript = [];
                renderTranscript();
            }
        } catch (error) {
            showError('Failed to clear: ' + error.message);
        }
    }

    function handleCopy() {
        const text = transcript.map(entry => entry.text).join(' ');
        if (navigator.clipboard) navigator.clipboard.writeText(text).catch(() => fallbackCopy(text));
        else fallbackCopy(text);
    }

    function fallbackCopy(text) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.left = '-9999px';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
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
