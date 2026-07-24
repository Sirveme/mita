/* ============================================
   SOLICITUD GASFITERÍA - JS
   ============================================ */

let pasoActual = 1;
const totalPasos = 4;
let datosFormulario = {};

document.addEventListener('DOMContentLoaded', function() {
    console.log('Solicitud gasfitería cargado');
    
    const fechaInput = document.getElementById('fechaServicio');
    if (fechaInput) {
        const hoy = new Date().toISOString().split('T')[0];
        fechaInput.min = hoy;
        fechaInput.value = hoy;
    }
    
    initEventListeners();
    calcularPrecioTotal();
    actualizarProgressBar();
    manejarCamposUrgencia();
});

function initEventListeners() {
    const tipoProblema = document.getElementById('tipoProblema');
    if (tipoProblema) {
        tipoProblema.addEventListener('change', calcularPrecioTotal);
    }
    
    const urgenciaInputs = document.querySelectorAll('input[name="urgencia"]');
    urgenciaInputs.forEach(input => {
        input.addEventListener('change', function() {
            calcularPrecioTotal();
            manejarCamposUrgencia();
        });
    });
    
    const form = document.getElementById('solicitudForm');
    if (form) {
        form.addEventListener('submit', handleSubmit);
    }
}

function manejarCamposUrgencia() {
    const urgencia = document.querySelector('input[name="urgencia"]:checked');
    const grupoFecha = document.getElementById('grupoFecha');
    const grupoHora = document.getElementById('grupoHora');
    
    if (urgencia && (urgencia.value === 'emergencia' || urgencia.value === 'urgente')) {
        if (grupoFecha) grupoFecha.style.display = 'none';
        if (grupoHora) grupoHora.style.display = 'none';
        
        document.querySelector('input[name="fecha_servicio"]').removeAttribute('required');
        document.querySelector('select[name="hora_servicio"]').removeAttribute('required');
    } else {
        if (grupoFecha) grupoFecha.style.display = 'block';
        if (grupoHora) grupoHora.style.display = 'block';
        
        document.querySelector('input[name="fecha_servicio"]').setAttribute('required', 'required');
        document.querySelector('select[name="hora_servicio"]').setAttribute('required', 'required');
    }
}

function calcularPrecioTotal() {
    let total = 70; // Diagnóstico base
    
    const tipoProblema = document.getElementById('tipoProblema');
    const precioServicioRow = document.getElementById('precioServicio');
    const precioServicioValor = document.getElementById('precioServicioValor');
    
    if (tipoProblema && tipoProblema.value) {
        const selectedOption = tipoProblema.options[tipoProblema.selectedIndex];
        const precioServicio = parseInt(selectedOption.getAttribute('data-precio')) || 0;
        
        if (precioServicio > 0) {
            total += precioServicio;
            precioServicioRow.style.display = 'flex';
            precioServicioValor.textContent = `S/${precioServicio}`;
        } else {
            precioServicioRow.style.display = 'none';
        }
    }
    
    const urgencia = document.querySelector('input[name="urgencia"]:checked');
    const recargaUrgenciaRow = document.getElementById('recargaUrgencia');
    const recargaUrgenciaValor = document.getElementById('recargaUrgenciaValor');
    
    if (urgencia) {
        const recargo = parseInt(urgencia.getAttribute('data-recargo')) || 0;
        if (recargo > 0) {
            total += recargo;
            recargaUrgenciaRow.style.display = 'flex';
            recargaUrgenciaValor.textContent = `S/${recargo}`;
        } else {
            recargaUrgenciaRow.style.display = 'none';
        }
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
    const tipoProblema = document.getElementById('tipoProblema');
    if (tipoProblema) {
        document.getElementById('resumenTipoProblema').textContent = 
            tipoProblema.options[tipoProblema.selectedIndex].text;
    }
    
    const ubicacionProblema = document.querySelector('input[name="ubicacion_problema"]:checked');
    if (ubicacionProblema) {
        const labelText = ubicacionProblema.nextElementSibling.querySelector('span').textContent;
        document.getElementById('resumenUbicacionProblema').textContent = labelText;
    }
    
    const urgencia = document.querySelector('input[name="urgencia"]:checked');
    if (urgencia) {
        const urgenciaTextos = {
            'emergencia': 'Emergencia (Inmediato)',
            'urgente': 'Urgente (Mismo día)',
            'normal': 'Normal (Agendado)'
        };
        document.getElementById('resumenUrgencia').textContent = urgenciaTextos[urgencia.value] || '-';
    }
    
    const tiempoProblema = document.querySelector('select[name="tiempo_problema"]');
    if (tiempoProblema) {
        document.getElementById('resumenTiempo').textContent = 
            tiempoProblema.options[tiempoProblema.selectedIndex].text;
    }
    
    const urgenciaCheck = document.querySelector('input[name="urgencia"]:checked');
    if (urgenciaCheck && (urgenciaCheck.value === 'emergencia' || urgenciaCheck.value === 'urgente')) {
        document.getElementById('resumenFechaHora').textContent = 'Lo antes posible';
    } else {
        const fecha = document.querySelector('input[name="fecha_servicio"]');
        const hora = document.querySelector('select[name="hora_servicio"]');
        if (fecha && hora) {
            const fechaFormateada = new Date(fecha.value).toLocaleDateString('es-PE', { 
                weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' 
            });
            document.getElementById('resumenFechaHora').textContent = `${fechaFormateada} a las ${hora.value}`;
        }
    }
    
    const descripcion = document.querySelector('textarea[name="descripcion_problema"]');
    if (descripcion) {
        const texto = descripcion.value.length > 80 ? 
            descripcion.value.substring(0, 80) + '...' : descripcion.value;
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
    
    const telefono = document.querySelector('input[name="telefono_contacto"]');
    document.getElementById('resumenTelefono').textContent = telefono ? telefono.value : '-';
    
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
                codigo_servicio: `GAS-${Date.now()}`,
                mensaje: 'Servicio solicitado exitosamente'
            });
        }, 2000);
    });
}

function mostrarModalExito(codigoServicio) {
    const modal = document.getElementById('modalExito');
    const codigoSpan = document.getElementById('codigoServicio');
    const mensajeUrgencia = document.getElementById('mensajeUrgencia');
    
    if (codigoSpan) codigoSpan.textContent = codigoServicio;
    
    const urgencia = document.querySelector('input[name="urgencia"]:checked');
    if (mensajeUrgencia && urgencia) {
        if (urgencia.value === 'emergencia') {
            mensajeUrgencia.textContent = 'Un técnico te contactará en los próximos 15 minutos.';
            mensajeUrgencia.style.color = '#EF4444';
        } else if (urgencia.value === 'urgente') {
            mensajeUrgencia.textContent = 'Te contactaremos en menos de 2 horas.';
            mensajeUrgencia.style.color = '#F59E0B';
        } else {
            mensajeUrgencia.textContent = 'Te confirmaremos la cita próximamente.';
        }
    }
    
    if (modal) modal.classList.add('show');
}

function irASeguimiento() {
    window.location.href = '/cliente/seguimiento';
}

window.siguientePaso = siguientePaso;
window.anteriorPaso = anteriorPaso;
window.obtenerUbicacionActual = obtenerUbicacionActual;
window.irASeguimiento = irASeguimiento;

console.log('✅ Solicitud gasfitería JS cargado');