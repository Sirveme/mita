/* ============================================
   SOLICITUD ACEITE - JS
   ============================================ */

let pasoActual = 1;
const totalPasos = 4;
let datosFormulario = {};

// ========================================
// INICIALIZACIÓN
// ========================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('Solicitud aceite cargado');
    
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
    if (!validarPasoActual()) {
        return;
    }
    
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
        function(position) {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            
            console.log('Ubicación obtenida:', lat, lng);
            mostrarNotificacion('Ubicación obtenida exitosamente', 'success');
        },
        function(error) {
            console.error('Error de geolocalización:', error);
            mostrarNotificacion('No se pudo obtener tu ubicación', 'error');
        }
    );
}

// ========================================
// SUBMIT DEL FORMULARIO
// ========================================

/* ============================================
   MODIFICACIÓN PARA solicitud_aceite.js
   
   REEMPLAZAR la función handleSubmit() existente con esta:
   ============================================ */

async function handleSubmit(e) {
    e.preventDefault();
    
    if (!validarPasoActual()) {
        return;
    }
    
    guardarDatosPaso();
    
    const terminosCheckbox = document.querySelector('input[name="acepto_terminos"]');
    if (!terminosCheckbox || !terminosCheckbox.checked) {
        mostrarNotificacion('Debes aceptar los términos y condiciones', 'error');
        return;
    }
    
    // Crear objeto solicitud
    const solicitud = {
        id: 'SERV-' + Date.now(),
        vehiculo: {
            marca: datosFormulario.marca_vehiculo || '',
            modelo: datosFormulario.modelo_vehiculo || '',
            anio: datosFormulario.anio_vehiculo || '',
            placa: datosFormulario.placa_vehiculo || '',
            color: datosFormulario.color_vehiculo || '',
            kilometraje: datosFormulario.kilometraje || 0
        },
        servicio: {
            tipo: 'cambio_aceite',
            tipo_aceite: datosFormulario.tipo_aceite || 'mineral',
            incluir_filtro: datosFormulario.incluir_filtro === 'si',
            notas: datosFormulario.notas || ''
        },
        ubicacion: {
            distrito: datosFormulario.distrito || '',
            direccion: datosFormulario.direccion || '',
            numero_casa: datosFormulario.numero_casa || '',
            piso: datosFormulario.piso || '',
            referencia: datosFormulario.referencia || ''
        },
        estado: 'iniciado',
        created_at: new Date().toISOString()
    };
    
    localStorage.setItem('solicitud_actual', JSON.stringify(solicitud));
    
    console.log('✅ Solicitud guardada:', solicitud);
    
    // REDIRIGIR (NO mostrar modal)
    window.location.href = '/cliente/calendario-horarios';
}

/* ============================================
   INSTRUCCIONES:
   
   1. Abrir app/static/js/solicitud_aceite.js
   2. Buscar la función async function handleSubmit(e)
   3. REEMPLAZAR toda esa función con la de arriba
   4. Guardar archivo
   
   ESTO CONECTA EL FLUJO:
   Formulario → Calendario → Métodos Pago → Buscar Mecánico → Asignado
   ============================================ */

async function enviarSolicitud(datos) {
    console.log('Enviando solicitud:', datos);
    
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve({
                success: true,
                codigo_servicio: `ACE-${Date.now()}`,
                mensaje: 'Servicio solicitado exitosamente'
            });
        }, 2000);
    });
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
    window.location.href = '/cliente/seguimiento';
}

// ========================================
// EXPORTS GLOBALES
// ========================================

window.siguientePaso = siguientePaso;
window.anteriorPaso = anteriorPaso;
window.obtenerUbicacionActual = obtenerUbicacionActual;
window.irASeguimiento = irASeguimiento;

console.log('✅ Solicitud aceite JS cargado correctamente');


/* ============================================
   CÓDIGO ADICIONAL PARA solicitud_aceite.js
   Agregar al final del archivo existente
   ============================================ */

// ========================================
// VARIABLES GLOBALES ADICIONALES
// ========================================

let selectedOilType = 'standard';
let selectedOilPrice = 180;

// ========================================
// VALIDACIÓN DE PLACA EN TIEMPO REAL
// ========================================

function validatePlaca(input) {
    const value = input.value.toUpperCase();
    const pattern = /^[A-Z0-9]{3}-?[A-Z0-9]{3,4}$/;
    const validation = document.getElementById('placaValidation');
    const btnConsultar = document.getElementById('btnConsultar');

    if (value.length === 0) {
        validation.innerHTML = '';
        btnConsultar.disabled = true;
        input.classList.remove('valid', 'invalid');
        return;
    }

    if (pattern.test(value) && value.length >= 6) {
        validation.innerHTML = '<i class="fas fa-check-circle"></i> Formato de placa válido';
        validation.className = 'validation-message success';
        input.classList.add('valid');
        input.classList.remove('invalid');
        btnConsultar.disabled = false;
    } else {
        validation.innerHTML = '<i class="fas fa-times-circle"></i> Formato inválido. Debe ser: ABC-123';
        validation.className = 'validation-message error';
        input.classList.add('invalid');
        input.classList.remove('valid');
        btnConsultar.disabled = true;
    }
}

// ========================================
// CONSULTAR PLACA (SIMULACIÓN API)
// ========================================

function consultarPlaca() {
    const placa = document.getElementById('placa').value;
    const btn = document.getElementById('btnConsultar');
    const resultDiv = document.getElementById('autoCompleteResult');

    // Loading state
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Consultando...';

    // Simular llamada API
    setTimeout(() => {
        // Datos simulados (en producción = API real)
        const vehicleData = {
            marca: 'toyota',
            modelo: 'Corolla',
            anio: 2018,
            color: 'Gris Metalizado'
        };

        // Llenar campos
        document.getElementById('marca').value = vehicleData.marca;
        document.getElementById('modelo').value = vehicleData.modelo;
        document.getElementById('anio').value = vehicleData.anio;
        document.getElementById('color').value = vehicleData.color;

        // Mostrar resultado
        resultDiv.style.display = 'block';
        resultDiv.innerHTML = `
            <div class="autocomplete-result">
                <div class="result-header">
                    <i class="fas fa-check-circle"></i>
                    <span>Vehículo encontrado en SUNARP</span>
                </div>
                <div class="result-item">
                    <span class="result-label">Marca:</span>
                    <span class="result-value">${vehicleData.marca.toUpperCase()}</span>
                </div>
                <div class="result-item">
                    <span class="result-label">Modelo:</span>
                    <span class="result-value">${vehicleData.modelo}</span>
                </div>
                <div class="result-item">
                    <span class="result-label">Año:</span>
                    <span class="result-value">${vehicleData.anio}</span>
                </div>
                <div class="result-item">
                    <span class="result-label">Color:</span>
                    <span class="result-value">${vehicleData.color}</span>
                </div>
            </div>
        `;

        // Restaurar botón
        btn.innerHTML = '<i class="fas fa-check"></i> Consultado';
        
        // Mostrar recomendación
        checkVehicleData();

    }, 1500);
}

// ========================================
// ACTUALIZAR VALOR DEL SLIDER
// ========================================

function updateKmValue(value) {
    const kmValue = document.getElementById('kmValue');
    if (kmValue) {
        kmValue.textContent = parseInt(value).toLocaleString('es-PE');
    }
}

// ========================================
// VERIFICAR DATOS COMPLETOS PARA ACEITE
// ========================================

function checkVehicleData() {
    const marca = document.getElementById('marca').value;
    const modelo = document.getElementById('modelo').value;
    const anio = document.getElementById('anio').value;

    if (marca && modelo && anio) {
        const recommendationDiv = document.getElementById('oilRecommendation');
        if (recommendationDiv) {
            recommendationDiv.style.display = 'block';
        }
    }
}

// ========================================
// SELECCIONAR TIPO DE ACEITE
// ========================================

function selectOil(element, type, price) {
    // Remover selección anterior
    document.querySelectorAll('.oil-option').forEach(opt => {
        opt.classList.remove('selected');
    });

    // Agregar selección actual
    element.classList.add('selected');
    selectedOilType = type;
    selectedOilPrice = price;

    console.log('Aceite seleccionado:', type, price);
}

// ========================================
// EXPORTS ADICIONALES
// ========================================

window.validatePlaca = validatePlaca;
window.consultarPlaca = consultarPlaca;
window.updateKmValue = updateKmValue;
window.checkVehicleData = checkVehicleData;
window.selectOil = selectOil;

console.log('✅ Funciones adicionales de aceite cargadas');