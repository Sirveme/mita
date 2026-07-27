/**
 * MITA Custom Alerts
 * Reemplaza alert() y confirm() nativos con modales estilizados
 */

const MitaAlert = {

    // Contenedor de modales
    init() {
        if (document.getElementById('mita-alert-container')) return;

        const container = document.createElement('div');
        container.id = 'mita-alert-container';
        container.innerHTML = `
            <div class="mita-alert-overlay" id="mita-alert-overlay"></div>
            <div class="mita-alert-box" id="mita-alert-box">
                <div class="mita-alert-icon" id="mita-alert-icon"></div>
                <div class="mita-alert-title" id="mita-alert-title"></div>
                <div class="mita-alert-message" id="mita-alert-message"></div>
                <div class="mita-alert-buttons" id="mita-alert-buttons"></div>
            </div>
        `;
        document.body.appendChild(container);

        const style = document.createElement('style');
        style.textContent = `
            .mita-alert-overlay {
                position: fixed; top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0, 0, 0, 0.7); z-index: 9998; display: none;
                backdrop-filter: blur(4px);
            }
            .mita-alert-box {
                position: fixed; top: 50%; left: 50%;
                transform: translate(-50%, -50%) scale(0.9);
                background: #111118; border: 1px solid #2a2a3a; border-radius: 16px;
                padding: 32px; min-width: 320px; max-width: 90%; z-index: 9999; display: none;
                text-align: center; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
                opacity: 0; transition: transform 0.2s, opacity 0.2s;
            }
            .mita-alert-box.show { transform: translate(-50%, -50%) scale(1); opacity: 1; }
            .mita-alert-icon { font-size: 48px; margin-bottom: 16px; }
            .mita-alert-icon.success { color: #22c55e; }
            .mita-alert-icon.error { color: #ef4444; }
            .mita-alert-icon.warning { color: #f59e0b; }
            .mita-alert-icon.info { color: #3b82f6; }
            .mita-alert-icon.question { color: #FFCD11; }
            .mita-alert-title { font-size: 20px; font-weight: 600; color: #ffffff; margin-bottom: 8px; }
            .mita-alert-message { font-size: 14px; color: #888; margin-bottom: 24px; line-height: 1.5; }
            .mita-alert-buttons { display: flex; gap: 12px; justify-content: center; }
            .mita-alert-btn {
                padding: 12px 24px; border-radius: 8px; border: none; font-size: 14px; font-weight: 600;
                cursor: pointer; transition: transform 0.2s, box-shadow 0.2s;
            }
            .mita-alert-btn:hover { transform: translateY(-2px); }
            .mita-alert-btn.primary { background: #FFCD11; color: #000; }
            .mita-alert-btn.secondary { background: transparent; color: #888; border: 1px solid #2a2a3a; }
            .mita-alert-btn.danger { background: #ef4444; color: #fff; }
        `;
        document.head.appendChild(style);
    },

    show(options) {
        this.init();

        const overlay = document.getElementById('mita-alert-overlay');
        const box = document.getElementById('mita-alert-box');
        const icon = document.getElementById('mita-alert-icon');
        const title = document.getElementById('mita-alert-title');
        const message = document.getElementById('mita-alert-message');
        const buttons = document.getElementById('mita-alert-buttons');

        const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ', question: '?' };

        icon.textContent = icons[options.type] || icons.info;
        icon.className = 'mita-alert-icon ' + (options.type || 'info');
        title.textContent = options.title || '';
        message.textContent = options.message || '';

        buttons.innerHTML = '';

        return new Promise((resolve) => {
            if (options.showCancel) {
                const cancelBtn = document.createElement('button');
                cancelBtn.className = 'mita-alert-btn secondary';
                cancelBtn.textContent = options.cancelText || 'Cancelar';
                cancelBtn.onclick = () => { this.hide(); resolve(false); };
                buttons.appendChild(cancelBtn);
            }

            const confirmBtn = document.createElement('button');
            confirmBtn.className = 'mita-alert-btn ' + (options.type === 'error' ? 'danger' : 'primary');
            confirmBtn.textContent = options.confirmText || 'Aceptar';
            confirmBtn.onclick = () => { this.hide(); resolve(true); };
            buttons.appendChild(confirmBtn);

            overlay.style.display = 'block';
            box.style.display = 'block';
            requestAnimationFrame(() => { box.classList.add('show'); });

            const escHandler = (e) => {
                if (e.key === 'Escape') {
                    this.hide(); resolve(false);
                    document.removeEventListener('keydown', escHandler);
                }
            };
            document.addEventListener('keydown', escHandler);
        });
    },

    hide() {
        const overlay = document.getElementById('mita-alert-overlay');
        const box = document.getElementById('mita-alert-box');
        box.classList.remove('show');
        setTimeout(() => { overlay.style.display = 'none'; box.style.display = 'none'; }, 200);
    },

    success(title, message) { return this.show({ type: 'success', title, message }); },
    error(title, message) { return this.show({ type: 'error', title, message }); },
    warning(title, message) { return this.show({ type: 'warning', title, message }); },
    info(title, message) { return this.show({ type: 'info', title, message }); },

    confirm(title, message) {
        return this.show({ type: 'question', title, message, showCancel: true, confirmText: 'Sí', cancelText: 'No' });
    },

    confirmDelete(itemName) {
        return this.show({
            type: 'warning', title: '¿Eliminar?',
            message: `¿Estás seguro de eliminar "${itemName}"? Esta acción no se puede deshacer.`,
            showCancel: true, confirmText: 'Sí, eliminar', cancelText: 'Cancelar'
        });
    }
};

window.MitaAlert = MitaAlert;
