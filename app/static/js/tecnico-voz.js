/* Voz para el técnico: síntesis (anuncio) + reconocimiento ("acepto"/"rechaza"). */
window.MitaVoz = (function () {
    function activo() { try { return localStorage.getItem('mita_voz') !== 'off'; } catch (e) { return true; } }

    function speak(text) {
        if (!activo() || !window.speechSynthesis) return;
        try {
            const u = new SpeechSynthesisUtterance(text);
            u.lang = 'es-PE'; u.rate = 0.9; u.pitch = 1;
            speechSynthesis.cancel(); speechSynthesis.speak(u);
        } catch (e) {}
    }

    let rec = null;
    function listen(onAccept, onReject) {
        if (!activo()) return;
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR) return;
        try {
            rec = new SR(); rec.lang = 'es-PE'; rec.continuous = false; rec.interimResults = false;
            rec.onresult = (e) => {
                const t = (e.results[0][0].transcript || '').toLowerCase();
                if (['acepto', 'aceptar', 'sí', 'si', 'voy', 'ok', 'dale'].some(w => t.includes(w))) onAccept && onAccept();
                else if (['rechazo', 'rechazar', 'no', 'paso'].some(w => t.includes(w))) onReject && onReject();
            };
            rec.onerror = () => {};
            rec.start();
            setTimeout(() => { try { rec && rec.stop(); } catch (e) {} }, 10000);   // 10 s luego pide tocar
        } catch (e) {}
    }
    function stop() { try { rec && rec.stop(); } catch (e) {} try { speechSynthesis.cancel(); } catch (e) {} }
    return { speak, listen, stop, activo };
})();
