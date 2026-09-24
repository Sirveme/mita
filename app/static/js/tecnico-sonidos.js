/* Sonido de alerta para nueva solicitud (Web Audio) + vibración. */
window.MitaSonido = (function () {
    let ctx = null;
    function tono(freq, start, dur) {
        const o = ctx.createOscillator(), g = ctx.createGain();
        o.type = 'sine'; o.frequency.value = freq;
        g.gain.setValueAtTime(0.0001, start);
        g.gain.exponentialRampToValueAtTime(0.13, start + 0.03);
        g.gain.exponentialRampToValueAtTime(0.0001, start + dur);
        o.connect(g); g.connect(ctx.destination); o.start(start); o.stop(start + dur + 0.03);
    }
    function activo() { try { return localStorage.getItem('mita_sonido') !== 'off'; } catch (e) { return true; } }
    function alerta() {
        if (activo()) {
            try {
                ctx = ctx || new (window.AudioContext || window.webkitAudioContext)();
                const t = ctx.currentTime;
                tono(523, t, 0.3); tono(659, t + 0.30, 0.3); tono(784, t + 0.60, 0.34);   // Do-Mi-Sol
            } catch (e) {}
        }
        try { if (navigator.vibrate) navigator.vibrate([200, 100, 200, 100, 400]); } catch (e) {}
    }
    return { alerta, activo };
})();
