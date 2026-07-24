/* ========================================
   MITA - SOLICITUD DE SERVICIO JS
   ======================================== */

// Variables globales
let pasoActual = 1;
const totalPasos = 4;
let datosFormulario = {};

// ========================================
// INICIALIZACIÓN
// ========================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('Solicitud de servicio cargado');
    
    // Configurar fecha mínima (hoy)
    const fechaInput = document.getElementById('fechaServicio');
    if (fechaInput) {
        const hoy = new Date().toISOString().split('T')[0];
        fechaInput.min = hoy;
        fechaInput.value = hoy;
    }
    
    // Event listeners
    initEventListeners();
    
    // Calcular precio inicial
    calcularPrecioTotal();
    
    // Actualizar progress bar
    actualizarProgressBar();
});

// ========================================
// EVENT LISTENERS
// ========================================

function initEventListeners() {
    // Cambio de tipo de aceite
    const tipoAceite = document.getElementById('tipoAceite');
    if (tipoAceite) {
        tipoAceite.addEventListener('change', calcularPrecioTotal);
    }
    
    // Cambio de filtro
    const filtroInputs = document.querySelectorAll('input[name="incluir_filtro"]');
    filtroInputs.forEach(input => {
        input.addEventListener('change', calcularPrecioTotal);
    });
    
    // Submit del formulario
    const form = document.getElementById('solicitudForm');
    if (form) {
        form.addEventListener('submit', handleSubmit);
    }
    
    // Autocompletar placa en mayúsculas
    const placaInput = document.querySelector('input[name="placa_vehiculo"]');
    if (placaInput) {
        placaInput.addEventListener('input', function(e) {
            e.target.value = e.target.value.toUpperCase();
        });
    }
}

// ========================================
// CÁLCULO DE PRECIO
// ========================================

function calcularPrecioTotal() {
    let total = 50; // Servicio a domicilio base
    
    // Precio del aceite
    const tipoAceite = document.getElementById('tipoAceite');
    const precioAceiteRow = document.getElementById('precioAceite');
    const precioAceiteValor = document.getElementById('precioAceiteValor');
    
    if (tipoAceite && tipoAceite.value) {
        const selectedOption = tipoAceite.options[tipoAceite.selectedIndex];
        const precioAceite = parseInt(selectedOption.getAttribute('data-precio')) || 0;
        
        if (precioAceite > 0) {
            total += precioAceite;
            precioAceiteRow.style.display = 'flex';
            precioAceiteValor.textContent = `S/${precioAceite}`;
        } else {
            precioAceiteRow.style.display = 'none';
        }
    }
    
    // Precio del filtro
    const filtroSi = document.querySelector('input[name="incluir_filtro"][value="si"]');
    const precioFiltroRow = document.getElementById('precioFiltro');
    
    if (filtroSi && filtroSi.checked) {
        total += 30;
        precioFiltroRow.style.display = 'flex';
    } else {
        precioFiltroRow.style.display = 'none';
    }
    
    // Actualizar total
    const totalEstimado = document.getElementById('totalEstimado');
    if (totalEstimado) {
        totalEstimado.textContent = `S/${total}`;
    }
    
    return total;
}

// ========================================
// NAVEGACIÓN ENTRE PASOS
// ========================================

function siguientePaso() {
    // Validar paso actual
    if (!validarPasoActual()) {
        return;
    }
    
    // Guardar datos del paso actual
    guardarDatosPaso();
    
    // Avanzar al siguiente paso
    if (pasoActual < totalPasos) {
        pasoActual++;
        mostrarPaso(pasoActual);
        
        // Si es el último paso, actualizar resumen
        if (pasoActual === totalPasos) {
            actualizarResumen();
        }
    }
}

function anteriorPaso() {
    if (pasoActual > 1) {
        pasoActual--;
        mostrarPaso(pasoActual);
    }
}

function mostrarPaso(paso) {
    // Ocultar todos los pasos
    document.querySelectorAll('.form-step').forEach(step => {
        step.classList.remove('active');
    });
    
    // Mostrar paso actual
    const pasoElement = document.querySelector(`.form-step[data-step="${paso}"]`);
    if (pasoElement) {
        pasoElement.classList.add('active');
    }
    
    // Actualizar progress bar
    actualizarProgressBar();
    
    // Actualizar botones
    actualizarBotones();
    
    // Actualizar steps
    actualizarSteps();
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function actualizarProgressBar() {
    const progressFill = document.getElementById('progressFill');
    if (progressFill) {
        const porcentaje = (pasoActual / totalPasos) * 100;
        progressFill.style.width = `${porcentaje}%`;
    }
}

function actualizarBotones() {
    const btnAnterior = document.getElementById('btnAnterior');
    const btnSiguiente = document.getElementById('btnSiguiente');
    const btnConfirmar = document.getElementById('btnConfirmar');
    
    // Botón anterior
    if (btnAnterior) {
        btnAnterior.style.display = pasoActual > 1 ? 'flex' : 'none';
    }
    
    // Botón siguiente vs confirmar
    if (pasoActual === totalPasos) {
        if (btnSiguiente) btnSiguiente.style.display = 'none';
        if (btnConfirmar) btnConfirmar.style.display = 'flex';
    } else {
        if (btnSiguiente) btnSiguiente.style.display = 'flex';
        if (btnConfirmar) btnConfirmar.style.display = 'none';
    }
}

function actualizarSteps() {
    document.querySelectorAll('.step').forEach(step => {
        const stepNum = parseInt(step.getAttribute('data-step'));
        
        step.classList.remove('active', 'completed');
        
        if (stepNum === pasoActual) {
            step.classList.add('active');
        } else if (stepNum < pasoActual) {
            step.classList.add('completed');
        }
    });
}

// ========================================
// VALIDACIÓN
// ========================================

function validarPasoActual() {
    const pasoElement = document.querySelector(`.form-step[data-step="${pasoActual}"]`);
    if (!pasoElement) return true;
    
    const inputs = pasoElement.querySelectorAll('input[required], select[required], textarea[required]');
    let valido = true;
    
    inputs.forEach(input => {
        if (!input.value || input.value.trim() === '') {
            valido = false;
            input.style.borderColor = 'var(--error)';
            
            // Remover estilo después de 2 segundos
            setTimeout(() => {
                input.style.borderColor = '';
            }, 2000);
        }
    });
    
    if (!valido) {
        mostrarNotificacion('Por favor completa todos los campos requeridos', 'error');
    }
    
    return valido;
}

// ========================================
// GUARDAR DATOS
// ========================================

function guardarDatosPaso() {
    const pasoElement = document.querySelector(`.form-step[data-step="${pasoActual}"]`);
    if (!pasoElement) return;
    
    const inputs = pasoElement.querySelectorAll('input, select, textarea');
    
    inputs.forEach(input => {
        if (input.type === 'radio') {
            if (input.checked) {
                datosFormulario[input.name] = input.value;
            }
        } else if (input.type === 'checkbox') {
            datosFormulario[input.name] = input.checked;
        } else {
            datosFormulario[input.name] = input.value;
        }
    });
    
    console.log('Datos guardados:', datosFormulario);
}

// ========================================
// RESUMEN
// ========================================

function actualizarResumen() {
    // Resumen servicio
    const tipoAceite = document.getElementById('tipoAceite');
    if (tipoAceite) {
        const textoAceite = tipoAceite.options[tipoAceite.selectedIndex].text;
        document.getElementById('resumenAceite').textContent = textoAceite || '-';
    }
    
    const filtro = document.querySelector('input[name="incluir_filtro"]:checked');
    document.getElementById('resumenFiltro').textContent = filtro ? (filtro.value === 'si' ? 'Sí' : 'No') : '-';
    
    const fecha = document.querySelector('input[name="fecha_servicio"]');
    const hora = document.querySelector('select[name="hora_servicio"]');
    if (fecha && hora) {
        const fechaFormateada = new Date(fecha.value).toLocaleDateString('es-PE', { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });
        document.getElementById('resumenFechaHora').textContent = `${fechaFormateada} a las ${hora.value}`;
    }
    
    // Resumen vehículo
    const marca = document.querySelector('select[name="marca_vehiculo"]');
    const modelo = document.querySelector('input[name="modelo_vehiculo"]');
    const anio = document.querySelector('input[name="anio_vehiculo"]');
    
    if (marca && modelo && anio) {
        const marcaTexto = marca.options[marca.selectedIndex].text;
        document.getElementById('resumenVehiculo').textContent = 
            `${marcaTexto} ${modelo.value} ${anio.value}`;
    }
    
    const placa = document.querySelector('input[name="placa_vehiculo"]');
    document.getElementById('resumenPlaca').textContent = placa ? placa.value : '-';
    
    const kilometraje = document.querySelector('input[name="kilometraje"]');
    document.getElementById('resumenKilometraje').textContent = 
        kilometraje ? `${parseInt(kilometraje.value).toLocaleString()} km` : '-';
    
    // Resumen ubicación
    const direccion = document.querySelector('input[name="direccion"]');
    const numero = document.querySelector('input[name="numero_casa"]');
    const piso = document.querySelector('input[name="piso"]');
    
    let direccionCompleta = direccion ? direccion.value : '';
    if (numero && numero.value) direccionCompleta += ` #${numero.value}`;
    if (piso && piso.value) direccionCompleta += `, Piso ${piso.value}`;
    
    document.getElementById('resumenDireccion').textContent = direccionCompleta || '-';
    
    const distrito = document.querySelector('select[name="distrito"]');
    if (distrito) {
        const distritoTexto = distrito.options[distrito.selectedIndex].text;
        document.getElementById('resumenDistrito').textContent = distritoTexto;
    }
    
    // Total
    const total = calcularPrecioTotal();
    document.getElementById('resumenTotal').textContent = `S/${total}`;
}

// ========================================
// UBICACIÓN
// ========================================

function obtenerUbicacionActual() {
    if (!navigator.geolocation) {
        mostrarNotificacion('Tu navegador no soporta geolocalización', 'error');
        return;
    }
    
    mostrarNotificacion('Obteniendo tu ubicación...', 'info');
    
    navigator.geolocation.getCurrentPosition(
        async function(position) {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            
            console.log('Ubicación obtenida:', lat, lng);
            
            // Aquí podrías usar una API de geocoding inverso
            // Por ahora, solo mostramos un mensaje
            mostrarNotificacion('Ubicación obtenida exitosamente', 'success');
            
            // Actualizar mapa preview
            const mapPreview = document.getElementById('mapPreview');
            if (mapPreview) {
                mapPreview.innerHTML = `
                    <i class="fas fa-map-marker-alt" style="color: var(--success);"></i>
                    <p style="color: var(--success);">Ubicación detectada</p>
                    <small style="color: var(--text-gray);">Lat: ${lat.toFixed(4)}, Lng: ${lng.toFixed(4)}</small>
                `;
            }
            
            // TODO: Llamar a API de geocoding para obtener dirección
            // await obtenerDireccionDesdeCoordenadas(lat, lng);
        },
        function(error) {
            console.error('Error de geolocalización:', error);
            mostrarNotificacion('No se pudo obtener tu ubicación', 'error');
        },
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        }
    );
}

// ========================================
// SUBMIT DEL FORMULARIO
// ========================================

async function handleSubmit(e) {
    e.preventDefault();
    
    // Validar paso final
    if (!validarPasoActual()) {
        return;
    }
    
    // Guardar datos finales
    guardarDatosPaso();
    
    // Validar términos y condiciones
    const terminosCheckbox = document.querySelector('input[name="acepto_terminos"]');
    if (!terminosCheckbox || !terminosCheckbox.checked) {
        mostrarNotificacion('Debes aceptar los términos y condiciones', 'error');
        return;
    }
    
    // Mostrar loading
    const btnConfirmar = document.getElementById('btnConfirmar');
    const textoOriginal = btnConfirmar.innerHTML;
    btnConfirmar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
    btnConfirmar.disabled = true;
    
    try {
        // Enviar datos al backend
        const response = await enviarSolicitud(datosFormulario);
        
        if (response.success) {
            // Mostrar modal de éxito
            mostrarModalExito(response.codigo_servicio);
        } else {
            throw new Error(response.message || 'Error al procesar la solicitud');
        }
        
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion(error.message || 'Ocurrió un error. Intenta nuevamente.', 'error');
        
        // Restaurar botón
        btnConfirmar.innerHTML = textoOriginal;
        btnConfirmar.disabled = false;
    }
}

async function enviarSolicitud(datos) {
    // Simulación de envío al backend
    console.log('Enviando solicitud:', datos);
    
    // TODO: Reemplazar con llamada real al backend
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve({
                success: true,
                codigo_servicio: `SRV-${Date.now()}`,
                mensaje: 'Servicio solicitado exitosamente'
            });
        }, 2000);
    });
    
    // Código real cuando esté el backend:
    /*
    const response = await fetch('/api/servicios/solicitar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(datos)
    });
    
    if (!response.ok) {
        throw new Error('Error al enviar la solicitud');
    }
    
    return await response.json();
    */
}

// ========================================
// MODAL DE ÉXITO
// ========================================

function mostrarModalExito(codigoServicio) {
    const modal = document.getElementById('modalExito');
    const codigoSpan = document.getElementById('codigoServicio');
    
    if (codigoSpan) {
        codigoSpan.textContent = codigoServicio;
    }
    
    if (modal) {
        modal.classList.add('show');
    }
}

function irASeguimiento() {
    // Redirigir a página de seguimiento
    window.location.href = '/cliente/seguimiento';
}

// ========================================
// NOTIFICACIONES
// ========================================

function mostrarNotificacion(mensaje, tipo = 'info') {
    // Remover notificación previa
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
        <i class="fas ${iconClass} toast-icon"></i>
        <span class="toast-message">${mensaje}</span>
    `;
    
    // Agregar al body
    document.body.appendChild(toast);
    
    // Mostrar con animación
    setTimeout(() => {
        toast.classList.add('show');
    }, 100);
    
    // Ocultar y remover
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            toast.remove();
        }, 400);
    }, 4000);
}

// ========================================
// UTILIDADES
// ========================================

function formatearFecha(fecha) {
    return new Date(fecha).toLocaleDateString('es-PE', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

function formatearMoneda(valor) {
    return `S/${parseFloat(valor).toFixed(2)}`;
}

// ========================================
// EXPORT FUNCIONES GLOBALES
// ========================================

window.siguientePaso = siguientePaso;
window.anteriorPaso = anteriorPaso;
window.obtenerUbicacionActual = obtenerUbicacionActual;
window.irASeguimiento = irASeguimiento;

console.log('✅ Solicitud de servicio JS cargado correctamente');