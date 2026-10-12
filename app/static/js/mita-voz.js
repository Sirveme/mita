/**
 * MitaVoz v3 (zMita-20) — entrada por voz con feedback claro e init idempotente.
 *   Estándar: Web Speech API (continuo, acumula finales, no se auto-envía).
 *   Premium:  MediaRecorder -> OpenAI Whisper (/api/v1/chat-ia/transcribir).
 * Llamar MitaVoz.init() tras renderizar el chat. Es idempotente (usa btn.onclick).
 */
console.log('[MitaVoz] ====== DEBUG INFO ======');
console.log('[MitaVoz] URL:', (typeof window !== 'undefined') ? window.location.href : '?');
console.log('[MitaVoz] HTTPS:', (typeof window !== 'undefined') && window.location.protocol === 'https:');
console.log('[MitaVoz] SpeechRecognition:', (typeof window !== 'undefined') && ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window));
console.log('[MitaVoz] getUserMedia:', (typeof navigator !== 'undefined') && !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia));
console.log('[MitaVoz] ========================');

const MitaVoz = (function () {
    'use strict';
    const PLACEHOLDER = 'Escribe o dicta tu problema...';
    let initCount = 0;
    let isRecording = false;
    let currentMode = null;      // 'estandar' | 'premium'
    let mediaRecorder = null;
    let audioChunks = [];
    let recognition = null;
    let textoBase = '';          // texto ya presente en el input al empezar
    let btnEstandar = null, btnPremium = null, voiceStatus = null;
    // Medidor de micrófono (Parte A)
    const UMBRAL_RMS = 0.01;
    let audioCtx = null, analyser = null, meterStream = null, meterTimer = null, meterWarnTimer = null;
    let peakRMS = 0, meterInicio = 0, recInicio = 0;

    const MIC_MSG = 'Tu micrófono no capta sonido. Revisa cuál está seleccionado en el navegador (ícono 🎤 en la barra de direcciones).';

    async function startMeter(existingStream) {
        peakRMS = 0; meterInicio = Date.now();
        try {
            meterStream = existingStream || await navigator.mediaDevices.getUserMedia({ audio: true });
        } catch (e) { console.warn('[MitaVoz] medidor: sin stream', e); return null; }
        try {
            const AC = window.AudioContext || window.webkitAudioContext;
            audioCtx = new AC();
            const src = audioCtx.createMediaStreamSource(meterStream);
            analyser = audioCtx.createAnalyser(); analyser.fftSize = 512;
            src.connect(analyser);
            const buf = new Uint8Array(analyser.fftSize);
            const dev = document.getElementById('voice-device');
            const track = meterStream.getAudioTracks()[0];
            if (dev && track) dev.textContent = '🎤 ' + (track.label || 'micrófono');
            const bars = voiceStatus ? voiceStatus.querySelectorAll('.vm-bar') : [];
            meterTimer = setInterval(() => {
                analyser.getByteTimeDomainData(buf);
                let sum = 0;
                for (let i = 0; i < buf.length; i++) { const v = (buf[i] - 128) / 128; sum += v * v; }
                const rms = Math.sqrt(sum / buf.length);
                if (rms > peakRMS) peakRMS = rms;
                const nivel = Math.min(1, rms * 6);
                bars.forEach((b, i) => { b.style.transform = 'scaleY(' + Math.max(0.12, Math.min(1, nivel * (0.5 + i * 0.18))) + ')'; });
            }, 80);
            meterWarnTimer = setTimeout(() => { if (peakRMS < UMBRAL_RMS) showStatus(MIC_MSG, 'error'); }, 3000);
        } catch (e) { console.warn('[MitaVoz] medidor no disponible', e); }
        return meterStream;
    }
    function stopMeter(closeStream) {
        if (meterTimer) { clearInterval(meterTimer); meterTimer = null; }
        if (meterWarnTimer) { clearTimeout(meterWarnTimer); meterWarnTimer = null; }
        try { if (audioCtx) audioCtx.close(); } catch (e) {}
        audioCtx = null; analyser = null;
        if (closeStream && meterStream) { try { meterStream.getTracks().forEach(t => t.stop()); } catch (e) {} }
        meterStream = null;
        const dev = document.getElementById('voice-device'); if (dev) dev.textContent = '';
        return peakRMS;
    }

    function getInput() {
        return document.getElementById('chat-input') || document.getElementById('chatInput') || document.querySelector('.chat-input-container input');
    }

    function init() {
        initCount++;
        console.log('[MitaVoz] init #' + initCount);
        btnEstandar = document.getElementById('btnVozEstandar') || document.querySelector('.btn-voz-estandar');
        btnPremium = document.getElementById('btnVozPremium') || document.querySelector('.btn-voz-premium');
        const input = getInput();
        if (!btnEstandar && !btnPremium) { console.warn('[MitaVoz] Botones no encontrados'); return false; }
        if (!input) { console.warn('[MitaVoz] Input de chat no encontrado'); return false; }

        ensureStatusElement(input);

        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            if (btnEstandar) { btnEstandar.disabled = true; btnEstandar.title = 'No soportado (solo Chrome/Edge)'; btnEstandar.style.opacity = '0.5'; }
        } else if (!recognition) {
            initWebSpeech();
        }
        // Idempotente: onclick reemplaza cualquier handler anterior (no se acumulan)
        if (btnEstandar && !btnEstandar.disabled) btnEstandar.onclick = () => toggleRecording('estandar');
        if (btnPremium) btnPremium.onclick = () => toggleRecording('premium');
        console.log('[MitaVoz] ✅ init listo');
        return true;
    }

    function ensureStatusElement(input) {
        voiceStatus = document.getElementById('voice-status');
        if (voiceStatus && document.body.contains(voiceStatus)) return;
        voiceStatus = document.createElement('div');
        voiceStatus.id = 'voice-status';
        voiceStatus.className = 'voice-status hidden';
        voiceStatus.innerHTML = `
            <div class="voice-status-content">
                <div class="voice-indicator"></div>
                <div class="voice-meter" aria-hidden="true"><span class="vm-bar"></span><span class="vm-bar"></span><span class="vm-bar"></span><span class="vm-bar"></span><span class="vm-bar"></span></div>
                <span class="voice-status-text">Escuchando…</span>
                <button type="button" class="voice-stop-btn" title="Detener">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
                </button>
            </div>
            <div class="voice-device" id="voice-device"></div>`;
        const container = input.closest('.chat-input-container') || input.parentElement;
        if (container && container.parentNode) container.parentNode.insertBefore(voiceStatus, container);
        const stopBtn = voiceStatus.querySelector('.voice-stop-btn');
        if (stopBtn) stopBtn.onclick = stopRecording;
    }

    // ---------- Web Speech ----------
    function initWebSpeech() {
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SR();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'es-PE';
        recognition.onstart = () => { console.log('[MitaVoz] start estandar'); showStatus('Habla ahora… toca ⬛ para terminar', 'recording'); };
        recognition.onresult = (event) => {
            let finales = '', parcial = '';
            for (let i = 0; i < event.results.length; i++) {
                const t = event.results[i][0].transcript;
                if (event.results[i].isFinal) finales += t + ' '; else parcial += t;
            }
            const inp = getInput(); if (inp) inp.value = (textoBase + finales + parcial).trim();
            console.log('[MitaVoz] onresult ' + event.results.length + ' resultados');
        };
        recognition.onerror = (event) => {
            console.error('[MitaVoz] error ' + event.error);
            let msg = 'Error de reconocimiento';
            if (event.error === 'not-allowed') { msg = 'Permiso de micrófono denegado.'; alert(msg); }
            else if (event.error === 'no-speech') msg = MIC_MSG;
            else if (event.error === 'audio-capture') msg = MIC_MSG;
            else if (event.error === 'network') msg = 'Error de red';
            showStatus(msg, 'error');
            if (event.error !== 'no-speech') setTimeout(() => stopRecording(), 1500);
        };
        recognition.onend = () => {
            console.log('[MitaVoz] onend');
            if (isRecording && currentMode === 'estandar') {
                // Modo continuo: acumular lo transcrito y reiniciar sin borrar el input
                const inp = getInput(); textoBase = (inp && inp.value ? inp.value + ' ' : textoBase);
                try { recognition.start(); } catch (e) { /* InvalidStateError: ya corriendo */ }
            }
        };
    }

    // ---------- Whisper ----------
    async function startWhisperRecording() {
        try {
            showStatus('Solicitando acceso al micrófono…', 'loading');
            if (!navigator.mediaDevices || !window.MediaRecorder) throw new Error('MediaRecorder no soportado');
            const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
            showStatus('Grabando… toca ⬛ para terminar', 'recording-premium');
            let mimeType = 'audio/webm;codecs=opus';
            if (!MediaRecorder.isTypeSupported(mimeType)) mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : (MediaRecorder.isTypeSupported('audio/mp4') ? 'audio/mp4' : '');
            mediaRecorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
            audioChunks = [];
            mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };
            mediaRecorder.onstop = async () => {
                const dur = (Date.now() - recInicio) / 1000;
                const peak = stopMeter(false);     // leer pico antes de cerrar el stream
                stream.getTracks().forEach(t => t.stop());
                if (!audioChunks.length || dur < 0.8) { showStatus('Habla un poco más y vuelve a intentar.', 'error'); setTimeout(hideStatus, 2500); return; }
                if (peak < UMBRAL_RMS) { showStatus(MIC_MSG, 'error'); setTimeout(hideStatus, 4000); return; }
                const blob = new Blob(audioChunks, { type: (mediaRecorder.mimeType || 'audio/webm') });
                console.log('[MitaVoz] audio blob:', blob.size, 'bytes, dur', dur.toFixed(1), 's, peak', peak.toFixed(3));
                await transcribeWithWhisper(blob);
            };
            mediaRecorder.onerror = (e) => { console.error('[MitaVoz] error MediaRecorder', e.error); showStatus('Error de grabación', 'error'); stopRecording(); };
            mediaRecorder.start(1000);
            startMeter(stream);   // medidor reutiliza el mismo stream
        } catch (error) {
            console.error('[MitaVoz] error micrófono', error);
            if (error && error.name === 'NotAllowedError') alert('Permiso de micrófono denegado. Habilítalo en el navegador.');
            else if (error && error.name === 'NotFoundError') alert('No se encontró ningún micrófono.');
            else alert('Error al acceder al micrófono.');
            stopRecording();
        }
    }

    async function transcribeWithWhisper(audioBlob) {
        showStatus('Transcribiendo con Whisper…', 'loading');
        try {
            const fd = new FormData();
            const ext = (audioBlob.type && audioBlob.type.indexOf('mp4') >= 0) ? 'mp4' : 'webm';
            fd.append('audio', audioBlob, 'audio.' + ext);
            const resp = await fetch('/api/v1/chat-ia/transcribir', { method: 'POST', body: fd });
            console.log('[MitaVoz] /transcribir', resp.status);
            if (resp.status === 503) { showStatus('Premium no disponible ahora. Usa Estándar.', 'error'); return; }
            if (!resp.ok) { const t = await resp.text(); throw new Error('HTTP ' + resp.status + ': ' + t); }
            const data = await resp.json();
            const inp = getInput();
            if (data.motivo === 'sin_voz') { showStatus(MIC_MSG, 'error'); return; }
            if (data.texto && inp) { inp.value = data.texto; showStatus('✓ Listo — revisa y presiona Enviar', 'success'); inp.focus(); }
            else showStatus(MIC_MSG, 'error');
        } catch (error) {
            console.error('[MitaVoz] error Whisper', error);
            showStatus('Error al transcribir', 'error');
        } finally {
            setTimeout(() => { hideStatus(); }, 2500);
        }
    }

    // ---------- Control ----------
    function toggleRecording(mode) {
        console.log('[MitaVoz] toggle ' + mode + ' (isRecording=' + isRecording + ')');
        if (isRecording) stopRecording(); else startRecording(mode);
    }
    function startRecording(mode) {
        console.log('[MitaVoz] start ' + mode);
        const inp = getInput(); if (!inp) return;
        isRecording = true; currentMode = mode; recInicio = Date.now();
        textoBase = (inp.value || '').trim();     // no borramos lo ya escrito
        if (textoBase) textoBase += ' ';
        inp.placeholder = 'Habla ahora… toca ⬛ para terminar';
        if (mode === 'estandar' && btnEstandar) { btnEstandar.classList.add('recording'); startMeter(); try { recognition.start(); } catch (e) { /* ya corriendo */ } }
        else if (mode === 'premium' && btnPremium) { btnPremium.classList.add('recording'); startWhisperRecording(); }
    }
    function stopRecording() {
        if (!isRecording) return;
        const mode = currentMode;
        console.log('[MitaVoz] stop (' + mode + ')');
        isRecording = false; currentMode = null;
        const inp = getInput();
        if (mode === 'estandar') {
            if (recognition) { try { recognition.stop(); } catch (e) {} }
            stopMeter(true);
            if (btnEstandar) btnEstandar.classList.remove('recording');
            const val = (inp && inp.value || '').trim();
            if (val) { showStatus('✓ Listo — revisa y presiona Enviar', 'success'); if (inp) inp.focus(); }
            else { showStatus('No te escuché, intenta de nuevo', 'error'); }
            setTimeout(hideStatus, 2500);
        } else if (mode === 'premium') {
            if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
            if (btnPremium) btnPremium.classList.remove('recording');
            // El estado lo maneja transcribeWithWhisper
        }
        if (inp) inp.placeholder = PLACEHOLDER;
    }

    // ---------- Status UI ----------
    function showStatus(text, type) {
        if (!voiceStatus) return;
        voiceStatus.classList.remove('hidden', 'recording', 'recording-premium', 'loading', 'error', 'success');
        voiceStatus.classList.add(type);
        const el = voiceStatus.querySelector('.voice-status-text'); if (el) el.textContent = text;
    }
    function hideStatus() { if (voiceStatus) voiceStatus.classList.add('hidden'); }

    return { init, stop: stopRecording, isRecording: () => isRecording, _initCount: () => initCount };
})();

window.MitaVoz = MitaVoz;
console.log('[MitaVoz] Módulo cargado (esperando init)');
