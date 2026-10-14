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
    // Conversación por voz (manos libres)
    let _onAutoEnviar = null, _ultimoModo = null, _reaperturas = 0, _reapertura = false;
    let _finalTimer = null, _vozDetectada = false, _silencioDesde = 0, _autoEnviarPremium = false;
    const UMBRAL_SILENCIO = 0.012, SILENCIO_MS = 1300, FINAL_MS = 1200, MAX_REC_MS = 30000;
    function onAutoEnviar(cb) { _onAutoEnviar = cb; }
    function ultimoModo() { return _ultimoModo; }
    function _dispararAutoEnvio() {
        const inp = getInput();
        if (inp && (inp.value || '').trim() && _onAutoEnviar) { _reaperturas = 0; try { _onAutoEnviar(); } catch (e) {} }
    }

    // Ventana de edición antes del auto-envío (Parte B, zMita-31):
    // el texto aparece 1.5 s con un botón ✏️; tocar ✏️ o el input cancela el envío.
    let _autoEnvioTimer = null, _editarBtn = null;
    const AUTOENVIO_MS = 1500;
    function _quitarBotonEditar() { if (_editarBtn) { try { _editarBtn.remove(); } catch (e) {} _editarBtn = null; } }
    function _cancelarAutoEnvio(inp) {
        if (_autoEnvioTimer) { clearTimeout(_autoEnvioTimer); _autoEnvioTimer = null; }
        _quitarBotonEditar();
        showStatus('Revisa el texto y presiona Enviar', 'success');
        setTimeout(hideStatus, 2000);
        if (inp) { try { inp.focus(); } catch (e) {} }
    }
    function _programarAutoEnvio(inp) {
        if (!inp || !(inp.value || '').trim()) return;
        if (_autoEnvioTimer) clearTimeout(_autoEnvioTimer);
        marcarDictado();
        showStatus('Enviando en un momento… toca ✏️ o el texto para editar', 'success');
        _quitarBotonEditar();
        _editarBtn = document.createElement('button');
        _editarBtn.type = 'button'; _editarBtn.className = 'voice-edit-btn'; _editarBtn.textContent = '✏️ Editar';
        const cancelar = () => _cancelarAutoEnvio(inp);
        _editarBtn.addEventListener('click', cancelar);
        const cont = inp.closest('.chat-input-container') || inp.parentElement;
        if (cont && cont.parentNode) cont.parentNode.insertBefore(_editarBtn, cont);
        inp.addEventListener('focus', cancelar, { once: true });
        inp.addEventListener('input', cancelar, { once: true });
        _autoEnvioTimer = setTimeout(() => {
            _autoEnvioTimer = null; _quitarBotonEditar();
            try { inp.removeEventListener('focus', cancelar); inp.removeEventListener('input', cancelar); } catch (e) {}
            showStatus('Enviando…', 'success');
            _dispararAutoEnvio();
        }, AUTOENVIO_MS);
    }
    function reabrir() {
        // Reabre el micrófono en el último modo (modo conversación)
        if (isRecording || !_ultimoModo) return false;
        if (_reaperturas >= 2) { _reaperturas = 0; return false; }  // 2 reaperturas sin hablar -> parar
        _reaperturas += 1;
        _reapertura = true;   // si no capta voz, cerrar en silencio (sin error en el hilo)
        startRecording(_ultimoModo);
        return true;
    }

    // Aviso de "sin voz": en una reapertura de conversación se cierra en silencio
    function _avisoSinVoz(msg) {
        if (_reapertura) { _reapertura = false; hideStatus(); return; }
        showStatus(msg, 'error');
    }

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
                // Detección de silencio (Premium, manos libres): tras hablar, 1.3 s en silencio -> enviar
                if (currentMode === 'premium' && isRecording) {
                    const ahora = Date.now();
                    if (rms >= UMBRAL_SILENCIO) { _vozDetectada = true; _silencioDesde = 0; }
                    else if (_vozDetectada) { if (!_silencioDesde) _silencioDesde = ahora; else if (ahora - _silencioDesde > SILENCIO_MS) { _autoEnviarPremium = true; stopRecording(); } }
                    if (ahora - recInicio > MAX_REC_MS) { _autoEnviarPremium = true; stopRecording(); }   // tope 30 s
                }
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
            let hayFinal = false;
            for (let i = 0; i < event.results.length; i++) {
                const t = event.results[i][0].transcript;
                if (event.results[i].isFinal) { finales += t + ' '; hayFinal = true; } else parcial += t;
            }
            const inp = getInput(); if (inp) inp.value = (textoBase + finales + parcial).trim();
            console.log('[MitaVoz] onresult ' + event.results.length + ' resultados');
            // Envío automático: 1.2 s tras el último resultado final sin nuevos
            if (_finalTimer) clearTimeout(_finalTimer);
            if (hayFinal) _finalTimer = setTimeout(() => { if (currentMode === 'estandar' && isRecording) { stopRecording(); _programarAutoEnvio(getInput()); } }, FINAL_MS);
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
                if (!audioChunks.length || dur < 0.8) { _avisoSinVoz('Habla un poco más y vuelve a intentar.'); setTimeout(hideStatus, 2500); return; }
                if (peak < UMBRAL_RMS) { _avisoSinVoz(MIC_MSG); setTimeout(hideStatus, 4000); return; }
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
            if (data.motivo === 'sin_voz') { _avisoSinVoz(MIC_MSG); return; }
            if (data.texto && inp) {
                _reapertura = false;   // sí captó voz
                inp.value = data.texto; marcarDictado();
                if (_autoEnviarPremium) { _autoEnviarPremium = false; _programarAutoEnvio(inp); }
                else { showStatus('✓ Listo — revisa y presiona Enviar', 'success'); inp.focus(); }
            }
            else _avisoSinVoz(MIC_MSG);
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
        if (isRecording) stopRecording(); else { _reapertura = false; startRecording(mode); }
    }
    function startRecording(mode) {
        console.log('[MitaVoz] start ' + mode);
        const inp = getInput(); if (!inp) return;
        detenerVoz();   // cortar cualquier audio del asistente al empezar a grabar
        isRecording = true; currentMode = mode; recInicio = Date.now();
        _ultimoModo = mode; _vozDetectada = false; _silencioDesde = 0; _autoEnviarPremium = false;
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
            if (val) { _reapertura = false; marcarDictado(); showStatus('✓ Listo — revisa y presiona Enviar', 'success'); if (inp) inp.focus(); }
            else { _avisoSinVoz('No te escuché, intenta de nuevo'); }
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

    // ====== Voz de salida (el asistente habla) ======
    let ttsAudio = null;
    let ultimoDictadoTs = 0;

    function marcarDictado() { ultimoDictadoTs = Date.now(); }
    function ultimoDictado() { return ultimoDictadoTs; }

    let _cancelTts = false;

    function detenerVoz() {
        _cancelTts = true;
        if (ttsAudio) { try { ttsAudio.pause(); } catch (e) {} ttsAudio = null; }
        try { if (window.speechSynthesis) speechSynthesis.cancel(); } catch (e) {}
    }

    function _sentencias(t) { return (String(t).match(/[^.!?]+[.!?]*/g) || [String(t)]).map(s => s.trim()).filter(Boolean); }

    function _cargarVoces(cb) {
        const v = (window.speechSynthesis && speechSynthesis.getVoices()) || [];
        if (v.length) { cb(v); return; }
        try { speechSynthesis.onvoiceschanged = () => cb(speechSynthesis.getVoices() || []); } catch (e) { cb([]); }
    }
    function _elegirVozEs(voces) {
        const score = (v) => {
            const n = (v.name || '').toLowerCase(), l = (v.lang || '').toLowerCase();
            if (/online.*natural/.test(n)) return 100;     // Edge neuronales
            if (/google espa/.test(n)) return 90;          // Chrome
            if (l.startsWith('es-pe')) return 80;
            if (l.startsWith('es-419') || l.startsWith('es-us')) return 70;
            if (l.startsWith('es')) return 50;
            return 0;
        };
        return voces.filter(v => /^es/i.test(v.lang || '') || /espa/i.test(v.name || '')).sort((a, b) => score(b) - score(a))[0] || null;
    }
    function _vozEstandar(texto, onEnd) {
        if (!window.speechSynthesis) { if (onEnd) onEnd(); return; }
        _cancelTts = false;
        _cargarVoces((voces) => {
            const voz = _elegirVozEs(voces);
            console.log('[MitaVoz] voz estándar =', voz && voz.name, voz && voz.lang);
            const frases = _sentencias(texto); let i = 0;
            const next = () => {
                if (_cancelTts || i >= frases.length) { if (onEnd) onEnd(); return; }
                const u = new SpeechSynthesisUtterance(frases[i++]);
                if (voz) u.voice = voz; u.lang = (voz && voz.lang) || 'es-PE'; u.rate = 1.0; u.pitch = 1.0;
                u.onend = next; u.onerror = next;
                try { speechSynthesis.speak(u); } catch (e) { next(); }
            };
            next();
        });
    }

    let _lastProv = '', _lastVoz = '';
    async function _pedirAudio(frase) {
        const r = await fetch('/api/v1/chat-ia/hablar', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ texto: frase })
        });
        if (!r.ok) throw new Error('hablar HTTP ' + r.status);
        _lastProv = r.headers.get('X-Proveedor') || ''; _lastVoz = r.headers.get('X-Voz') || '';
        return URL.createObjectURL(await r.blob());
    }
    function _reproducir(url, onFirst) {
        return new Promise((res) => {
            ttsAudio = new Audio(url);
            if (onFirst) onFirst();
            ttsAudio.onended = () => { try { URL.revokeObjectURL(url); } catch (e) {} res(true); };
            ttsAudio.onerror = () => res(false);
            ttsAudio.play().catch(() => res('blocked'));
        });
    }

    async function hablar(texto, opts) {
        texto = (texto || '').trim(); if (!texto) return;
        opts = opts || {};
        detenerVoz(); _cancelTts = false;
        const frases = _sentencias(texto);
        // PREMIUM: pedir 1ª oración y reproducir mientras se piden las siguientes (cola)
        try {
            let siguiente = _pedirAudio(frases[0]);   // prefetch 1ª
            let primera = true;
            for (let i = 0; i < frases.length; i++) {
                if (_cancelTts) return;
                const url = await siguiente;
                if (i + 1 < frases.length) siguiente = _pedirAudio(frases[i + 1]).catch(() => null);
                const r = await _reproducir(url, primera ? opts.onPlay : null);
                primera = false;
                if (r === 'blocked') { if (opts.onBlocked) opts.onBlocked(); return; }
            }
            if (opts.onEnded) opts.onEnded();
            console.log('[MitaVoz] nivel=premium proveedor=' + _lastProv + ' voz=' + _lastVoz);
            return;
        } catch (e) {
            console.warn('[MitaVoz] Premium TTS falló, uso Estándar:', e.message);
            if (opts.onEstandar) opts.onEstandar();
        }
        if (opts.onPlay) opts.onPlay();
        _vozEstandar(texto, opts.onEnded);
    }

    return {
        init, stop: stopRecording, isRecording: () => isRecording, _initCount: () => initCount,
        hablar, detenerVoz, ultimoDictado, onAutoEnviar, reabrir, ultimoModo
    };
})();

window.MitaVoz = MitaVoz;
console.log('[MitaVoz] Módulo cargado (esperando init)');
