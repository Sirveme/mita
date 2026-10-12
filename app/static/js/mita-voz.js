/**
 * MitaVoz v2 (zMita-18/19) — entrada por voz con feedback visible.
 *   Estándar: Web Speech API (continuo, hasta que el usuario pare).
 *   Premium:  MediaRecorder -> OpenAI Whisper (/api/v1/chat-ia/transcribir).
 * Llamar MitaVoz.init() DESPUÉS de que el chat renderice sus botones.
 */
console.log('[MitaVoz] ====== DEBUG INFO ======');
console.log('[MitaVoz] URL:', (typeof window !== 'undefined') ? window.location.href : '?');
console.log('[MitaVoz] HTTPS:', (typeof window !== 'undefined') && window.location.protocol === 'https:');
console.log('[MitaVoz] SpeechRecognition:', (typeof window !== 'undefined') && ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window));
console.log('[MitaVoz] getUserMedia:', (typeof navigator !== 'undefined') && !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia));
console.log('[MitaVoz] ========================');

const MitaVoz = (function () {
    'use strict';

    let isRecording = false;
    let currentMode = null;      // 'estandar' | 'premium'
    let mediaRecorder = null;
    let audioChunks = [];
    let recognition = null;
    let btnEstandar = null, btnPremium = null, chatInput = null, voiceStatus = null;

    function init() {
        console.log('[MitaVoz] Inicializando...');
        btnEstandar = document.getElementById('btnVozEstandar') || document.querySelector('.btn-voz-estandar');
        btnPremium = document.getElementById('btnVozPremium') || document.querySelector('.btn-voz-premium');
        chatInput = document.getElementById('chat-input') || document.getElementById('chatInput') || document.querySelector('.chat-input-container input');
        console.log('[MitaVoz] Elementos:', { btnEstandar: !!btnEstandar, btnPremium: !!btnPremium, chatInput: !!chatInput });

        if (!btnEstandar && !btnPremium) { console.warn('[MitaVoz] Botones de voz no encontrados'); return false; }
        if (!chatInput) { console.warn('[MitaVoz] Input de chat no encontrado'); return false; }

        createStatusElement();

        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            console.warn('[MitaVoz] Web Speech API no soportada');
            if (btnEstandar) { btnEstandar.disabled = true; btnEstandar.title = 'No soportado (solo Chrome/Edge)'; btnEstandar.style.opacity = '0.5'; }
        } else {
            initWebSpeech();
        }
        if (btnEstandar && !btnEstandar.disabled) btnEstandar.addEventListener('click', () => toggleRecording('estandar'));
        if (btnPremium) btnPremium.addEventListener('click', () => toggleRecording('premium'));
        console.log('[MitaVoz] ✅ Inicializado');
        return true;
    }

    function createStatusElement() {
        voiceStatus = document.getElementById('voice-status');
        if (voiceStatus) return;
        voiceStatus = document.createElement('div');
        voiceStatus.id = 'voice-status';
        voiceStatus.className = 'voice-status hidden';
        voiceStatus.innerHTML = `
            <div class="voice-status-content">
                <div class="voice-indicator"></div>
                <span class="voice-status-text">Escuchando…</span>
                <button type="button" class="voice-stop-btn" title="Detener">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
                </button>
            </div>`;
        const inputContainer = chatInput.closest('.chat-input-container') || chatInput.parentElement;
        if (inputContainer && inputContainer.parentNode) inputContainer.parentNode.insertBefore(voiceStatus, inputContainer);
        const stopBtn = voiceStatus.querySelector('.voice-stop-btn');
        if (stopBtn) stopBtn.addEventListener('click', stopRecording);
    }

    // ---------- Web Speech ----------
    function initWebSpeech() {
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SR();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'es-PE';
        recognition.onstart = () => { console.log('[MitaVoz] 🎤 Web Speech iniciado'); showStatus('Escuchando… (habla ahora)', 'recording'); };
        recognition.onresult = (event) => {
            let interim = '', final = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const t = event.results[i][0].transcript;
                if (event.results[i].isFinal) final += t; else interim += t;
            }
            chatInput.value = (final + interim).trim();
            if (interim) showStatus('Escuchando… (click en ⬛ para terminar)', 'recording');
        };
        recognition.onerror = (event) => {
            console.error('[MitaVoz] ❌ Web Speech:', event.error);
            let msg = 'Error de reconocimiento';
            if (event.error === 'not-allowed') { msg = 'Permiso de micrófono denegado.'; alert(msg); }
            else if (event.error === 'no-speech') msg = 'No se detectó voz';
            else if (event.error === 'network') msg = 'Error de red';
            else if (event.error === 'audio-capture') msg = 'No se pudo acceder al micrófono';
            showStatus(msg, 'error');
            setTimeout(() => stopRecording(), 2000);
        };
        recognition.onend = () => {
            console.log('[MitaVoz] Web Speech terminado');
            if (isRecording && currentMode === 'estandar') {
                try { recognition.start(); } catch (e) { stopRecording(); }
            }
        };
    }

    // ---------- Whisper ----------
    async function startWhisperRecording() {
        try {
            showStatus('Solicitando acceso al micrófono…', 'loading');
            if (!navigator.mediaDevices || !window.MediaRecorder) throw new Error('MediaRecorder no soportado');
            const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
            console.log('[MitaVoz] 🎙️ Micrófono obtenido');
            showStatus('Grabando… (click en ⬛ para terminar)', 'recording-premium');
            const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm';
            mediaRecorder = new MediaRecorder(stream, { mimeType });
            audioChunks = [];
            mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };
            mediaRecorder.onstop = async () => {
                stream.getTracks().forEach(t => t.stop());
                if (!audioChunks.length) { showStatus('No se grabó audio', 'error'); setTimeout(hideStatus, 2000); return; }
                const blob = new Blob(audioChunks, { type: mimeType });
                console.log('[MitaVoz] Audio blob:', blob.size, 'bytes');
                await transcribeWithWhisper(blob);
            };
            mediaRecorder.onerror = (e) => { console.error('[MitaVoz] ❌ MediaRecorder:', e.error); showStatus('Error de grabación', 'error'); stopRecording(); };
            mediaRecorder.start(1000);
        } catch (error) {
            console.error('[MitaVoz] ❌ Micrófono:', error);
            if (error && error.name === 'NotAllowedError') alert('Permiso de micrófono denegado. Habilítalo en el navegador.');
            else if (error && error.name === 'NotFoundError') alert('No se encontró ningún micrófono.');
            else alert('Error al acceder al micrófono: ' + (error && error.message));
            stopRecording();
        }
    }

    async function transcribeWithWhisper(audioBlob) {
        showStatus('Transcribiendo con Whisper…', 'loading');
        try {
            const fd = new FormData();
            fd.append('audio', audioBlob, 'audio.webm');
            console.log('[MitaVoz] Enviando a /api/v1/chat-ia/transcribir…');
            const resp = await fetch('/api/v1/chat-ia/transcribir', { method: 'POST', body: fd });
            console.log('[MitaVoz] Respuesta:', resp.status);
            if (resp.status === 503) { showStatus('Transcripción Premium no disponible. Usa Estándar.', 'error'); return; }
            if (!resp.ok) { const t = await resp.text(); throw new Error('HTTP ' + resp.status + ': ' + t); }
            const data = await resp.json();
            if (data.texto) { chatInput.value = data.texto; showStatus('✓ Transcripción completada', 'success'); chatInput.focus(); }
            else showStatus('No se pudo transcribir el audio', 'error');
        } catch (error) {
            console.error('[MitaVoz] ❌ Whisper:', error);
            showStatus('Error al transcribir', 'error');
        } finally {
            setTimeout(() => { hideStatus(); stopRecording(); }, 2000);
        }
    }

    // ---------- Control ----------
    function toggleRecording(mode) {
        console.log('[MitaVoz] Toggle:', mode, 'isRecording:', isRecording);
        if (isRecording) stopRecording(); else startRecording(mode);
    }
    function startRecording(mode) {
        console.log('[MitaVoz] ▶️ Iniciando:', mode);
        isRecording = true; currentMode = mode;
        chatInput.value = '';
        if (mode === 'estandar' && btnEstandar) { btnEstandar.classList.add('recording'); try { recognition.start(); } catch (e) {} }
        else if (mode === 'premium' && btnPremium) { btnPremium.classList.add('recording'); startWhisperRecording(); }
    }
    function stopRecording() {
        console.log('[MitaVoz] ⏹️ Deteniendo');
        if (!isRecording) return;
        isRecording = false;
        if (currentMode === 'estandar') { if (recognition) { try { recognition.stop(); } catch (e) {} } if (btnEstandar) btnEstandar.classList.remove('recording'); }
        else if (currentMode === 'premium') { if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop(); if (btnPremium) btnPremium.classList.remove('recording'); }
        currentMode = null;
        setTimeout(hideStatus, 1500);
    }

    // ---------- Status UI ----------
    function showStatus(text, type) {
        if (!voiceStatus) return;
        voiceStatus.classList.remove('hidden', 'recording', 'recording-premium', 'loading', 'error', 'success');
        voiceStatus.classList.add(type);
        const el = voiceStatus.querySelector('.voice-status-text'); if (el) el.textContent = text;
    }
    function hideStatus() { if (voiceStatus) voiceStatus.classList.add('hidden'); }

    return { init, stop: stopRecording, isRecording: () => isRecording };
})();

window.MitaVoz = MitaVoz;
console.log('[MitaVoz] Módulo cargado (esperando init)');
