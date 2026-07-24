// ============================================
// INDICADOR DE SESIÓN
// Ruta: app/static/js/components/session-indicator.js
// ============================================

class SessionIndicator {
    constructor() {
        this.init();
    }

    init() {
        // Esperar a que cargue la página
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.render());
        } else {
            this.render();
        }
    }

    render() {
        // Verificar si hay sesión
        const userName = sessionStorage.getItem('userName');
        const userPhone = sessionStorage.getItem('userPhone');
        
        if (!userName) return;

        // Crear indicador
        const indicator = document.createElement('div');
        indicator.id = 'session-indicator';
        indicator.innerHTML = `
            <div class="session-info">
                <span class="session-user">👤 ${userName}</span>
                <button class="session-logout" onclick="sessionIndicator.logout()">Salir</button>
            </div>
        `;

        // Agregar estilos
        const style = document.createElement('style');
        style.textContent = `
            #session-indicator {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                background: rgba(255, 205, 17, 0.95);
                padding: 12px 20px;
                border-radius: 30px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                backdrop-filter: blur(10px);
                animation: slideIn 0.3s ease-out;
            }

            @keyframes slideIn {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }

            .session-info {
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .session-user {
                color: #0f1419;
                font-weight: 600;
                font-size: 0.9rem;
            }

            .session-logout {
                background: #0f1419;
                color: #FFCD11;
                border: none;
                padding: 6px 14px;
                border-radius: 20px;
                font-size: 0.85rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
            }

            .session-logout:hover {
                transform: scale(1.05);
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
            }

            @media (max-width: 768px) {
                #session-indicator {
                    top: 10px;
                    right: 10px;
                    padding: 10px 16px;
                }

                .session-user {
                    font-size: 0.85rem;
                }

                .session-logout {
                    padding: 5px 12px;
                    font-size: 0.8rem;
                }
            }
        `;

        // Agregar al DOM
        document.head.appendChild(style);
        document.body.appendChild(indicator);

        console.log('[Session] Indicador renderizado');
    }

    logout() {
        if (confirm('¿Cerrar sesión?')) {
            // Limpiar storage
            localStorage.clear();
            sessionStorage.clear();
            
            // Redirigir a login
            window.location.href = '/login';
        }
    }
}

// Crear instancia global
const sessionIndicator = new SessionIndicator();
window.sessionIndicator = sessionIndicator;

console.log('[Session] Session Indicator cargado ✅');