/* ============================================
   MITA - UTILIDADES GLOBALES
   ============================================ */

// ========================================
// CONFIGURACIÓN GLOBAL
// ========================================

const CONFIG = {
    API_BASE_URL: '/api',
    TOAST_DURATION: 4000,
    ANIMATION_DURATION: 300
};

// ========================================
// NOTIFICACIONES (TOAST)
// ========================================

function mostrarNotificacion(mensaje, tipo = 'info') {
    // Remover notificación previa si existe
    const prevToast = document.querySelector('.toast-notification');
    if (prevToast) {
        prevToast.remove();
    }
    
    // Crear notificación
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${tipo}`;
    
    // Icono según tipo
    let iconClass = 'fa-info-circle';
    if (tipo === 'success') iconClass = 'fa-check-circle';
    if (tipo === 'error') iconClass = 'fa-exclamation-circle';
    if (tipo === 'warning') iconClass = 'fa-exclamation-triangle';
    
    toast.innerHTML = `
        <span class="toast-icon">${getIconEmoji(tipo)}</span>
        <span class="toast-message">${mensaje}</span>
    `;
    
    // Estilos inline (para funcionar sin CSS adicional)
    Object.assign(toast.style, {
        position: 'fixed',
        top: '80px',
        right: '20px',
        background: 'rgba(26, 35, 50, 0.98)',
        color: 'white',
        padding: '1rem 1.5rem',
        borderRadius: '12px',
        boxShadow: '0 8px 30px rgba(0, 0, 0, 0.3)',
        display: 'flex',
        alignItems: 'center',
        gap: '0.875rem',
        zIndex: '10001',
        maxWidth: '380px',
        opacity: '0',
        transform: 'translateX(400px)',
        transition: 'all 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55)',
        borderLeft: `4px solid ${getToastColor(tipo)}`
    });
    
    // Agregar al body
    document.body.appendChild(toast);
    
    // Mostrar con animación
    setTimeout(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateX(0)';
    }, 100);
    
    // Ocultar y remover
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(400px)';
        setTimeout(() => {
            toast.remove();
        }, 400);
    }, CONFIG.TOAST_DURATION);
}

function getIconEmoji(tipo) {
    const iconos = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️'
    };
    return iconos[tipo] || iconos.info;
}

function getToastColor(tipo) {
    const colores = {
        'success': '#10B981',
        'error': '#EF4444',
        'warning': '#F59E0B',
        'info': '#3B82F6'
    };
    return colores[tipo] || colores.info;
}

// ========================================
// NOTIFICACIONES PANEL
// ========================================

function abrirNotificaciones() {
    console.log('Abrir panel de notificaciones');
    
    // Verificar si ya existe el modal
    let modal = document.getElementById('notificacionesModal');
    
    if (!modal) {
        // Crear modal de notificaciones
        modal = document.createElement('div');
        modal.id = 'notificacionesModal';
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content-panel">
                <div class="modal-header">
                    <h3>Notificaciones</h3>
                    <button class="btn-close-modal" onclick="cerrarModal('notificacionesModal')">
                        ✕
                    </button>
                </div>
                <div class="modal-body">
                    <div class="notification-list">
                        <div class="notification-item unread">
                            <div class="notification-icon">🔔</div>
                            <div class="notification-content">
                                <h4>Servicio completado</h4>
                                <p>Tu cambio de aceite ha sido completado exitosamente</p>
                                <span class="notification-time">Hace 2 horas</span>
                            </div>
                        </div>
                        
                        <div class="notification-item unread">
                            <div class="notification-icon">👨‍🔧</div>
                            <div class="notification-content">
                                <h4>Técnico asignado</h4>
                                <p>Juan Pérez ha sido asignado a tu servicio</p>
                                <span class="notification-time">Hace 5 horas</span>
                            </div>
                        </div>
                        
                        <div class="notification-item">
                            <div class="notification-icon">💰</div>
                            <div class="notification-content">
                                <h4>Pago confirmado</h4>
                                <p>Recibimos tu pago de S/180.00</p>
                                <span class="notification-time">Ayer</span>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn-secondary" onclick="marcarTodasLeidas()">
                        Marcar todas como leídas
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        aplicarEstilosModal(modal);
    }
    
    // Mostrar modal
    modal.style.display = 'flex';
    setTimeout(() => {
        modal.classList.add('show');
    }, 10);
}

// ========================================
// PERFIL DE USUARIO
// ========================================

function abrirPerfil() {
    console.log('Abrir perfil de usuario');
    
    // Verificar si ya existe el modal
    let modal = document.getElementById('perfilModal');
    
    if (!modal) {
        // Crear modal de perfil
        modal = document.createElement('div');
        modal.id = 'perfilModal';
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content-panel">
                <div class="modal-header">
                    <h3>Mi Perfil</h3>
                    <button class="btn-close-modal" onclick="cerrarModal('perfilModal')">
                        ✕
                    </button>
                </div>
                <div class="modal-body">
                    <div class="perfil-container">
                        <div class="perfil-avatar-large">
                            <span>JD</span>
                        </div>
                        <h3>Juan Díaz</h3>
                        <p class="perfil-email">juan.diaz@email.com</p>
                        
                        <div class="perfil-opciones">
                            <a href="/cliente/perfil/editar" class="perfil-opcion">
                                <span class="opcion-icon">👤</span>
                                <span>Editar perfil</span>
                                <span class="arrow">→</span>
                            </a>
                            
                            <a href="/cliente/historial" class="perfil-opcion">
                                <span class="opcion-icon">📋</span>
                                <span>Mis servicios</span>
                                <span class="arrow">→</span>
                            </a>
                            
                            <a href="/cliente/metodos-pago" class="perfil-opcion">
                                <span class="opcion-icon">💳</span>
                                <span>Métodos de pago</span>
                                <span class="arrow">→</span>
                            </a>
                            
                            <a href="/cliente/direcciones" class="perfil-opcion">
                                <span class="opcion-icon">📍</span>
                                <span>Mis direcciones</span>
                                <span class="arrow">→</span>
                            </a>
                            
                            <a href="/cliente/configuracion" class="perfil-opcion">
                                <span class="opcion-icon">⚙️</span>
                                <span>Configuración</span>
                                <span class="arrow">→</span>
                            </a>
                            
                            <a href="#" class="perfil-opcion" onclick="cerrarSesion(); return false;">
                                <span class="opcion-icon">🚪</span>
                                <span>Cerrar sesión</span>
                                <span class="arrow">→</span>
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        aplicarEstilosModal(modal);
    }
    
    // Mostrar modal
    modal.style.display = 'flex';
    setTimeout(() => {
        modal.classList.add('show');
    }, 10);
}

// ========================================
// POLÍTICAS Y GARANTÍAS
// ========================================

function abrirPolitica(tipo) {
    console.log('Abrir política:', tipo);
    
    const contenido = obtenerContenidoPolitica(tipo);
    
    // Crear modal
    const modal = document.createElement('div');
    modal.id = `politicaModal-${tipo}`;
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content-panel modal-large">
            <div class="modal-header">
                <h3>${contenido.titulo}</h3>
                <button class="btn-close-modal" onclick="cerrarModal('politicaModal-${tipo}')">
                    ✕
                </button>
            </div>
            <div class="modal-body">
                ${contenido.html}
            </div>
            <div class="modal-footer">
                <button class="btn-primary" onclick="cerrarModal('politicaModal-${tipo}')">
                    Entendido
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    aplicarEstilosModal(modal);
    
    // Mostrar modal
    modal.style.display = 'flex';
    setTimeout(() => {
        modal.classList.add('show');
    }, 10);
}

function obtenerContenidoPolitica(tipo) {
    const politicas = {
        'garantias': {
            titulo: '🛡️ Garantía de Servicio',
            html: `
                <div class="politica-content">
                    <h4>Nuestra Garantía de 30 Días</h4>
                    <p>En MITA, garantizamos la calidad de todos nuestros servicios por 30 días calendario desde la fecha de realización.</p>
                    
                    <h4>¿Qué cubre la garantía?</h4>
                    <ul>
                        <li>Mano de obra del técnico</li>
                        <li>Repuestos instalados durante el servicio</li>
                        <li>Defectos de instalación o reparación</li>
                    </ul>
                    
                    <h4>¿Qué NO cubre?</h4>
                    <ul>
                        <li>Daños causados por mal uso</li>
                        <li>Desgaste natural de componentes</li>
                        <li>Servicios realizados por terceros</li>
                        <li>Daños por fenómenos naturales</li>
                    </ul>
                    
                    <h4>¿Cómo hacer válida la garantía?</h4>
                    <p>1. Contacta a soporte dentro de los 30 días<br>
                    2. Proporciona el código de servicio<br>
                    3. Describe el problema<br>
                    4. Un técnico evaluará sin costo</p>
                    
                    <div class="info-box">
                        <strong>📞 Contacto:</strong> soporte@serviplus.pe | WhatsApp: +51 999 888 777
                    </div>
                </div>
            `
        },
        'devoluciones': {
            titulo: '↩️ Política de Devoluciones',
            html: `
                <div class="politica-content">
                    <h4>Satisfacción Garantizada</h4>
                    <p>Si no quedas satisfecho con el servicio, tienes derecho a solicitar una devolución.</p>
                    
                    <h4>Condiciones para devolución:</h4>
                    <ul>
                        <li>Solicitud dentro de las primeras 24 horas</li>
                        <li>Problema documentado con fotos/videos</li>
                        <li>El técnico no pudo resolver el problema</li>
                        <li>Servicio no cumplió con lo prometido</li>
                    </ul>
                    
                    <h4>Proceso de devolución:</h4>
                    <ol>
                        <li>Contacta a soporte inmediatamente</li>
                        <li>Explica el motivo de insatisfacción</li>
                        <li>Proporciona evidencia (si aplica)</li>
                        <li>Evaluamos en 24-48 horas</li>
                        <li>Reembolso en 5-7 días hábiles</li>
                    </ol>
                    
                    <h4>Tipos de reembolso:</h4>
                    <ul>
                        <li><strong>100%:</strong> Servicio no realizado</li>
                        <li><strong>50%:</strong> Servicio parcial</li>
                        <li><strong>Servicio nuevo:</strong> Sin cargo adicional</li>
                    </ul>
                    
                    <div class="warning-box">
                        <strong>⚠️ Importante:</strong> No se aceptan devoluciones por cambio de opinión después de completado el servicio satisfactoriamente.
                    </div>
                </div>
            `
        }
    };
    
    return politicas[tipo] || { titulo: 'Información', html: '<p>Contenido no disponible</p>' };
}

// ========================================
// CERRAR MODALES
// ========================================

function cerrarModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => {
            modal.style.display = 'none';
            modal.remove();
        }, CONFIG.ANIMATION_DURATION);
    }
}

// Cerrar modal al hacer click en el overlay
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal-overlay')) {
        const modalId = e.target.id;
        if (modalId) {
            cerrarModal(modalId);
        }
    }
});

// ========================================
// ESTILOS PARA MODALES (INLINE)
// ========================================

function aplicarEstilosModal(modal) {
    // Estilos para el overlay
    Object.assign(modal.style, {
        position: 'fixed',
        top: '0',
        left: '0',
        right: '0',
        bottom: '0',
        background: 'rgba(0, 0, 0, 0.8)',
        display: 'none',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: '10000',
        opacity: '0',
        transition: 'opacity 0.3s ease'
    });
    
    // Aplicar clase show para la animación
    modal.classList.add('show');
    
    // Estilos CSS adicionales (inyectados una sola vez)
    if (!document.getElementById('modal-styles')) {
        const style = document.createElement('style');
        style.id = 'modal-styles';
        style.textContent = `
            .modal-overlay.show {
                opacity: 1 !important;
            }
            
            .modal-content-panel {
                background: #1A2332;
                border-radius: 20px;
                max-width: 500px;
                width: 90%;
                max-height: 80vh;
                overflow: hidden;
                display: flex;
                flex-direction: column;
                animation: modalSlideUp 0.3s ease;
            }
            
            .modal-large {
                max-width: 700px;
            }
            
            @keyframes modalSlideUp {
                from {
                    opacity: 0;
                    transform: translateY(50px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .modal-header {
                padding: 1.5rem;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .modal-header h3 {
                margin: 0;
                color: white;
                font-size: 1.25rem;
            }
            
            .btn-close-modal {
                background: none;
                border: none;
                color: rgba(255, 255, 255, 0.7);
                font-size: 1.5rem;
                cursor: pointer;
                width: 32px;
                height: 32px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                transition: all 0.3s ease;
            }
            
            .btn-close-modal:hover {
                background: rgba(255, 255, 255, 0.1);
                color: white;
            }
            
            .modal-body {
                padding: 1.5rem;
                overflow-y: auto;
                flex: 1;
            }
            
            .modal-footer {
                padding: 1rem 1.5rem;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                display: flex;
                gap: 1rem;
                justify-content: flex-end;
            }
            
            /* Notificaciones */
            .notification-list {
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }
            
            .notification-item {
                display: flex;
                gap: 1rem;
                padding: 1rem;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                transition: background 0.3s ease;
            }
            
            .notification-item.unread {
                background: rgba(255, 205, 17, 0.1);
                border-left: 3px solid #FFCD11;
            }
            
            .notification-item:hover {
                background: rgba(255, 255, 255, 0.08);
            }
            
            .notification-icon {
                font-size: 1.5rem;
                flex-shrink: 0;
            }
            
            .notification-content h4 {
                margin: 0 0 0.25rem 0;
                color: white;
                font-size: 1rem;
            }
            
            .notification-content p {
                margin: 0 0 0.5rem 0;
                color: rgba(255, 255, 255, 0.7);
                font-size: 0.9rem;
            }
            
            .notification-time {
                font-size: 0.8rem;
                color: rgba(255, 255, 255, 0.5);
            }
            
            /* Perfil */
            .perfil-container {
                text-align: center;
            }
            
            .perfil-avatar-large {
                width: 100px;
                height: 100px;
                border-radius: 50%;
                background: #FFCD11;
                color: #1A2332;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 2.5rem;
                font-weight: 700;
                margin: 0 auto 1rem;
            }
            
            .perfil-container h3 {
                margin: 0 0 0.25rem 0;
                color: white;
            }
            
            .perfil-email {
                color: rgba(255, 255, 255, 0.6);
                margin-bottom: 2rem;
            }
            
            .perfil-opciones {
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
            }
            
            .perfil-opcion {
                display: flex;
                align-items: center;
                gap: 1rem;
                padding: 1rem;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                text-decoration: none;
                color: white;
                transition: all 0.3s ease;
            }
            
            .perfil-opcion:hover {
                background: rgba(255, 205, 17, 0.1);
                transform: translateX(5px);
            }
            
            .opcion-icon {
                font-size: 1.5rem;
            }
            
            .perfil-opcion span:nth-child(2) {
                flex: 1;
                text-align: left;
            }
            
            .arrow {
                color: #FFCD11;
            }
            
            /* Políticas */
            .politica-content {
                color: rgba(255, 255, 255, 0.9);
                line-height: 1.6;
            }
            
            .politica-content h4 {
                color: #FFCD11;
                margin-top: 1.5rem;
                margin-bottom: 0.75rem;
            }
            
            .politica-content ul,
            .politica-content ol {
                margin: 0.5rem 0 1rem 1.5rem;
            }
            
            .politica-content li {
                margin-bottom: 0.5rem;
            }
            
            .info-box,
            .warning-box {
                padding: 1rem;
                border-radius: 8px;
                margin-top: 1.5rem;
            }
            
            .info-box {
                background: rgba(59, 130, 246, 0.1);
                border-left: 3px solid #3B82F6;
            }
            
            .warning-box {
                background: rgba(245, 158, 11, 0.1);
                border-left: 3px solid #F59E0B;
            }
            
            /* Botones */
            .btn-primary,
            .btn-secondary {
                padding: 0.75rem 1.5rem;
                border: none;
                border-radius: 12px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            
            .btn-primary {
                background: #FFCD11;
                color: #1A2332;
            }
            
            .btn-primary:hover {
                background: #E6B800;
                transform: translateY(-2px);
            }
            
            .btn-secondary {
                background: rgba(255, 255, 255, 0.1);
                color: white;
            }
            
            .btn-secondary:hover {
                background: rgba(255, 255, 255, 0.15);
            }
        `;
        document.head.appendChild(style);
    }
}

// ========================================
// FUNCIONES ADICIONALES
// ========================================

function marcarTodasLeidas() {
    const items = document.querySelectorAll('.notification-item.unread');
    items.forEach(item => {
        item.classList.remove('unread');
    });
    mostrarNotificacion('Todas las notificaciones marcadas como leídas', 'success');
}

function cerrarSesion() {
    if (confirm('¿Estás seguro que deseas cerrar sesión?')) {
        mostrarNotificacion('Cerrando sesión...', 'info');
        setTimeout(() => {
            window.location.href = '/logout';
        }, 1000);
    }
}

// ========================================
// FORMATEO DE DATOS
// ========================================

function formatearMoneda(valor) {
    return `S/${parseFloat(valor).toFixed(2)}`;
}

function formatearFecha(fecha) {
    const opciones = { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    };
    return new Date(fecha).toLocaleDateString('es-PE', opciones);
}

function formatearHora(fecha) {
    const opciones = { 
        hour: '2-digit', 
        minute: '2-digit' 
    };
    return new Date(fecha).toLocaleTimeString('es-PE', opciones);
}

// ========================================
// VALIDACIONES
// ========================================

function validarEmail(email) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email);
}

function validarTelefono(telefono) {
    const regex = /^(\+51)?[9]\d{8}$/;
    return regex.test(telefono);
}

function validarDNI(dni) {
    const regex = /^\d{8}$/;
    return regex.test(dni);
}

// ========================================
// LOADING OVERLAY
// ========================================

function mostrarLoading(mensaje = 'Cargando...') {
    let loading = document.getElementById('loadingOverlay');
    
    if (!loading) {
        loading = document.createElement('div');
        loading.id = 'loadingOverlay';
        loading.innerHTML = `
            <div class="loading-spinner"></div>
            <p class="loading-text">${mensaje}</p>
        `;
        
        Object.assign(loading.style, {
            position: 'fixed',
            top: '0',
            left: '0',
            right: '0',
            bottom: '0',
            background: 'rgba(0, 0, 0, 0.8)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: '10002',
            color: 'white'
        });
        
        document.body.appendChild(loading);
        
        // Agregar estilos para el spinner
        if (!document.getElementById('loading-styles')) {
            const style = document.createElement('style');
            style.id = 'loading-styles';
            style.textContent = `
                .loading-spinner {
                    width: 50px;
                    height: 50px;
                    border: 4px solid rgba(255, 255, 255, 0.3);
                    border-top-color: #FFCD11;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }
                
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
                
                .loading-text {
                    margin-top: 1rem;
                    font-size: 1.125rem;
                    font-weight: 600;
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    loading.style.display = 'flex';
}

function ocultarLoading() {
    const loading = document.getElementById('loadingOverlay');
    if (loading) {
        loading.style.display = 'none';
    }
}

// ========================================
// EXPORTS GLOBALES
// ========================================

window.mostrarNotificacion = mostrarNotificacion;
window.abrirNotificaciones = abrirNotificaciones;
window.abrirPerfil = abrirPerfil;
window.abrirPolitica = abrirPolitica;
window.cerrarModal = cerrarModal;
window.marcarTodasLeidas = marcarTodasLeidas;
window.cerrarSesion = cerrarSesion;
window.formatearMoneda = formatearMoneda;
window.formatearFecha = formatearFecha;
window.formatearHora = formatearHora;
window.validarEmail = validarEmail;
window.validarTelefono = validarTelefono;
window.validarDNI = validarDNI;
window.mostrarLoading = mostrarLoading;
window.ocultarLoading = ocultarLoading;

console.log('✅ Utils.js loaded successfully');