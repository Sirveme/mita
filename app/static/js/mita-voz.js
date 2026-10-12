/**
 * MitaVoz (zMita-18) — entrada por voz dual para el chat IA.
 *   Estándar: Web Speech API (gratis, en el navegador)
 *   Premium:  OpenAI Whisper (/api/v1/chat-ia/transcribir)
 * Llamar MitaVoz.init() DESPUÉS de que el chat renderice su input-container.
 */
const MitaVoz = (function () {
    'use strict';

    let isRecording = false;
    let currentMode = null;          // 'estandar' | 'premium'
    let mediaRecorder = null;
    let audioChunks = [];
    let btnEstandar, btnPremium, chatInput;
    let recognition = null;

    function init() {
        btnEstandar = document.getElementById('btnVozEstandar');
        btnPremium = document.getElementById('btnVozPremium');
        chatInput = document.getElementById('chat-input');   // ID real del widget
        if (!btnEstandar || !btnPremium || !chatInput) {
            console.warn('[MitaVoz] Elementos no encontrados (¿se inicializó antes que el chat?)');
            return;
        }
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            btnEstandar.disabled = true;
            btnEstandar.title = 'No soportado en este navegador';
        } else {
            initWebSpeech();
        }
        btnEstandar.addEventListener('click', () => toggleRecording('estandar'));
        btnPremium.addEventListener('click', () => toggleRecording('premium'));
    }

    // ---------- Web Speech (Estándar) ----------
    function initWebSpeech() {
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SR();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = 'es-PE';
        recognition.onresult = function (event) {
            let transcript = '';
            for (let i = event.resultIndex; i < event.results.length; i++) transcript += event.results[i][0].transcript;
            chatInput.value = transcript;
        };
        recognition.onerror = function (event) {
            stopRecording();
            if (event.error === 'not-allowed') alert('Permiso de micrófono denegado. Habilítalo en el navegador.');
        };
        recognition.onend = function () { if (currentMode === 'estandar') stopRecording(); };
    }
    function startWebSpeech() { if (recognition) { try { recognition.start(); } catch (e) { /* ya activo */ } } }
    function stopWebSpeech() { if (recognition) { try { recognition.stop(); } catch (e) {} } }

    // ---------- Whisper (Premium) ----------
    async function startWhisperRecording() {
        if (!navigator.mediaDevices || !window.MediaRecorder) { alert('Grabación no soportada en este navegador.'); stopRecording(); return; }
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mime = (window.MediaRecorder && MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) ? 'audio/webm;codecs=opus' : '';
            mediaRecorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
            audioChunks = [];
            mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };
            mediaRecorder.onstop = async () => {
                stream.getTracks().forEach(t => t.stop());
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                await transcribeWithWhisper(audioBlob);
            };
            mediaRecorder.start();
        } catch (error) {
            stopRecording();
            if (error && error.name === 'NotAllowedError') alert('Permiso de micrófono denegado.');
        }
    }
    function stopWhisperRecording() { if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop(); }

    async function transcribeWithWhisper(audioBlob) {
        showTranscribingIndicator();
        try {
            const fd = new FormData();
            fd.append('audio', audioBlob, 'audio.webm');
            const resp = await fetch('/api/v1/chat-ia/transcribir', { method: 'POST', body: fd });
            if (resp.status === 503) { alert('La transcripción Premium no está disponible ahora. Usa el modo Estándar.'); return; }
            if (!resp.ok) throw new Error('HTTP ' + resp.status);
            const data = await resp.json();
            if (data.texto) chatInput.value = data.texto;
        } catch (error) {
            alert('Error al transcribir. Intenta de nuevo.');
        } finally {
            hideTranscribingIndicator();
            stopRecording();
        }
    }

    // ---------- Control ----------
    function toggleRecording(mode) {
        if (isRecording) {
            if (currentMode === mode) stopRecording();
            else { stopRecording(); setTimeout(() => startRecording(mode), 120); }
        } else { startRecording(mode); }
    }
    function startRecording(mode) {
        isRecording = true; currentMode = mode;
        if (mode === 'estandar') { btnEstandar.classList.add('recording'); startWebSpeech(); }
        else { btnPremium.classList.add('recording'); startWhisperRecording(); }
        chatInput.value = '';
        chatInput.placeholder = 'Escuchando…';
    }
    function stopRecording() {
        if (!isRecording) return;
        isRecording = false;
        if (currentMode === 'estandar') { stopWebSpeech(); btnEstandar.classList.remove('recording'); }
        else { stopWhisperRecording(); if (btnPremium) btnPremium.classList.remove('recording'); }
        currentMode = null;
        chatInput.placeholder = 'Escribe o dicta tu problema...';
    }

    // ---------- UI ----------
    function showTranscribingIndicator() {
        if (document.getElementById('transcribingIndicator')) return;
        const el = document.createElement('div');
        el.id = 'transcribingIndicator';
        el.className = 'transcribing-indicator';
        el.innerHTML = '<div class="spinner"></div><span>Transcribiendo con Whisper…</span>';
        const container = document.querySelector('.chat-input-container');
        if (container && container.parentNode) container.parentNode.insertBefore(el, container);
    }
    function hideTranscribingIndicator() { const el = document.getElementById('transcribingIndicator'); if (el) el.remove(); }

    return { init: init, stop: stopRecording };
})();

window.MitaVoz = MitaVoz;
