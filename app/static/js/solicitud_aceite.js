/**
 * SOLICITUD ACEITE - COMPATIBLE CON HTML REAL
 * Usa: .step[data-step], .step-circle
 */

console.log('🔧 Solicitud aceite JS iniciando...');

// ============================================
// VARIABLES GLOBALES
// ============================================

let pasoActual = 1;
const totalPasos = 4;
let datosFormulario = {};

// ============================================
// FUNCIONES INLINE
// ============================================

window.validatePlaca = function(input) {
    if (!input) return;
    input.value = input.value.toUpperCase();
    
    const btnConsultar = document.getElementById('btnConsultar');
    if (btnConsultar) {
        btnConsultar.disabled = input.value.length < 7;
    }
};

window.checkVehicleData = function() {
    console.log('🔍 Verificando datos vehículo...');
};

window.updateKmValue = function(value) {
    const display = document.getElementById('kmValue');
    if (display) {
        const numValue = parseInt(value) || 0;
        display.textContent = numValue.toLocaleString('es-PE');
    }
};

window.consultarPlaca = function() {
    alert('Función consulta SUNARP en desarrollo');
};

window.selectOil = function(element, tipo, precio) {
    document.querySelectorAll('.oil-option').forEach(opt => {
        opt.classList.remove('selected');
    });
    element.classList.add('selected');
};

window.obtenerUbicacionActual = function() {
    alert('Geolocalización en desarrollo');
};

// ============================================
// NAVEGACIÓN
// ============================================

function mostrarPaso(paso) {
    console.log(`\n📍 ========== MOSTRANDO PASO ${paso} ==========`);
    
    // Ocultar todos los pasos
    document.querySelectorAll('.form-step').forEach(step => {
        step.classList.remove('active');
    });
    
    // Mostrar el paso actual
    const pasoElement = document.querySelector(`.form-step[data-step="${paso}"]`);
    if (pasoElement) {
        pasoElement.classList.add('active');
        console.log(`✅ Paso ${paso} mostrado`);
    } else {
        console.error(`❌ No se encontró paso ${paso}`);
    }
    
    // Actualizar indicadores (USAR TU HTML REAL)
    actualizarIndicadorPasos(paso);
    
    // Actualizar botones
    actualizarBotones(paso);
    
    // Si es paso 4, actualizar resumen
    if (paso === 4) {
        setTimeout(() => {
            actualizarResumen();
            actualizarPrecioTotal();
            mostrarResumenPaso4();
        }, 100);
    }
    
    pasoActual = paso;
    actualizarIndicadorPasos(paso);
    actualizarBotones(paso);
    console.log('========================================\n');
}

function actualizarIndicadorPasos(paso) {
    console.log(`🎨 Actualizando indicadores para paso ${paso}...`);
    
    // Buscar usando TU HTML REAL: .step[data-step]
    const steps = document.querySelectorAll('.progress-steps .step');
    
    console.log(`✓ Encontrados ${steps.length} indicadores`);
    
    steps.forEach((step, index) => {
        const numPaso = index + 1;
        const circle = step.querySelector('.step-circle');
        
        // Remover todas las clases
        step.classList.remove('active', 'completed');
        if (circle) {
            circle.classList.remove('active', 'completed');
        }
        
        if (numPaso < paso) {
            // Paso completado
            step.classList.add('completed');
            if (circle) circle.classList.add('completed');
            console.log(`  ✓ Paso ${numPaso}: COMPLETADO (verde)`);
        } else if (numPaso === paso) {
            // Paso actual
            step.classList.add('active');
            if (circle) circle.classList.add('active');
            console.log(`  ✓ Paso ${numPaso}: ACTUAL (amarillo)`);
        } else {
            // Paso pendiente
            console.log(`  ✓ Paso ${numPaso}: pendiente`);
        }
    });
    
    // Actualizar barra de progreso
    actualizarBarraProgreso(paso);
}

function actualizarBarraProgreso(paso) {
    const progressFill = document.getElementById('progressFill');
    if (progressFill) {
        const porcentaje = ((paso - 1) / (totalPasos - 1)) * 100;
        progressFill.style.width = porcentaje + '%';
        console.log(`  ✓ Barra progreso: ${porcentaje}%`);
    }
}

function actualizarBotones(paso) {
    const btnAnterior = document.getElementById('btnAnterior');
    const btnSiguiente = document.getElementById('btnSiguiente');
    const btnConfirmar = document.getElementById('btnConfirmar');
    
    if (btnAnterior) {
        btnAnterior.style.display = paso === 1 ? 'none' : 'inline-flex';
    }
    
    if (btnSiguiente && btnConfirmar) {
        if (paso === totalPasos) {
            btnSiguiente.style.display = 'none';
            btnConfirmar.style.display = 'inline-flex';
        } else {
            btnSiguiente.style.display = 'inline-flex';
            btnConfirmar.style.display = 'none';
        }
    }
}

window.siguientePaso = async function(e) {
    if (e) e.preventDefault();
    
    console.log(`\n➡️ SIGUIENTE - Paso actual: ${pasoActual}`);
    
    if (!validarPasoActual()) {
        console.log('❌ Validación falló');
        return;
    }
    
    console.log('✅ Validación OK');
    guardarDatosPaso();
    
    // ============================================
    // NUEVO: Si va al Paso 2, cargar recomendaciones
    // ============================================
    if (pasoActual === 1) {
        console.log('🔍 Cargando recomendaciones automáticas...');
        mostrarPaso(2);
        await cargarRecomendaciones();
    } else if (pasoActual < totalPasos) {
        mostrarPaso(pasoActual + 1);
    }
};

window.anteriorPaso = function(e) {
    if (e) e.preventDefault();
    
    if (pasoActual > 1) {
        console.log(`⬅️ Paso anterior`);
        guardarDatosPaso();
        mostrarPaso(pasoActual - 1);
    }
};

// ============================================
// VALIDACIÓN
// ============================================

function validarPasoActual() {
    switch(pasoActual) {
        case 1: return validarPaso1();
        case 2: return validarPaso2();
        case 3: return validarPaso3();
        case 4: return validarPaso4();
        default: return true;
    }
}

function validarPaso1() {
    const placa = document.getElementById('placa');
    const marca = document.getElementById('marca');
    const modelo = document.getElementById('modelo');
    const anio = document.getElementById('anio');
    
    if (!placa?.value) { alert('Ingresa la placa'); return false; }
    if (!marca?.value) { alert('Selecciona la marca'); return false; }
    if (!modelo?.value) { alert('Ingresa el modelo'); return false; }
    if (!anio?.value) { alert('Ingresa el año'); return false; }
    
    return true;
}


// Después de validar Paso 1, antes de mostrar Paso 2
async function cargarRecomendaciones() {
    if (!marcaSeleccionada || !modeloSeleccionado) {
        console.error('❌ Falta seleccionar marca o modelo');
        mostrarMensajeSinRecomendaciones();
        return;
    }
    
    const anio = parseInt(datosFormulario.anio) || 0;
    const km = parseInt(datosFormulario.kilometraje) || 0;
    
    console.log('🔍 Buscando recomendaciones...', {
        marca_id: marcaSeleccionada.id,
        modelo_id: modeloSeleccionado.id,
        anio,
        kilometraje: km
    });
    
    try {
        const response = await fetch(
            `/api/v1/recomendaciones/buscar-por-ids?marca_id=${marcaSeleccionada.id}&modelo_id=${modeloSeleccionado.id}&anio=${anio}&kilometraje=${km}`
        );
        
        const data = await response.json();
        
        if (!data.success) {
            console.warn('⚠️ No hay recomendaciones:', data.error);
            mostrarMensajeSinRecomendaciones();
            return;
        }
        
        console.log('✅ Recomendaciones:', data);
        
        // Renderizar opciones de aceites
        renderizarOpcionesAceite(data.aceites, data.especificaciones);
        
        // Renderizar filtros
        renderizarOpcionesFiltros(data.filtros);
        
    } catch (error) {
        console.error('❌ Error:', error);
        mostrarMensajeSinRecomendaciones();
    }
}

function mostrarMensajeSinRecomendaciones() {
    const container = document.getElementById('opcionesAceite');
    container.innerHTML = `
        <div style="text-align: center; padding: 2rem; background: rgba(245, 158, 11, 0.1); border-radius: 12px;">
            <i class="fas fa-exclamation-triangle" style="font-size: 3rem; color: #F59E0B; margin-bottom: 1rem;"></i>
            <h3 style="color: #F59E0B; margin-bottom: 0.5rem;">No hay recomendaciones específicas</h3>
            <p style="color: rgba(255,255,255,0.7);">
                Aún no tenemos productos recomendados para este vehículo.<br>
                Nuestro equipo te contactará para ofrecerte las mejores opciones.
            </p>
        </div>
    `;
}

function renderizarOpcionesAceite(aceites, specs) {
    const container = document.getElementById('opcionesAceite');
    
    // Header con especificaciones - SIN TEMPLATE LITERALS
    let html = '<div class="recomendacion-header">';
    html += '  <h3>🛢️ Aceite recomendado para tu vehículo</h3>';
    html += '  <div class="specs-box">';
    html += '    <div class="spec-item">';
    html += '      <i class="fas fa-flask"></i>';
    html += '      <span>' + specs.viscosidad + '</span>';
    html += '    </div>';
    html += '    <div class="spec-item">';
    html += '      <i class="fas fa-certificate"></i>';
    html += '      <span>' + specs.tipo_aceite + '</span>';
    html += '    </div>';
    html += '    <div class="spec-item">';
    html += '      <i class="fas fa-tint"></i>';
    html += '      <span>' + specs.capacidad_litros + ' litros</span>';
    html += '    </div>';
    html += '  </div>';
    
    if (specs.notas) {
        html += '  <p class="specs-note">' + specs.notas + '</p>';
    }
    
    html += '</div>';
    html += '<div class="aceites-carrusel">';
    html += '  <button type="button" class="carrusel-btn prev" onclick="moverCarrusel(-1)">';
    html += '    <i class="fas fa-chevron-left"></i>';
    html += '  </button>';
    html += '  <div class="carrusel-container">';
    html += '    <div class="carrusel-track" id="carruselTrack">';
    
    // Contador de opciones totales
    let totalOpciones = 0;
    
    // OEM (Fabricante)
    if (aceites.oem && aceites.oem.length > 0) {
        totalOpciones++;
        html += crearTarjetaAceite(aceites.oem[0], 'oem', 'RECOMENDADO FABRICANTE');
    }
    
    // Premium (2-3 opciones)
    if (aceites.premium && aceites.premium.length > 0) {
        aceites.premium.slice(0, 2).forEach(function(aceite) {
            totalOpciones++;
            html += crearTarjetaAceite(aceite, 'premium', 'ALTA CALIDAD');
        });
    }
    
    // Estándar (2-3 opciones)
    if (aceites.estandar && aceites.estandar.length > 0) {
        aceites.estandar.slice(0, 2).forEach(function(aceite) {
            totalOpciones++;
            html += crearTarjetaAceite(aceite, 'estandar', 'MÁS USADO');
        });
    }
    
    // Económico (1-2 opciones)
    if (aceites.economico && aceites.economico.length > 0) {
        aceites.economico.slice(0, 2).forEach(function(aceite) {
            totalOpciones++;
            html += crearTarjetaAceite(aceite, 'economico', 'ECONÓMICO');
        });
    }
    
    html += '    </div>';
    html += '  </div>';
    html += '  <button type="button" class="carrusel-btn next" onclick="moverCarrusel(1)">';
    html += '    <i class="fas fa-chevron-right"></i>';
    html += '  </button>';
    html += '</div>';
    html += '<div class="carrusel-dots" id="carruselDots"></div>';
    
    container.innerHTML = html;
    
    // Inicializar carrusel
    inicializarCarrusel(totalOpciones);
}

function crearTarjetaAceite(aceite, tipo, badge) {
    const badgeColors = {
        'oem': 'badge-oem',
        'premium': 'badge-premium',
        'estandar': 'badge-estandar',
        'economico': 'badge-economico'
    };
    
    const nombreSafe = String(aceite.nombre || '').replace(/'/g, "\\'").replace(/"/g, "&quot;");
    
    // ✅ RUTA CORRECTA + ROMPER LOOP CON onerror=null
    const imagenUrl = aceite.imagen_url || '/static/img/aceite-generico.png';
    
    let html = '<div class="aceite-card">';
    html += '  <div class="badge ' + badgeColors[tipo] + '">' + badge + '</div>';
    html += '  <div class="aceite-imagen">';
    html += '    <img src="' + imagenUrl + '" ';
    html += '         alt="' + nombreSafe + '" ';
    html += '         onerror="this.onerror=null; this.src=\'/static/img/aceite-generico.png\'">';
    html += '  </div>';
    html += '  <div class="aceite-info">';
    html += '    <h4 class="aceite-nombre">' + aceite.nombre + '</h4>';
    
    if (aceite.marca) {
        html += '    <p class="aceite-marca">' + aceite.marca + '</p>';
    }
    
    if (aceite.descripcion) {
        html += '    <p class="aceite-desc">' + aceite.descripcion.substring(0, 80) + '...</p>';
    }
    
    html += '  </div>';
    html += '  <div class="aceite-footer">';
    html += '    <div class="aceite-precio">';
    html += '      <span class="precio-label">Precio:</span>';
    html += '      <span class="precio-valor">S/ ' + aceite.precio.toFixed(2) + '</span>';
    html += '    </div>';
    
    if (aceite.stock > 0) {
        html += '    <button class="btn-seleccionar-aceite" ';
        html += '            data-id="' + aceite.id + '" ';
        html += '            data-precio="' + aceite.precio + '" ';
        html += '            data-nombre="' + nombreSafe + '" ';
        html += '            onclick="seleccionarAceiteBtn(this)">';
        html += '      <i class="fas fa-check-circle"></i>';
        html += '      Seleccionar';
        html += '    </button>';
    } else {
        html += '    <button class="btn-sin-stock" disabled>';
        html += '      <i class="fas fa-times-circle"></i>';
        html += '      Sin stock';
        html += '    </button>';
    }
    
    html += '  </div>';
    html += '</div>';
    
    return html;
}

function seleccionarAceiteBtn(boton) {
    const id = parseInt(boton.getAttribute('data-id'));
    const precio = parseFloat(boton.getAttribute('data-precio'));
    const nombre = boton.getAttribute('data-nombre');
    
    // Guardar selección
    datosFormulario.aceite_id = id;
    datosFormulario.aceite_precio = precio;
    datosFormulario.aceite_nombre = nombre;
    
    // Marcar visualmente
    document.querySelectorAll('.aceite-card').forEach(card => {
        card.classList.remove('seleccionado');
    });
    boton.closest('.aceite-card').classList.add('seleccionado');
    
    // Actualizar precio
    actualizarTotalPaso2();
    
    console.log('✅ Aceite seleccionado:', nombre, precio);
}

// Variables globales del carrusel
let carruselPos = 0;
let carruselTotal = 0;

function inicializarCarrusel(total) {
    carruselTotal = total;
    carruselPos = 0;
    
    // Crear dots
    const dotsContainer = document.getElementById('carruselDots');
    if (dotsContainer) {
        let dotsHtml = '';
        for (let i = 0; i < total; i++) {
            dotsHtml += `<span class="dot ${i === 0 ? 'active' : ''}" onclick="irASlide(${i})"></span>`;
        }
        dotsContainer.innerHTML = dotsHtml;
    }
    
    actualizarCarrusel();
}

function moverCarrusel(direccion) {
    carruselPos += direccion;
    
    // Loop infinito
    if (carruselPos < 0) carruselPos = carruselTotal - 1;
    if (carruselPos >= carruselTotal) carruselPos = 0;
    
    actualizarCarrusel();
}

function irASlide(index) {
    carruselPos = index;
    actualizarCarrusel();
}

function actualizarCarrusel() {
    const track = document.getElementById('carruselTrack');
    if (track) {
        track.style.transform = `translateX(-${carruselPos * 100}%)`;
    }
    
    // Actualizar dots
    document.querySelectorAll('.carrusel-dots .dot').forEach((dot, index) => {
        dot.classList.toggle('active', index === carruselPos);
    });
}

function seleccionarAceite(id, precio, nombre, boton) {
    datosFormulario.aceite_id = id;
    datosFormulario.aceite_precio = precio;
    datosFormulario.aceite_nombre = nombre;
    
    // Marcar visualmente
    document.querySelectorAll('.aceite-card').forEach(card => {
        card.classList.remove('seleccionado');
    });
    boton.closest('.aceite-card').classList.add('seleccionado');
    
    actualizarTotalPaso2();
    
    console.log('✅ Aceite seleccionado:', nombre, precio);
}

function renderizarOpcionesFiltros(filtros) {
    const container = document.getElementById('opcionesFiltros');
    
    if (!filtros || (!filtros.aceite && !filtros.aire && !filtros.combustible)) {
        container.innerHTML = '';
        return;
    }
    
    let html = `
        <div class="recomendacion-header">
            <h3>🔧 Filtros recomendados</h3>
            <p class="specs">Selecciona los filtros que deseas cambiar</p>
        </div>
        <div class="filtros-grid">
    `;
    
    // Filtro de aceite (obligatorio)
    if (filtros.aceite) {
        html += `
            <div class="filtro-card obligatorio">
                <div class="badge-obligatorio">OBLIGATORIO</div>
                <img src="${filtros.aceite.imagen_url || '/static/img/default-filter.png'}" alt="Filtro aceite">
                <h4>Filtro de Aceite</h4>
                <p>${filtros.aceite.nombre}</p>
                <div class="precio">S/ ${filtros.aceite.precio.toFixed(2)}</div>
                <input type="checkbox" id="filtro_aceite" checked disabled>
                <label for="filtro_aceite">Incluido</label>
            </div>
        `;
        datosFormulario.filtro_aceite_id = filtros.aceite.id;
        datosFormulario.filtro_aceite_precio = filtros.aceite.precio;
    }
    
    // Filtro de aire (opcional)
    if (filtros.aire) {
        html += `
            <div class="filtro-card">
                <div class="badge-opcional">OPCIONAL</div>
                <img src="${filtros.aire.imagen_url || '/static/img/default-filter.png'}" alt="Filtro aire">
                <h4>Filtro de Aire</h4>
                <p>${filtros.aire.nombre}</p>
                <div class="precio">S/ ${filtros.aire.precio.toFixed(2)}</div>
                <input type="checkbox" id="filtro_aire" onchange="toggleFiltro('aire', ${filtros.aire.id}, ${filtros.aire.precio})">
                <label for="filtro_aire">Agregar</label>
            </div>
        `;
    }
    
    // Filtro combustible (opcional)
    if (filtros.combustible) {
        html += `
            <div class="filtro-card">
                <div class="badge-opcional">OPCIONAL</div>
                <img src="${filtros.combustible.imagen_url || '/static/img/default-filter.png'}" alt="Filtro combustible">
                <h4>Filtro de Combustible</h4>
                <p>${filtros.combustible.nombre}</p>
                <div class="precio">S/ ${filtros.combustible.precio.toFixed(2)}</div>
                <input type="checkbox" id="filtro_combustible" onchange="toggleFiltro('combustible', ${filtros.combustible.id}, ${filtros.combustible.precio})">
                <label for="filtro_combustible">Agregar</label>
            </div>
        `;
    }
    
    html += '</div>';
    container.innerHTML = html;
    
    actualizarTotalPaso2();
}

function toggleFiltro(tipo, id, precio) {
    const checkbox = document.getElementById(`filtro_${tipo}`);
    
    if (checkbox.checked) {
        datosFormulario[`filtro_${tipo}_id`] = id;
        datosFormulario[`filtro_${tipo}_precio`] = precio;
    } else {
        delete datosFormulario[`filtro_${tipo}_id`];
        delete datosFormulario[`filtro_${tipo}_precio`];
    }
    
    actualizarTotalPaso2();
}

function actualizarTotalPaso2() {
    let total = 50; // Servicio base
    
    // Aceite
    if (datosFormulario.aceite_precio) {
        total += parseFloat(datosFormulario.aceite_precio);
        document.getElementById('precioAceiteRow').style.display = 'flex';
        document.getElementById('precioAceiteValor').textContent = `S/ ${datosFormulario.aceite_precio.toFixed(2)}`;
    }
    
    // Filtros
    let totalFiltros = 0;
    if (datosFormulario.filtro_aceite_precio) totalFiltros += parseFloat(datosFormulario.filtro_aceite_precio);
    if (datosFormulario.filtro_aire_precio) totalFiltros += parseFloat(datosFormulario.filtro_aire_precio);
    if (datosFormulario.filtro_combustible_precio) totalFiltros += parseFloat(datosFormulario.filtro_combustible_precio);
    
    if (totalFiltros > 0) {
        total += totalFiltros;
        document.getElementById('precioFiltroRow').style.display = 'flex';
        document.getElementById('precioFiltroValor').textContent = `S/ ${totalFiltros.toFixed(2)}`;
    }
    
    document.getElementById('totalEstimadoPaso2').textContent = `S/ ${total.toFixed(2)}`;
}


function validarPaso2() {
    console.log('📝 Validando Paso 2: Servicio');
    
    // Verificar que haya seleccionado aceite
    if (!datosFormulario.aceite_id) {
        alert('Por favor selecciona un tipo de aceite');
        return false;
    }
    
    console.log('✅ Paso 2 OK - Aceite seleccionado:', datosFormulario.aceite_id);
    return true;
}

function validarPaso3() {
    const distrito = document.querySelector('select[name="distrito"]');
    const direccion = document.getElementById('direccion');
    
    if (!distrito?.value) { alert('Selecciona el distrito'); return false; }
    if (!direccion?.value?.trim()) { alert('Ingresa la dirección'); return false; }
    
    return true;
}

function validarPaso4() {
    const terminos = document.querySelector('input[name="acepto_terminos"]');
    
    if (!terminos?.checked) {
        alert('Debes aceptar los términos');
        return false;
    }
    
    return true;
}

// ============================================
// GUARDAR DATOS
// ============================================

function guardarDatosPaso() {
    const formulario = document.querySelector(`.form-step[data-step="${pasoActual}"]`);
    if (!formulario) return;

    switch(pasoActual) {
        case 1: guardarPaso1(); break;

        case 2: 
            // Guardar notas
            const notas = formulario.querySelector('[name="notas"]');
            if (notas) datosFormulario.notas = notas.value;
            
            console.log('💾 Paso 2 guardado (productos ya en datosFormulario)');
            break;

        case 3: guardarPaso3(); break;
        case 4: guardarPaso4(); break;
    }
    console.log('💾 Datos:', datosFormulario);
}

function guardarPaso1() {
    datosFormulario.placa = document.getElementById('placa')?.value?.toUpperCase();
    datosFormulario.marca_id = marcaSeleccionada?.id;
    datosFormulario.marca = marcaSeleccionada?.nombre;
    datosFormulario.modelo_id = modeloSeleccionado?.id;
    datosFormulario.modelo = modeloSeleccionado?.nombre;
    datosFormulario.anio = document.getElementById('anio')?.value;
    datosFormulario.kilometraje = document.getElementById('kilometraje')?.value;
    
    console.log('💾 Paso 1 guardado:', datosFormulario);
}

function guardarPaso2() {
    // Guardar notas
    const formulario = document.querySelector('.form-step[data-step="2"]');
    const notas = formulario?.querySelector('[name="notas"]');
    if (notas) datosFormulario.notas = notas.value;
    
    // Los datos de aceite YA están guardados por seleccionarAceiteBtn()
    // Los datos de filtros YA están guardados por toggleFiltro()
    
    console.log('💾 Paso 2 guardado:', {
        aceite_id: datosFormulario.aceite_id,
        aceite_precio: datosFormulario.aceite_precio,
        aceite_nombre: datosFormulario.aceite_nombre,
        filtros: {
            aceite: datosFormulario.filtro_aceite_precio,
            aire: datosFormulario.filtro_aire_precio,
            combustible: datosFormulario.filtro_combustible_precio
        }
    });
}

function guardarPaso3() {
    const distrito = document.querySelector('select[name="distrito"]');
    const direccion = document.getElementById('direccion');
    const referencia = document.querySelector('input[name="referencia"]');
    const numero = document.querySelector('input[name="numero_casa"]');
    const piso = document.querySelector('input[name="piso"]');
    
    datosFormulario.distrito = distrito?.value || '';
    datosFormulario.distritoTexto = distrito?.options[distrito.selectedIndex]?.text || '';
    datosFormulario.direccion = direccion?.value || '';
    datosFormulario.referencia = referencia?.value || '';
    datosFormulario.numero_casa = numero?.value || '';
    datosFormulario.piso = piso?.value || '';
}

function guardarPaso4() {
    const terminos = document.querySelector('input[name="acepto_terminos"]');
    datosFormulario.acepto_terminos = terminos?.checked || false;
}

// ============================================
// ACTUALIZAR RESUMEN
// ============================================

function actualizarResumen() {
    console.log('📋 Actualizando resumen...');
    
    const vehiculo = `${datosFormulario.marcaTexto || datosFormulario.marca || '?'} ${datosFormulario.modelo || '?'} ${datosFormulario.anio || '?'}`;
    const km = parseInt(datosFormulario.kilometraje) || 0;
    
    actualizarElemento('resumenVehiculo', vehiculo);
    actualizarElemento('resumenPlaca', datosFormulario.placa || '-');
    actualizarElemento('resumenKilometraje', km.toLocaleString('es-PE') + ' km');
    actualizarElemento('resumenAceite', datosFormulario.tipo_aceite_texto || '-');
    actualizarElemento('resumenFiltro', datosFormulario.incluir_filtro === 'si' ? 'Sí incluido' : 'No incluido');
    
    // FECHA/HORA: Ocultar este campo porque se selecciona después en calendario
    const elemFechaHora = document.getElementById('resumenFechaHora');
    if (elemFechaHora) {
        const contenedor = elemFechaHora.closest('.form-group') || 
                          elemFechaHora.closest('.resumen-item') ||
                          elemFechaHora.parentElement;
        if (contenedor) {
            contenedor.style.display = 'none';
            console.log('  ✓ Campo fecha/hora ocultado (se selecciona en calendario)');
        }
    }
    
    actualizarElemento('resumenDireccion', datosFormulario.direccion || '-');
    actualizarElemento('resumenDistrito', datosFormulario.distritoTexto || '-');
}

function actualizarElemento(id, valor) {
    const elem = document.getElementById(id);
    if (elem) {
        elem.textContent = valor;
        console.log(`  ✓ ${id}: "${valor}"`);
    }
}

function actualizarPrecioTotal() {
    const precioServicio = 50;
    const precioAceite = datosFormulario.precio_aceite || 0;
    const precioFiltro = datosFormulario.incluir_filtro === 'si' ? 30 : 0;
    const total = precioServicio + precioAceite + precioFiltro;
    
    console.log(`💰 Total: S/.${total} (${precioServicio} + ${precioAceite} + ${precioFiltro})`);
    
    const elemTotal = document.getElementById('resumenTotal') || 
                     document.getElementById('totalEstimado');
    
    if (elemTotal) {
        elemTotal.textContent = `S/.${total}`;
    }
}

function actualizarPrecioPaso2() {
    const tipoAceiteSelect = document.getElementById('tipoAceite');
    if (!tipoAceiteSelect) return;
    
    const selectedOption = tipoAceiteSelect.options[tipoAceiteSelect.selectedIndex];
    const precioAceite = parseInt(selectedOption.dataset.precio) || 0;
    const filtroSi = document.querySelector('input[name="incluir_filtro"][value="si"]:checked');
    const precioFiltro = filtroSi ? 30 : 0;
    const total = 50 + precioAceite + precioFiltro;
    
    const elemPrecioAceite = document.getElementById('precioAceiteValor');
    const elemRowAceite = document.getElementById('precioAceite');
    const elemTotal = document.getElementById('totalEstimado');
    
    if (precioAceite > 0 && elemRowAceite) {
        elemRowAceite.style.display = 'flex';
        if (elemPrecioAceite) elemPrecioAceite.textContent = `S/.${precioAceite}`;
    }
    
    if (elemTotal) elemTotal.textContent = `S/.${total}`;
}


function mostrarResumenPaso4() {
    console.log('📋 Mostrando resumen Paso 4:', datosFormulario);
    
    // ============================================
    // VEHÍCULO
    // ============================================
    const vehiculoTexto = (datosFormulario.marca || '') + ' ' + (datosFormulario.modelo || '') + ' ' + (datosFormulario.anio || '');
    document.getElementById('resumenVehiculo').textContent = vehiculoTexto;
    document.getElementById('resumenPlaca').textContent = datosFormulario.placa || '-';
    document.getElementById('resumenKilometraje').textContent = (datosFormulario.kilometraje || '0') + ' km';
    
    // ============================================
    // SERVICIO
    // ============================================
    const aceiteTexto = datosFormulario.aceite_nombre || 'No seleccionado';
    document.getElementById('resumenAceite').textContent = aceiteTexto;
    
    // Contar filtros seleccionados
    let filtrosCount = 0;
    if (datosFormulario.filtro_aceite_id) filtrosCount++;
    if (datosFormulario.filtro_aire_id) filtrosCount++;
    if (datosFormulario.filtro_combustible_id) filtrosCount++;
    
    document.getElementById('resumenFiltro').textContent = filtrosCount + ' filtro(s) seleccionado(s)';
    
    // Fecha y hora (se llenarán después del calendario)
    const fechaHora = datosFormulario.fecha_servicio && datosFormulario.hora_servicio
        ? datosFormulario.fecha_servicio + ' a las ' + datosFormulario.hora_servicio
        : 'Por seleccionar';
    document.getElementById('resumenFechaHora').textContent = fechaHora;
    
    // ============================================
    // UBICACIÓN
    // ============================================
    document.getElementById('resumenDireccion').textContent = datosFormulario.direccion || '-';
    document.getElementById('resumenDistrito').textContent = datosFormulario.distrito || '-';
    
    // ============================================
    // CALCULAR TOTAL
    // ============================================
    let total = 50; // Servicio base a domicilio
    
    // Aceite
    if (datosFormulario.aceite_precio) {
        total += parseFloat(datosFormulario.aceite_precio);
    }
    
    // Filtros
    if (datosFormulario.filtro_aceite_precio) {
        total += parseFloat(datosFormulario.filtro_aceite_precio);
    }
    if (datosFormulario.filtro_aire_precio) {
        total += parseFloat(datosFormulario.filtro_aire_precio);
    }
    if (datosFormulario.filtro_combustible_precio) {
        total += parseFloat(datosFormulario.filtro_combustible_precio);
    }
    
    // Materiales incluidos (NO se muestra separado, está en el precio base)
    // Los S/ 50 del servicio YA incluyen materiales básicos
    
    document.getElementById('resumenTotal').textContent = 'S/ ' + total.toFixed(2);
    
    // Guardar total en datosFormulario
    datosFormulario.total_estimado = total;
    
    console.log('✅ Resumen actualizado. Total:', total);
    
    // ============================================
    // LLENAR resumenPaso4 con desglose detallado
    // ============================================
    let detalleHTML = '<div class="resumen-detallado">';
    detalleHTML += '  <h3><i class="fas fa-receipt"></i> Desglose del servicio</h3>';
    
    detalleHTML += '  <div class="item-resumen">';
    detalleHTML += '    <span><i class="fas fa-home"></i> Servicio a domicilio</span>';
    detalleHTML += '    <strong>S/ 50.00</strong>';
    detalleHTML += '  </div>';
    
    if (datosFormulario.aceite_precio) {
        detalleHTML += '  <div class="item-resumen">';
        detalleHTML += '    <span><i class="fas fa-oil-can"></i> ' + aceiteTexto + '</span>';
        detalleHTML += '    <strong>S/ ' + parseFloat(datosFormulario.aceite_precio).toFixed(2) + '</strong>';
        detalleHTML += '  </div>';
    }
    
    if (filtrosCount > 0) {
        let totalFiltros = 0;
        if (datosFormulario.filtro_aceite_precio) totalFiltros += parseFloat(datosFormulario.filtro_aceite_precio);
        if (datosFormulario.filtro_aire_precio) totalFiltros += parseFloat(datosFormulario.filtro_aire_precio);
        if (datosFormulario.filtro_combustible_precio) totalFiltros += parseFloat(datosFormulario.filtro_combustible_precio);
        
        detalleHTML += '  <div class="item-resumen">';
        detalleHTML += '    <span><i class="fas fa-filter"></i> Filtros (' + filtrosCount + ')</span>';
        detalleHTML += '    <strong>S/ ' + totalFiltros.toFixed(2) + '</strong>';
        detalleHTML += '  </div>';
    }
    
    detalleHTML += '  <div class="item-resumen incluido">';
    detalleHTML += '    <span><i class="fas fa-check-circle"></i> Materiales básicos incluidos</span>';
    detalleHTML += '    <strong class="incluido-text">Incluido</strong>';
    detalleHTML += '  </div>';
    
    detalleHTML += '  <p class="nota-materiales">';
    detalleHTML += '    <i class="fas fa-info-circle"></i> ';
    detalleHTML += '    Incluye: agua desmineralizada, shampoo automotriz, trapos industriales';
    detalleHTML += '  </p>';
    
    detalleHTML += '</div>';
    
    const contenedorResumen = document.getElementById('resumenPaso4');
    if (contenedorResumen) {
        contenedorResumen.innerHTML = detalleHTML;
    }
}


// ============================================
// VARIABLES GLOBALES PARA VEHÍCULO
// ============================================
let marcasVehiculos = [];
let modelosVehiculos = [];
let marcaSeleccionada = null;
let modeloSeleccionado = null;

// ============================================
// CARGAR MARCAS DESDE BD
// ============================================
async function cargarMarcasVehiculos() {
    try {
        const response = await fetch('/api/v1/recomendaciones/marcas');
        const data = await response.json();
        
        if (!data.success) {
            console.error('Error al cargar marcas');
            return;
        }
        
        marcasVehiculos = data.marcas;
        
        const selectMarca = document.getElementById('marca');
        if (!selectMarca) {
            console.warn('⚠️ Select marca no encontrado');
            return;
        }
        
        selectMarca.innerHTML = '<option value="">Selecciona la marca</option>';
        
        data.marcas.forEach(marca => {
            const option = document.createElement('option');
            option.value = marca.id;
            option.textContent = marca.nombre;
            option.dataset.nombre = marca.nombre;
            selectMarca.appendChild(option);
        });
        
        console.log('✅ Marcas cargadas:', data.marcas.length);
        
    } catch (error) {
        console.error('Error al cargar marcas:', error);
    }
}

// ============================================
// CARGAR MODELOS AL SELECCIONAR MARCA
// ============================================
window.cargarModelosPorMarca = async function() {
    const selectMarca = document.getElementById('marca');
    const selectModelo = document.getElementById('modelo');
    
    const marcaId = selectMarca.value;
    
    if (!marcaId) {
        selectModelo.innerHTML = '<option value="">Primero selecciona una marca</option>';
        selectModelo.disabled = true;
        modeloSeleccionado = null;
        return;
    }
    
    marcaSeleccionada = {
        id: parseInt(marcaId),
        nombre: selectMarca.options[selectMarca.selectedIndex].dataset.nombre
    };
    
    console.log('🔍 Cargando modelos para marca:', marcaSeleccionada.nombre);
    
    try {
        const response = await fetch(`/api/v1/recomendaciones/modelos/${marcaId}`);
        const data = await response.json();
        
        if (!data.success) {
            selectModelo.innerHTML = '<option value="">No hay modelos disponibles</option>';
            return;
        }
        
        modelosVehiculos = data.modelos;
        
        selectModelo.innerHTML = '<option value="">Selecciona el modelo</option>';
        selectModelo.disabled = false;
        
        data.modelos.forEach(modelo => {
            const option = document.createElement('option');
            option.value = modelo.id;
            option.textContent = modelo.nombre;
            option.dataset.nombre = modelo.nombre;
            selectModelo.appendChild(option);
        });
        
        console.log('✅ Modelos cargados:', data.modelos.length);
        
    } catch (error) {
        console.error('Error al cargar modelos:', error);
    }
};

function guardarModeloSeleccionado() {
    const selectModelo = document.getElementById('modelo');
    if (selectModelo && selectModelo.value) {
        modeloSeleccionado = {
            id: parseInt(selectModelo.value),
            nombre: selectModelo.options[selectModelo.selectedIndex].dataset.nombre
        };
        console.log('✅ Modelo seleccionado:', modeloSeleccionado);
    }
}


// ============================================
// SUBMIT
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('solicitudForm');
    if (form) {
        form.addEventListener('submit', handleSubmit);
    }
});

function handleSubmit(e) {
    e.preventDefault();
    
    console.log('📤 SUBMIT');
    
    if (!validarPaso4()) return false;
    
    guardarDatosPaso();
    
    // ============================================
    // NUEVO: Verificar datos de contacto
    // ============================================
    
    const tieneNombre = sessionStorage.getItem('temp_nombre');
    const tieneTelefono = sessionStorage.getItem('temp_telefono');
    
    if (!tieneNombre || !tieneTelefono) {
        console.log('⚠️ Faltan datos de contacto - mostrando modal');
        mostrarModalContacto();
        return false;
    }
    
    // ============================================
    // Continuar flujo normal
    // ============================================
    
    const solicitud = {
        id: 'SERV-' + Date.now(),
        vehiculo: {
            placa: datosFormulario.placa || '',
            marca: datosFormulario.marca || '',
            modelo: datosFormulario.modelo || '',
            anio: datosFormulario.anio || '',
            color: datosFormulario.color || '',
            kilometraje: parseInt(datosFormulario.kilometraje) || 0
        },
        servicio: {
            tipo: 'cambio_aceite',
            tipo_aceite: datosFormulario.tipo_aceite || '',
            precio_aceite: datosFormulario.precio_aceite || 0,
            incluir_filtro: datosFormulario.incluir_filtro === 'si',
            fecha: datosFormulario.fecha || '',
            hora: datosFormulario.hora || '',
            notas: datosFormulario.notas || ''
        },
        ubicacion: {
            distrito: datosFormulario.distrito || '',
            direccion: datosFormulario.direccion || '',
            referencia: datosFormulario.referencia || '',
            numero_casa: datosFormulario.numero_casa || '',
            piso: datosFormulario.piso || ''
        },
        contacto: {
            nombre: sessionStorage.getItem('temp_nombre') || '',
            telefono: sessionStorage.getItem('temp_telefono') || ''
        },
        estado: 'iniciado',
        created_at: new Date().toISOString()
    };
    
    console.log('📦 Solicitud:', solicitud);
    
    try {
        localStorage.setItem('solicitud_actual', JSON.stringify(solicitud));
        console.log('✅ Guardado');
    } catch (error) {
        console.error('❌ Error:', error);
        alert('Error al guardar');
        return false;
    }
    
    console.log('🔄 Redirigiendo...');
    
    setTimeout(() => {
        window.location.href = '/cliente/calendario-horarios';
    }, 300);
    
    return false;
}

// ============================================
// INICIALIZACIÓN
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ DOM CARGADO');
    
    mostrarPaso(1);
    
    // ============================================
    // NUEVO: Cargar marcas de vehículos
    // ============================================
    cargarMarcasVehiculos();
    
    // Event listener para cuando seleccione modelo
    const selectModelo = document.getElementById('modelo');
    if (selectModelo) {
        selectModelo.addEventListener('change', guardarModeloSeleccionado);
    }
    // ============================================
    
    // Remover required de fecha/hora en paso 2
    removerRequiredFechaHora();
    
    const slider = document.getElementById('kilometraje');
    if (slider) updateKmValue(slider.value);
    
    const fechaInput = document.getElementById('fechaServicio');
    if (fechaInput) {
        const hoy = new Date().toISOString().split('T')[0];
        fechaInput.setAttribute('min', hoy);
    }
    
    const tipoAceiteSelect = document.getElementById('tipoAceite');
    if (tipoAceiteSelect) {
        tipoAceiteSelect.addEventListener('change', actualizarPrecioPaso2);
    }
    
    const filtroRadios = document.querySelectorAll('input[name="incluir_filtro"]');
    filtroRadios.forEach(radio => {
        radio.addEventListener('change', actualizarPrecioPaso2);
    });
    
    actualizarPrecioPaso2();
    
    console.log('✅ LISTO');
});

// ============================================
// REMOVER REQUIRED DE FECHA/HORA (PASO 2)
// ============================================

function removerRequiredFechaHora() {
    console.log('🔧 Removiendo required de fecha/hora en paso 2...');
    
    // Buscar campos de fecha/hora en paso 2
    const paso2 = document.querySelector('.form-step[data-step="2"]');
    
    if (!paso2) {
        console.warn('  ⚠️ No se encontró paso 2');
        return;
    }
    
    // Campos a buscar
    const selectores = [
        '#fechaServicio',
        'input[name="fecha_servicio"]',
        'input[type="date"]',
        'select[name="hora_servicio"]'
    ];
    
    let removidos = 0;
    
    selectores.forEach(selector => {
        const campos = paso2.querySelectorAll(selector);
        campos.forEach(campo => {
            if (campo.hasAttribute('required')) {
                campo.removeAttribute('required');
                removidos++;
                console.log(`  ✓ Removido required de: ${selector}`);
            }
        });
    });
    
    if (removidos === 0) {
        console.log('  ℹ️ No se encontraron campos con required');
    } else {
        console.log(`  ✅ Total removidos: ${removidos}`);
    }
}


//============================================
// PARA EL MODAL DE CONTACTO
// ============================================ 
// ============================================
// NUEVA FUNCIÓN: Mostrar Modal Contacto
// ============================================

function mostrarModalContacto() {
    // Verificar si ya existe
    let modal = document.getElementById('modalContacto');
    
    if (modal) {
        modal.remove();
    }
    
    // Crear modal
    modal = document.createElement('div');
    modal.id = 'modalContacto';
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content-contacto">
            <!-- Header -->
            <div class="modal-header-contacto">
                <div class="modal-icon-header">
                    <span class="icon-circle">🎉</span>
                </div>
                <h2>¡Último paso!</h2>
                <p class="modal-subtitle">Elige cómo quieres continuar</p>
            </div>
            
            <!-- Opciones -->
            <div class="modal-body-contacto">
                
                <!-- OPCIÓN 1: Dejar datos -->
                <div class="opcion-card opcion-datos active" id="opcionDatos" onclick="seleccionarOpcion('datos')">
                    <div class="opcion-header">
                        <div class="opcion-icon">📝</div>
                        <div class="opcion-titulo">
                            <h3>Dejar mis datos</h3>
                            <p>Rápido y simple</p>
                        </div>
                        <div class="opcion-check">
                            <i class="fas fa-check-circle"></i>
                        </div>
                    </div>
                    
                    <div class="opcion-content" id="formDatos">
                        <div class="info-box-small">
                            <i class="fas fa-shield-alt"></i>
                            <p>Solo para coordinar el servicio. Sin spam ni publicidad.</p>
                        </div>
                        
                        <div class="form-group-modal">
                            <label>
                                <i class="fas fa-user"></i>
                                Nombre completo
                            </label>
                            <input 
                                type="text" 
                                id="inputNombre" 
                                placeholder="Juan Pérez"
                                required
                                minlength="2"
                            >
                            <div class="error-message" id="errorNombre"></div>
                        </div>
                        
                        <div class="form-group-modal">
                            <label>
                                <i class="fas fa-phone"></i>
                                Teléfono (9 dígitos)
                            </label>
                            <input 
                                type="tel" 
                                id="inputTelefono" 
                                placeholder="987654321"
                                maxlength="9"
                                pattern="[0-9]{9}"
                                required
                            >
                            <div class="error-message" id="errorTelefono"></div>
                        </div>
                        
                        <div class="uso-datos">
                            <h4>📞 ¿Cuándo te contactamos?</h4>
                            <ul>
                                <li><i class="fas fa-check"></i> Si el técnico no encuentra la dirección</li>
                                <li><i class="fas fa-check"></i> Confirmación antes de llegar</li>
                                <li><i class="fas fa-check"></i> Emergencias del servicio</li>
                            </ul>
                            <p class="garantia-text">
                                <i class="fas fa-ban"></i>
                                <strong>NO</strong> usamos WhatsApp personal ni enviamos publicidad
                            </p>
                        </div>
                        
                        <button type="button" class="btn-modal-primary" onclick="validarYContinuar()">
                            <i class="fas fa-arrow-right"></i>
                            Continuar al pago
                        </button>
                    </div>
                </div>
                
                <!-- OPCIÓN 2: Descargar APP -->
                <div class="opcion-card opcion-app" id="opcionApp" onclick="seleccionarOpcion('app')">
                    <div class="opcion-header">
                        <div class="opcion-icon">📱</div>
                        <div class="opcion-titulo">
                            <h3>Descargar la App</h3>
                            <p>Mejor experiencia [toca para + Info]</p>
                        </div>
                        <div class="opcion-check">
                            <i class="fas fa-check-circle"></i>
                        </div>
                    </div>
                    
                    <div class="opcion-content" id="formApp" style="display: none;">
                        <div class="app-benefits">
                            <h4>✨ Beneficios de la App:</h4>
                            <ul>
                                <li><i class="fas fa-bell"></i> Notificaciones en tiempo real</li>
                                <li><i class="fas fa-comments"></i> Chat directo con el técnico</li>
                                <li><i class="fas fa-history"></i> Historial de servicios</li>
                                <li><i class="fas fa-star"></i> Ofertas exclusivas</li>
                                <li><i class="fas fa-shield-check"></i> Tus datos protegidos</li>
                            </ul>
                        </div>
                        
                        <button type="button" class="btn-modal-secondary" onclick="instalarApp()">
                            <i class="fas fa-download"></i>
                            Instalar MITA App
                        </button>
                        
                        <p class="app-note">
                            Después de instalar, tus datos se guardarán automáticamente
                        </p>
                    </div>
                </div>
            </div>
            
            <div class="modal-footer-contacto">
                <p class="security-note">
                    <i class="fas fa-lock"></i>
                    Tus datos están protegidos según nuestra 
                    <a href="/politica-privacidad" target="_blank">política de privacidad</a>
                </p>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    aplicarEstilosModalContacto();
    
    // Mostrar modal con animación
    setTimeout(() => {
        modal.style.display = 'flex';
        setTimeout(() => {
            modal.classList.add('show');
        }, 10);
    }, 100);
    
    // Focus en nombre
    setTimeout(() => {
        document.getElementById('inputNombre')?.focus();
    }, 400);
}


// ============================================
// SELECCIONAR OPCIÓN
// ============================================

function seleccionarOpcion(tipo) {
    const opcionDatos = document.getElementById('opcionDatos');
    const opcionApp = document.getElementById('opcionApp');
    const formDatos = document.getElementById('formDatos');
    const formApp = document.getElementById('formApp');
    
    if (tipo === 'datos') {
        opcionDatos.classList.add('active');
        opcionApp.classList.remove('active');
        formDatos.style.display = 'block';
        formApp.style.display = 'none';
        
        setTimeout(() => {
            document.getElementById('inputNombre')?.focus();
        }, 100);
        
    } else if (tipo === 'app') {
        opcionApp.classList.add('active');
        opcionDatos.classList.remove('active');
        formApp.style.display = 'block';
        formDatos.style.display = 'none';
    }
}


// ============================================
// VALIDAR Y CONTINUAR
// ============================================

async function validarYContinuar() {
    const nombre = document.getElementById('inputNombre').value.trim();
    const telefono = document.getElementById('inputTelefono').value.trim();
    
    let errores = false;
    
    if (!nombre || nombre.length < 2) {
        document.getElementById('errorNombre').textContent = 'Ingresa un nombre válido';
        document.getElementById('inputNombre').classList.add('error');
        errores = true;
    } else {
        document.getElementById('errorNombre').textContent = '';
        document.getElementById('inputNombre').classList.remove('error');
    }
    
    const telefonoRegex = /^9\d{8}$/;
    if (!telefonoRegex.test(telefono)) {
        document.getElementById('errorTelefono').textContent = 'Debe comenzar con 9 y tener 9 dígitos';
        document.getElementById('inputTelefono').classList.add('error');
        errores = true;
    } else {
        document.getElementById('errorTelefono').textContent = '';
        document.getElementById('inputTelefono').classList.remove('error');
    }
    
    if (errores) return;
    
    // Guardar en sessionStorage
    sessionStorage.setItem('temp_nombre', nombre);
    sessionStorage.setItem('temp_telefono', telefono);
    
    console.log('✅ Datos guardados:', { nombre, telefono });
    
    // Cerrar modal
    const modal = document.getElementById('modalContacto');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => modal.remove(), 300);
    }
    
    // ============================================
    // NUEVO: CREAR SOLICITUD EN BD
    // ============================================
    
    try {
        const result = await solicitudManager.crearSolicitud({
            nombre_contacto: nombre,
            telefono_contacto: telefono,
            direccion_servicio: datosFormulario.direccion || '',
            referencias_direccion: datosFormulario.referencia || '',
            tipo_servicio: 'cambio_aceite',
            marca_vehiculo: datosFormulario.marca || '',
            modelo_vehiculo: datosFormulario.modelo || '',
            anio_vehiculo: parseInt(datosFormulario.anio) || null,
            placa_vehiculo: datosFormulario.placa || '',
            descripcion_adicional: datosFormulario.notas || ''
        });
        
        // Verificar éxito (puede venir como result.id o result.success)
        if (result.id || result.solicitud_id) {
            const solicitudId = result.id || result.solicitud_id;
            
            console.log('✅ Solicitud creada:', solicitudId);
            
            // Guardar ID
            localStorage.setItem('solicitud_actual_id', solicitudId);
            
            // Guardar objeto completo para calendario
            localStorage.setItem('solicitud_actual', JSON.stringify({
                id: solicitudId,
                vehiculo: {
                    marca: datosFormulario.marca,
                    modelo: datosFormulario.modelo,
                    placa: datosFormulario.placa,
                    anio: datosFormulario.anio
                },
                contacto: {
                    nombre: nombre,
                    telefono: telefono
                },
                ubicacion: {
                    direccion: datosFormulario.direccion,
                    distrito: datosFormulario.distrito
                },
                estado: 'iniciado'
            }));
            
            // ============================================
            // LIMPIAR sessionStorage para próxima solicitud
            // ============================================
            sessionStorage.removeItem('temp_nombre');
            sessionStorage.removeItem('temp_telefono');
            
            console.log('🧹 Datos temporales limpiados');
            
            if (typeof mostrarNotificacion === 'function') {
                mostrarNotificacion('Solicitud creada exitosamente', 'success');
            }
            
            // Redirigir a calendario
            setTimeout(() => {
                window.location.href = '/cliente/calendario-horarios';
            }, 500);
            
        } else {
            alert('Error al crear solicitud: ' + (result.error || 'Desconocido'));
        }
        
    } catch (error) {
        console.error('Error:', error);
        alert('Error de conexión. Intenta de nuevo.');
    }
}


// ============================================
// INSTALAR APP
// ============================================

// ============================================
// INSTALAR APP (usa sistema existente de base_pwa.html)
// ============================================

function instalarApp() {
    console.log('📱 Instalando app...');
    
    // Verificar si el prompt está disponible
    if (!window.deferredPrompt) {
        console.log('⚠️ Prompt no disponible');
        
        // Cerrar modal
        const modal = document.getElementById('modalContacto');
        if (modal) {
            modal.classList.remove('show');
            setTimeout(() => {
                modal.style.display = 'none';
            }, 300);
        }
        
        // Mostrar banner si no lo rechazó antes
        if (localStorage.getItem('installPromptDismissed') !== 'true') {
            showInstallPrompt();
            mostrarNotificacion('Presiona "Instalar" en el banner', 'info');
        } else {
            // Ya lo rechazó antes, dar instrucciones manuales
            mostrarNotificacion('Para instalar: Menú del navegador → Agregar a pantalla de inicio', 'info');
            
            // Volver a opción datos
            setTimeout(() => {
                mostrarModalContacto();
                seleccionarOpcion('datos');
            }, 3000);
        }
        
        return;
    }
    
    // Cerrar modal actual
    const modal = document.getElementById('modalContacto');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => {
            modal.style.display = 'none';
        }, 300);
    }
    
    // Mostrar el prompt nativo directamente
    window.deferredPrompt.prompt();
    
    // Esperar respuesta
    window.deferredPrompt.userChoice.then((choiceResult) => {
        console.log('👤 Decisión del usuario:', choiceResult.outcome);
        
        if (choiceResult.outcome === 'accepted') {
            console.log('✅ Usuario aceptó instalar');
            
            // Mostrar mensaje de éxito
            mostrarNotificacion('¡App instalada! Ahora completa tu servicio', 'success');
            
            // Esperar un momento y mostrar modal de datos
            setTimeout(() => {
                mostrarModalContacto();
                seleccionarOpcion('datos');
                
                // Mensaje adicional
                mostrarNotificacion('Por favor completa tus datos para continuar', 'info');
            }, 2000);
            
        } else {
            console.log('❌ Usuario rechazó instalar');
            
            // Guardar que rechazó (para no molestar de nuevo)
            localStorage.setItem('installPromptDismissed', 'true');
            
            // Mostrar mensaje
            mostrarNotificacion('No hay problema. Deja tus datos para continuar', 'info');
            
            // Volver a modal de datos
            setTimeout(() => {
                mostrarModalContacto();
                seleccionarOpcion('datos');
            }, 1500);
        }
        
        // Limpiar el prompt
        window.deferredPrompt = null;
        
    }).catch((error) => {
        console.error('❌ Error en instalación:', error);
        
        // En caso de error, volver a datos
        mostrarNotificacion('Hubo un problema. Deja tus datos para continuar', 'info');
        
        setTimeout(() => {
            mostrarModalContacto();
            seleccionarOpcion('datos');
        }, 1500);
    });
}


// ============================================
// ESTILOS INLINE
// ============================================

function aplicarEstilosModalContacto() {
    if (document.getElementById('modal-contacto-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'modal-contacto-styles';
    style.textContent = `
        #modalContacto {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.85);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            opacity: 0;
            transition: opacity 0.3s ease;
            padding: 20px;
        }
        
        #modalContacto.show {
            opacity: 1;
        }
        
        .modal-content-contacto {
            background: #1A2332;
            border-radius: 24px;
            max-width: 600px;
            width: 100%;
            max-height: 90vh;
            overflow-y: auto;
            animation: modalSlideUp 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        }
        
        @keyframes modalSlideUp {
            from {
                opacity: 0;
                transform: translateY(50px) scale(0.95);
            }
            to {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }
        
        .modal-header-contacto {
            text-align: center;
            padding: 2rem 2rem 1.5rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .modal-icon-header {
            margin-bottom: 1rem;
        }
        
        .icon-circle {
            display: inline-flex;
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, #FFCD11 0%, #FFE066 100%);
            border-radius: 50%;
            align-items: center;
            justify-content: center;
            font-size: 3rem;
            box-shadow: 0 10px 30px rgba(255, 205, 17, 0.3);
        }
        
        .modal-header-contacto h2 {
            margin: 0 0 0.5rem 0;
            color: white;
            font-size: 1.75rem;
        }
        
        .modal-subtitle {
            color: rgba(255, 255, 255, 0.7);
            margin: 0;
            font-size: 1rem;
        }
        
        .modal-body-contacto {
            padding: 2rem;
        }
        
        .opcion-card {
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .opcion-card:hover {
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(255, 205, 17, 0.3);
        }
        
        .opcion-card.active {
            background: rgba(255, 205, 17, 0.1);
            border-color: #FFCD11;
        }
        
        .opcion-header {
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        
        .opcion-icon {
            font-size: 2rem;
            flex-shrink: 0;
        }
        
        .opcion-titulo {
            flex: 1;
        }
        
        .opcion-titulo h3 {
            margin: 0 0 0.25rem 0;
            color: white;
            font-size: 1.125rem;
        }
        
        .opcion-titulo p {
            margin: 0;
            color: rgba(255, 255, 255, 0.6);
            font-size: 0.875rem;
        }
        
        .opcion-check {
            font-size: 1.5rem;
            color: rgba(255, 255, 255, 0.3);
            transition: all 0.3s ease;
        }
        
        .opcion-card.active .opcion-check {
            color: #FFCD11;
        }
        
        .opcion-content {
            margin-top: 1.5rem;
            animation: fadeIn 0.3s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .info-box-small {
            background: rgba(59, 130, 246, 0.1);
            border-left: 3px solid #3B82F6;
            border-radius: 8px;
            padding: 0.875rem;
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            margin-bottom: 1.5rem;
        }
        
        .info-box-small i {
            color: #3B82F6;
            font-size: 1.25rem;
            flex-shrink: 0;
        }
        
        .info-box-small p {
            margin: 0;
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.875rem;
            line-height: 1.5;
        }
        
        .form-group-modal {
            margin-bottom: 1.25rem;
        }
        
        .form-group-modal label {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            color: rgba(255, 255, 255, 0.9);
            font-weight: 600;
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
        }
        
        .form-group-modal input {
            width: 100%;
            padding: 0.875rem 1rem;
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            color: white;
            font-size: 1rem;
            transition: all 0.3s ease;
        }
        
        .form-group-modal input:focus {
            outline: none;
            background: rgba(255, 255, 255, 0.08);
            border-color: #FFCD11;
        }
        
        .form-group-modal input.error {
            border-color: #EF4444;
        }
        
        .error-message {
            color: #EF4444;
            font-size: 0.8rem;
            margin-top: 0.5rem;
            min-height: 1.2rem;
        }
        
        .uso-datos {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1.5rem;
        }
        
        .uso-datos h4 {
            margin: 0 0 0.875rem 0;
            color: #FFCD11;
            font-size: 0.95rem;
        }
        
        .uso-datos ul {
            list-style: none;
            padding: 0;
            margin: 0 0 1rem 0;
        }
        
        .uso-datos li {
            display: flex;
            align-items: center;
            gap: 0.625rem;
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.875rem;
            margin-bottom: 0.5rem;
        }
        
        .uso-datos li i {
            color: #10B981;
            font-size: 0.875rem;
        }
        
        .garantia-text {
            margin: 0;
            padding-top: 0.875rem;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            color: rgba(255, 255, 255, 0.7);
            font-size: 0.875rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .garantia-text i {
            color: #EF4444;
        }
        
        .garantia-text strong {
            color: white;
        }
        
        .btn-modal-primary,
        .btn-modal-secondary {
            width: 100%;
            padding: 1rem;
            border: none;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.625rem;
            transition: all 0.3s ease;
        }
        
        .btn-modal-primary {
            background: #FFCD11;
            color: #0f1419;
        }
        
        .btn-modal-primary:hover {
            background: #E6B800;
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(255, 205, 17, 0.3);
        }
        
        .btn-modal-secondary {
            background: rgba(255, 255, 255, 0.1);
            color: white;
            border: 2px solid rgba(255, 255, 255, 0.2);
        }
        
        .btn-modal-secondary:hover {
            background: rgba(255, 255, 255, 0.15);
            border-color: #FFCD11;
        }
        
        .app-benefits {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1.5rem;
        }
        
        .app-benefits h4 {
            margin: 0 0 1rem 0;
            color: #FFCD11;
            font-size: 0.95rem;
        }
        
        .app-benefits ul {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        
        .app-benefits li {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.875rem;
            margin-bottom: 0.75rem;
        }
        
        .app-benefits li i {
            color: #FFCD11;
            width: 20px;
        }
        
        .app-note {
            text-align: center;
            color: rgba(255, 255, 255, 0.6);
            font-size: 0.8rem;
            margin-top: 1rem;
        }
        
        .modal-footer-contacto {
            padding: 1.5rem 2rem;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            text-align: center;
        }
        
        .security-note {
            margin: 0;
            color: rgba(255, 255, 255, 0.6);
            font-size: 0.8rem;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
        }
        
        .security-note i {
            color: #10B981;
        }
        
        .security-note a {
            color: #FFCD11;
            text-decoration: none;
        }
        
        .security-note a:hover {
            text-decoration: underline;
        }
        
        @media (max-width: 640px) {
            .modal-content-contacto {
                border-radius: 16px;
            }
            
            .modal-header-contacto {
                padding: 1.5rem 1.5rem 1rem;
            }
            
            .icon-circle {
                width: 60px;
                height: 60px;
                font-size: 2rem;
            }
            
            .modal-header-contacto h2 {
                font-size: 1.5rem;
            }
            
            .modal-body-contacto {
                padding: 1.5rem;
            }
            
            .opcion-card {
                padding: 1.25rem;
            }
        }
    `;
    
    document.head.appendChild(style);
}




console.log('✅ JS cargado');