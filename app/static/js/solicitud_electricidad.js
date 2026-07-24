/* ============================================
   SOLICITUD ELECTRICIDAD - JS
   ============================================ */

let pasoActual = 1;
const totalPasos = 4;
let datosFormulario = {};

document.addEventListener('DOMContentLoaded', function() {
    console.log('Solicitud electricidad cargado');
    
    const fechaInput = document.getElementById('fechaServicio');
    if (fechaInput) {
        const hoy = new Date().toISOString().split('T')[0];
        fechaInput.min = hoy;
        fechaInput.value = hoy;
    }
    
    initEventListeners();
    calcularPrecioTotal();
    actualizarProgressBar();
});

function initEventListeners() {
    const tipoServicio = document.getElementById('tipoServicio');
    if (tipoServicio) {
        tipoServicio.addEventListener('change', calcularPrecioTotal);
    }
    
    const urgenciaInputs = document.querySelectorAll('input[name="es_urgencia"]');
    urgenciaInputs.forEach(input => {
        input.addEventListener('change', calcularPrecioTotal);
    });
    
    const form = document.getElementById('solicitudForm');
    if (form) {
        form.addEventListener('submit', handleSubmit);
    }
}

function calcularPrecioTotal() {
    let total = 80; // Diagnóstico base
    
    const tipoServicio = document.getElementById('tipoServicio');
    const precioServicioRow = document.getElementById('precioServicio');
    const precioServicioValor = document.getElementById('precioServicioValor');
    
    if (tipoServicio && tipoServicio.value) {
        const selectedOption = tipoServicio.options[tipoServicio.selectedIndex];
        const precioServicio = parseInt(selectedOption.getAttribute('data-precio')) || 0;
        
        if (precioServicio > 0) {
            total += precioServicio;
            precioServicioRow.style.display = 'flex';
            precioServicioValor.textContent = `S/${precioServicio}`;
        } else {
            precioServicioRow.style.display = 'none';
        }
    }
    
    const urgenciaSi = document.querySelector('input[name="es_urgencia"][value="si"]');
    const recargaUrgenciaRow = document.getElementById('recargaUrgencia');
    
    if (urgenciaSi && urgenciaSi.checked) {
        total += 50;
        recargaUrgenciaRow.style.display = 'flex';
    } else {
        recargaUrgenciaRow.style.display = 'none';
    }
    
    const totalEstimado = document.getElementById('totalEstimado');
    if (totalEstimado) {
        totalEstimado.textContent = `S/${total}`;
    }
    
    return total;
}

function siguientePaso() {
    if (!validarPasoActual()) return;
    guardarDatosPaso();
    
    if (pasoActual < totalPasos) {
        pasoActual++;
        mostrarPaso(pasoActual);
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
    document.querySelectorAll('.form-step').forEach(step => {
        step.classList.remove('active');
    });
    
    const pasoElement = document.querySelector(`.form-step[data-step="${paso}"]`);
    if (pasoElement) {
        pasoElement.classList.add('active');
    }
    
    actualizarProgressBar();
    actualizarBotones();
    actualizarSteps();
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
    
    if (btnAnterior) {
        btnAnterior.style.display = pasoActual > 1 ? 'flex' : 'none';
    }
    
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

function validarPasoActual() {
    const pasoElement = document.querySelector(`.form-step[data-step="${pasoActual}"]`);
    if (!pasoElement) return true;
    
    const inputs = pasoElement.querySelectorAll('input[required], select[required], textarea[required]');
    let valido = true;
    
    inputs.forEach(input => {
        if (input.type === 'radio') {
            const name = input.name;
            const checked = document.querySelector(`input[name="${name}"]:checked`);
            if (!checked) {
                valido = false;
            }
        } else if (!input.value || input.value.trim() === '') {
            valido = false;
            input.style.borderColor = 'var(--error)';
            setTimeout(() => { input.style.borderColor = ''; }, 2000);
        }
    });
    
    if (!valido) {
        mostrarNotificacion('Por favor completa todos los campos requeridos', 'error');
    }
    
    return valido;
}

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
}

function actualizarResumen() {
    const tipoServicio = document.getElementById('tipoServicio');
    if (tipoServicio) {
        const textoServicio = tipoServicio.options[tipoServicio.selectedIndex].text;
        document.getElementById('resumenTipoServicio').textContent = textoServicio || '-';
    }
    
    const problemaEspecifico = document.querySelector('input[name="problema_especifico"]:checked');
    if (problemaEspecifico) {
        const labelText = problemaEspecifico.nextElementSibling.querySelector('span').textContent;
        document.getElementById('resumenProblema').textContent = labelText;
    }
    
    const urgencia = document.querySelector('input[name="es_urgencia"]:checked');
    document.getElementById('resumenUrgencia').textContent = urgencia && urgencia.value === 'si' ? 'Sí' : 'No';
    
    const fecha = document.querySelector('input[name="fecha_servicio"]');
    const hora = document.querySelector('select[name="hora_servicio"]');
    if (fecha && hora) {
        const fechaFormateada = new Date(fecha.value).toLocaleDateString('es-PE', { 
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' 
        });
        document.getElementById('resumenFechaHora').textContent = `${fechaFormateada} a las ${hora.value}`;
    }
    
    const tipoPropiedad = document.querySelector('select[name="tipo_propiedad"]');
    if (tipoPropiedad) {
        document.getElementById('resumenTipoPropiedad').textContent = 
            tipoPropiedad.options[tipoPropiedad.selectedIndex].text;
    }
    
    const descripcion = document.querySelector('textarea[name="descripcion_problema"]');
    if (descripcion) {
        const texto = descripcion.value.length > 100 ? 
            descripcion.value.substring(0, 100) + '...' : descripcion.value;
        document.getElementById('resumenDescripcion').textContent = texto;
    }
    
    const direccion = document.querySelector('input[name="direccion"]');
    const numero = document.querySelector('input[name="numero_casa"]');
    const piso = document.querySelector('input[name="piso"]');
    
    let direccionCompleta = direccion ? direccion.value : '';
    if (numero && numero.value) direccionCompleta += ` #${numero.value}`;
    if (piso && piso.value) direccionCompleta += `, Piso ${piso.value}`;
    
    document.getElementById('resumenDireccion').textContent = direccionCompleta || '-';
    
    const distrito = document.querySelector('select[name="distrito"]');
    if (distrito) {
        document.getElementById('resumenDistrito').textContent = 
            distrito.options[distrito.selectedIndex].text;
    }
    
    const total = calcularPrecioTotal();
    document.getElementById('resumenTotal').textContent = `S/${total}`;
}

function obtenerUbicacionActual() {
    if (!navigator.geolocation) {
        mostrarNotificacion('Tu navegador no soporta geolocalización', 'error');
        return;
    }
    
    mostrarNotificacion('Obteniendo tu ubicación...', 'info');
    
    navigator.geolocation.getCurrentPosition(
        function(position) {
            mostrarNotificacion('Ubicación obtenida exitosamente', 'success');
        },
        function(error) {
            mostrarNotificacion('No se pudo obtener tu ubicación', 'error');
        }
    );
}

async function handleSubmit(e) {
    e.preventDefault();
    
    if (!validarPasoActual()) return;
    guardarDatosPaso();
    
    const terminosCheckbox = document.querySelector('input[name="acepto_terminos"]');
    if (!terminosCheckbox || !terminosCheckbox.checked) {
        mostrarNotificacion('Debes aceptar los términos y condiciones', 'error');
        return;
    }
    
    const btnConfirmar = document.getElementById('btnConfirmar');
    const textoOriginal = btnConfirmar.innerHTML;
    btnConfirmar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
    btnConfirmar.disabled = true;
    
    try {
        const response = await enviarSolicitud(datosFormulario);
        if (response.success) {
            mostrarModalExito(response.codigo_servicio);
        }
    } catch (error) {
        mostrarNotificacion(error.message || 'Ocurrió un error', 'error');
        btnConfirmar.innerHTML = textoOriginal;
        btnConfirmar.disabled = false;
    }
}

async function enviarSolicitud(datos) {
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve({
                success: true,
                codigo_servicio: `ELEC-${Date.now()}`,
                mensaje: 'Servicio solicitado exitosamente'
            });
        }, 2000);
    });
}

function mostrarModalExito(codigoServicio) {
    const modal = document.getElementById('modalExito');
    const codigoSpan = document.getElementById('codigoServicio');
    
    if (codigoSpan) codigoSpan.textContent = codigoServicio;
    if (modal) modal.classList.add('show');
}

function irASeguimiento() {
    window.location.href = '/cliente/seguimiento';
}

window.siguientePaso = siguientePaso;
window.anteriorPaso = anteriorPaso;
window.obtenerUbicacionActual = obtenerUbicacionActual;
window.irASeguimiento = irASeguimiento;

console.log('✅ Solicitud electricidad JS cargado');