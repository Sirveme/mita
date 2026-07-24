/* ============================================
   PANEL TÉCNICO - MITA
   ============================================ */

let tecnicoOnline = true;
let servicioActivo = null;
let timerInterval = null;

document.addEventListener('DOMContentLoaded', function() {
    console.log('Panel técnico cargado');
    initPanel();
});

// ========================================
// INICIALIZACIÓN
// ========================================

function initPanel() {
    cargarEstadisticas();
    verificarServicioActivo();
    cargarSolicitudes();
    initTimers();
}

// ========================================
// TOGGLE ONLINE/OFFLINE
// ========================================

function toggleStatus() {
    tecnicoOnline = !tecnicoOnline;
    
    const indicator = document.getElementById('statusIndicator');
    const statusText = indicator.querySelector('.status-text');
    
    if (tecnicoOnline) {
        indicator.classList.add('online');
        indicator.classList.remove('offline');
        statusText.textContent = 'En línea';
        mostrarNotificacion('Estás en línea. Recibirás solicitudes.', 'success');
    } else {
        indicator.classList.remove('online');
        indicator.classList.add('offline');
        statusText.textContent = 'Fuera de línea';
        mostrarNotificacion('Estás fuera de línea. No recibirás solicitudes.', 'warning');
    }
    
    // Aquí iría la actualización al servidor
    actualizarEstadoServidor(tecnicoOnline);
}

async function actualizarEstadoServidor(online) {
    try {
        // TODO: Implementar llamada al API
        console.log('Estado actualizado:', online ? 'online' : 'offline');
    } catch (error) {
        console.error('Error actualizando estado:', error);
    }
}

// ========================================
// CARGAR ESTADÍSTICAS
// ========================================

function cargarEstadisticas() {
    // Datos de ejemplo - reemplazar con llamada real al API
    const stats = {
        serviciosHoy: 5,
        gananciaHoy: 420,
        tiempoHoy: 6.5,
        calificacionHoy: 4.9
    };
    
    document.getElementById('serviciosHoy').textContent = stats.serviciosHoy;
    document.getElementById('gananciaHoy').textContent = `S/${stats.gananciaHoy}`;
    document.getElementById('tiempoHoy').textContent = `${stats.tiempoHoy}h`;
    document.getElementById('calificacionHoy').textContent = stats.calificacionHoy;
}

// ========================================
// SERVICIO ACTIVO
// ========================================

function verificarServicioActivo() {
    // Verificar si hay un servicio activo
    // TODO: Consultar al servidor
    
    const tieneServicioActivo = false; // Cambiar según respuesta del servidor
    
    const section = document.getElementById('activeServiceSection');
    if (tieneServicioActivo) {
        section.style.display = 'block';
        iniciarTimer();
    } else {
        section.style.display = 'none';
    }
}

function iniciarTimer() {
    let segundos = 0;
    
    timerInterval = setInterval(() => {
        segundos++;
        const horas = Math.floor(segundos / 3600);
        const minutos = Math.floor((segundos % 3600) / 60);
        const segs = segundos % 60;
        
        const timerElement = document.getElementById('activeTimer');
        if (timerElement) {
            timerElement.textContent = 
                `${String(horas).padStart(2, '0')}:${String(minutos).padStart(2, '0')}:${String(segs).padStart(2, '0')}`;
        }
    }, 1000);
}

function detenerTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

// ========================================
// CARGAR SOLICITUDES
// ========================================

async function cargarSolicitudes() {
    try {
        // TODO: Llamada real al API
        console.log('Cargando solicitudes...');
        
        // Las solicitudes ya están en el HTML como ejemplo
        // En producción, se cargarían dinámicamente
    } catch (error) {
        console.error('Error cargando solicitudes:', error);
        mostrarNotificacion('Error al cargar solicitudes', 'error');
    }
}

// ========================================
// ACEPTAR SERVICIO
// ========================================

async function aceptarServicio(id) {
    if (!tecnicoOnline) {
        mostrarNotificacion('Debes estar en línea para aceptar servicios', 'warning');
        return;
    }
    
    const confirmacion = confirm('¿Deseas aceptar este servicio?');
    
    if (!confirmacion) return;
    
    mostrarLoading('Aceptando servicio...');
    
    try {
        // TODO: Llamada al API
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        ocultarLoading();
        mostrarNotificacion('¡Servicio aceptado! Dirígete al cliente.', 'success');
        
        // Actualizar UI
        servicioActivo = id;
        document.getElementById('activeServiceSection').style.display = 'block';
        iniciarTimer();
        
        // Eliminar solicitud de la lista
        const card = document.querySelector(`.request-card[data-id="${id}"]`);
        if (card) {
            card.style.transition = 'all 0.3s ease';
            card.style.opacity = '0';
            card.style.transform = 'translateX(-100%)';
            setTimeout(() => card.remove(), 300);
        }
        
    } catch (error) {
        ocultarLoading();
        console.error('Error aceptando servicio:', error);
        mostrarNotificacion('Error al aceptar el servicio. Intenta nuevamente.', 'error');
    }
}

// ========================================
// VER DETALLES
// ========================================

function verDetalles(id) {
    console.log('Ver detalles del servicio:', id);
    
    // TODO: Abrir modal con detalles completos
    mostrarNotificacion('Función en desarrollo', 'info');
}

// ========================================
// FINALIZAR SERVICIO
// ========================================

async function finalizarServicio() {
    const confirmacion = confirm('¿Has completado el servicio?');
    
    if (!confirmacion) return;
    
    mostrarLoading('Finalizando servicio...');
    
    try {
        // TODO: Llamada al API
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        detenerTimer();
        ocultarLoading();
        mostrarNotificacion('¡Servicio completado! Excelente trabajo.', 'success');
        
        // Ocultar sección de servicio activo
        document.getElementById('activeServiceSection').style.display = 'none';
        servicioActivo = null;
        
        // Actualizar estadísticas
        cargarEstadisticas();
        
    } catch (error) {
        ocultarLoading();
        console.error('Error finalizando servicio:', error);
        mostrarNotificacion('Error al finalizar el servicio.', 'error');
    }
}

// ========================================
// PAUSAR SERVICIO
// ========================================

function pausarServicio() {
    mostrarNotificacion('Servicio pausado', 'info');
    detenerTimer();
    // TODO: Implementar lógica de pausa
}

// ========================================
// ACCIONES DE CLIENTE
// ========================================

function llamarCliente() {
    // TODO: Iniciar llamada
    mostrarNotificacion('Iniciando llamada...', 'info');
}

function abrirChat() {
    // TODO: Abrir chat
    mostrarNotificacion('Abriendo chat...', 'info');
}

function abrirMapa() {
    // TODO: Abrir navegación GPS
    mostrarNotificacion('Abriendo mapa...', 'info');
}

// ========================================
// FILTROS
// ========================================

function abrirFiltros() {
    // TODO: Modal de filtros
    mostrarNotificacion('Filtros en desarrollo', 'info');
}

// ========================================
// HEADER ACTIONS
// ========================================

function abrirNotificaciones() {
    // Reutilizar función de utils.js
    if (typeof window.abrirNotificaciones === 'function') {
        window.abrirNotificaciones();
    }
}

function abrirMenu() {
    // Reutilizar función de utils.js
    if (typeof window.abrirPerfil === 'function') {
        window.abrirPerfil();
    }
}

// ========================================
// TIMERS GENERALES
// ========================================

function initTimers() {
    // Actualizar solicitudes cada 30 segundos
    setInterval(() => {
        if (tecnicoOnline && !servicioActivo) {
            cargarSolicitudes();
        }
    }, 30000);
}

// ========================================
// EXPORTS GLOBALES
// ========================================

window.toggleStatus = toggleStatus;
window.aceptarServicio = aceptarServicio;
window.verDetalles = verDetalles;
window.finalizarServicio = finalizarServicio;
window.pausarServicio = pausarServicio;
window.llamarCliente = llamarCliente;
window.abrirChat = abrirChat;
window.abrirMapa = abrirMapa;
window.abrirFiltros = abrirFiltros;
window.abrirNotificaciones = abrirNotificaciones;
window.abrirMenu = abrirMenu;

console.log('✅ Panel técnico JS cargado');