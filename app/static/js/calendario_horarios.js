/**
 * CALENDARIO HORARIOS - COMPATIBLE CON HTML REAL
 * Usa: #calendarioDias, #slotsContainer, cambiarMes()
 */

console.log('📅 Calendario JS iniciando...');

// ============================================
// VARIABLES GLOBALES
// ============================================

let mesActual = new Date().getMonth();
let anioActual = new Date().getFullYear();
let fechaSeleccionada = null;
let horaSeleccionada = null;

const nombresMeses = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
];

// ============================================
// GENERAR CALENDARIO
// ============================================

function generarCalendario() {
    console.log(`📅 Generando: ${nombresMeses[mesActual]} ${anioActual}`);
    
    // Actualizar título
    const titulo = document.getElementById('mesActual');
    if (titulo) {
        titulo.textContent = `${nombresMeses[mesActual]} ${anioActual}`;
    }
    
    // Buscar contenedor de días (TU HTML USA #calendarioDias)
    const container = document.getElementById('calendarioDias');
    if (!container) {
        console.error('❌ NO se encontró #calendarioDias');
        return;
    }
    
    container.innerHTML = '';
    
    // Calcular primer día del mes
    const primerDia = new Date(anioActual, mesActual, 1).getDay();
    // Ajustar para Lunes=0 (en lugar de Domingo=0)
    const primerDiaAjustado = primerDia === 0 ? 6 : primerDia - 1;
    
    // Agregar espacios vacíos
    for (let i = 0; i < primerDiaAjustado; i++) {
        const vacio = document.createElement('div');
        vacio.className = 'calendar-day empty';
        container.appendChild(vacio);
    }
    
    // Agregar días del mes
    const ultimoDia = new Date(anioActual, mesActual + 1, 0).getDate();
    const hoy = new Date();
    
    for (let dia = 1; dia <= ultimoDia; dia++) {
        const divDia = document.createElement('div');
        divDia.className = 'calendar-day';
        divDia.textContent = dia;
        divDia.dataset.dia = dia;
        
        // Verificar si es hoy
        if (dia === hoy.getDate() && 
            mesActual === hoy.getMonth() && 
            anioActual === hoy.getFullYear()) {
            divDia.classList.add('today');
        }
        
        // Verificar si es pasado
        const fecha = new Date(anioActual, mesActual, dia);
        const hoyInicio = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate());
        
        if (fecha < hoyInicio) {
            divDia.classList.add('disabled');
        } else {
            divDia.addEventListener('click', () => seleccionarFecha(dia));
        }
        
        container.appendChild(divDia);
    }
    
    console.log(`✅ Calendario: ${ultimoDia} días`);
}

// ============================================
// CAMBIAR MES (FUNCIÓN GLOBAL PARA HTML)
// ============================================

window.cambiarMes = function(direccion) {
    mesActual += direccion;
    
    if (mesActual < 0) {
        mesActual = 11;
        anioActual--;
    } else if (mesActual > 11) {
        mesActual = 0;
        anioActual++;
    }
    
    generarCalendario();
    console.log(`📅 Mes: ${nombresMeses[mesActual]} ${anioActual}`);
};

// ============================================
// SELECCIONAR FECHA
// ============================================

function seleccionarFecha(dia) {
    console.log(`📅 Fecha: ${dia}/${mesActual + 1}/${anioActual}`);
    
    // Quitar selección anterior
    document.querySelectorAll('.calendar-day').forEach(d => {
        d.classList.remove('selected');
    });
    
    // Seleccionar nuevo
    const divDia = document.querySelector(`.calendar-day[data-dia="${dia}"]`);
    if (divDia) {
        divDia.classList.add('selected');
    }
    
    fechaSeleccionada = new Date(anioActual, mesActual, dia);
    
    // Mostrar fecha seleccionada
    const opciones = { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    };
    const fechaTexto = fechaSeleccionada.toLocaleDateString('es-PE', opciones);
    
    const elemFecha = document.getElementById('fechaSeleccionadaTexto');
    if (elemFecha) {
        elemFecha.textContent = fechaTexto;
    }
    
    // Generar horarios
    generarHorarios();
}

// ============================================
// GENERAR HORARIOS
// ============================================

function generarHorarios() {
    console.log('⏰ Generando horarios...');
    
    const container = document.getElementById('horariosContainer');
    const slotsContainer = document.getElementById('slotsContainer');
    
    if (!container || !slotsContainer) {
        console.error('❌ Contenedores no encontrados');
        return;
    }
    
    container.style.display = 'block';
    slotsContainer.innerHTML = '';
    
    // Horarios de 8 AM a 6 PM
    const horarios = [
        { valor: '08:00', texto: '8:00 AM' },
        { valor: '09:00', texto: '9:00 AM' },
        { valor: '10:00', texto: '10:00 AM' },
        { valor: '11:00', texto: '11:00 AM' },
        { valor: '12:00', texto: '12:00 PM' },
        { valor: '13:00', texto: '1:00 PM' },
        { valor: '14:00', texto: '2:00 PM' },
        { valor: '15:00', texto: '3:00 PM' },
        { valor: '16:00', texto: '4:00 PM' },
        { valor: '17:00', texto: '5:00 PM' },
        { valor: '18:00', texto: '6:00 PM' }
    ];
    
    horarios.forEach(horario => {
        const slot = document.createElement('div');
        slot.className = 'time-slot';
        slot.dataset.hora = horario.valor;
        
        // Simular disponibilidad (70% disponibles)
        const disponible = Math.random() > 0.3;
        
        slot.innerHTML = `
            <div class="time-slot-hora">${horario.texto}</div>
            <div class="time-slot-estado">${disponible ? 'Disponible' : 'Ocupado'}</div>
        `;
        
        if (!disponible) {
            slot.classList.add('ocupado');
        } else {
            slot.addEventListener('click', () => seleccionarHora(horario.valor, horario.texto));
        }
        
        slotsContainer.appendChild(slot);
    });
    
    console.log(`✅ ${horarios.length} horarios generados`);
    
    // Scroll suave
    container.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ============================================
// SELECCIONAR HORA
// ============================================

function seleccionarHora(hora, texto) {
    console.log(`⏰ Hora: ${texto}`);
    
    // Quitar selección anterior
    document.querySelectorAll('.time-slot').forEach(s => {
        s.classList.remove('selected');
    });
    
    // Seleccionar nuevo
    const slot = document.querySelector(`.time-slot[data-hora="${hora}"]`);
    if (slot) {
        slot.classList.add('selected');
    }
    
    horaSeleccionada = hora;
    
    // Habilitar botón continuar
    const btnContinuar = document.getElementById('btnContinuar');
    if (btnContinuar) {
        btnContinuar.disabled = false;
    }
}

// ============================================
// CONTINUAR AL PAGO - CON UPDATE A BD
// ============================================

window.continuarAPago = async function() {
    if (!fechaSeleccionada || !horaSeleccionada) {
        alert('Por favor selecciona fecha y hora');
        return;
    }
    
    console.log('✅ Guardando fecha y hora...');
    
    // Obtener ID de solicitud
    const solicitudId = localStorage.getItem('solicitud_actual_id');
    if (!solicitudId) {
        alert('Error: No se encontró solicitud');
        window.location.href = '/cliente/solicitud-aceite';
        return;
    }
    
    // Preparar datos
    const fechaISO = fechaSeleccionada.toISOString().split('T')[0];
    const fechaLegible = fechaSeleccionada.toLocaleDateString('es-PE', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    
    // ============================================
    // NUEVO: UPDATE A BASE DE DATOS
    // ============================================
    
    try {
        const deviceId = solicitudManager?.deviceId || localStorage.getItem('device_id') || 'unknown';

        const url = new URL(`/api/v1/solicitudes/${solicitudId}/fecha-hora`, window.location.origin);
        url.searchParams.append('fecha_servicio', fechaISO);
        url.searchParams.append('hora_servicio', horaSeleccionada);
        url.searchParams.append('device_id', deviceId);

        const response = await fetch(url, {
            method: 'PUT'
        });
        
        if (!response.ok) {
            const error = await response.json();
            
            // ============================================
            // FIX: Mostrar errores de validación correctamente
            // ============================================
            console.error('❌ Error completo:', error);
            
            let mensajeError = 'Error al guardar';
            
            if (error.detail) {
                if (Array.isArray(error.detail)) {
                    // Error de validación Pydantic
                    mensajeError = error.detail.map(e => 
                        `${e.loc.join('.')}: ${e.msg}`
                    ).join('\n');
                } else if (typeof error.detail === 'string') {
                    mensajeError = error.detail;
                }
            }
            
            throw new Error(mensajeError);
        }
        
        const result = await response.json();
        console.log('✅ BD actualizada:', result);
        
        // Actualizar localStorage SOLO si BD fue exitosa
        const solicitudStr = localStorage.getItem('solicitud_actual');
        if (solicitudStr) {
            const solicitud = JSON.parse(solicitudStr);
            
            solicitud.fechaHora = {
                fecha: fechaISO,
                hora: horaSeleccionada,
                fechaCompleta: fechaSeleccionada.toISOString(),
                fechaLegible: fechaLegible
            };
            
            localStorage.setItem('solicitud_actual', JSON.stringify(solicitud));
            console.log('📦 localStorage actualizado');
        }
        
        // Notificación éxito
        if (typeof mostrarNotificacion === 'function') {
            mostrarNotificacion('Fecha y hora confirmadas', 'success');
        }
        
        // Redirigir a métodos de pago
        console.log('🔄 Redirigiendo a pago...');
        setTimeout(() => {
            window.location.href = '/cliente/metodos-pago';
        }, 500);
        
    } catch (error) {
        console.error('❌ Error:', error);
        alert('Error al guardar fecha/hora:\n\n' + error.message);
    }
};

// ============================================
// INICIALIZACIÓN
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ DOM CARGADO');
    
    generarCalendario();
    
    // Verificar solicitud
    const solicitudStr = localStorage.getItem('solicitud_actual');
    if (!solicitudStr) {
        console.warn('⚠️ No hay solicitud');
        alert('No se encontró solicitud activa');
        setTimeout(() => {
            window.location.href = '/cliente/solicitud-aceite';
        }, 2000);
        return;
    }
    
    const solicitud = JSON.parse(solicitudStr);
    console.log('📦 Solicitud:', solicitud);
    
    console.log('✅ LISTO');
});


function volverAlPaso3() {
    // Volver a la página del formulario paso 3
    window.location.href = '/cliente/servicio/aceite#paso3';
}

console.log('✅ Calendario JS cargado');