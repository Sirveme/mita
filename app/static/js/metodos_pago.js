/* ============================================
   MÉTODOS DE PAGO - MITA
   Integración con Culqi (tarjetas) y Tunki (Yape)
   ============================================ */

let metodoSeleccionado = null;
let solicitud = {};
let culqiPublicKey = null;
let culqiToken = null;

// Yape/Tunki
let yapeOrderId = null;
let yapePollingInterval = null;
let yapeTimerInterval = null;
let yapeExpirationTime = null;

// ============================================
// INICIALIZACIÓN
// ============================================
document.addEventListener('DOMContentLoaded', async function() {
    await inicializarCulqi();
    cargarDatosSolicitud();
});

// ============================================
// CULQI - INICIALIZACIÓN
// ============================================
async function inicializarCulqi() {
    try {
        const response = await fetch('/api/pagos/culqi/public-key');

        if (!response.ok) {
            console.warn('Culqi no disponible:', response.status);
            return;
        }

        const data = await response.json();
        culqiPublicKey = data.public_key;

        if (typeof Culqi !== 'undefined' && culqiPublicKey) {
            Culqi.publicKey = culqiPublicKey;
            Culqi.settings({
                title: 'MITA',
                currency: 'PEN',
                iins:false,
                style: {
                    logo: '/static/img/logo-serviplus.png',
                    bannerColor: '#1A2332',
                    buttonBackground: '#FFCD11',
                    buttonText: '#1A2332',
                    buttonTextColor: '#1A2332',
                    linksColor: '#FFCD11',
                    priceColor: '#FFCD11'
                }
            });

            console.log('Culqi inicializado:', data.environment);
        }
    } catch (error) {
        console.error('Error inicializando Culqi:', error);
    }
}

// ============================================
// CARGAR DATOS DE LA SOLICITUD
// ============================================
function cargarDatosSolicitud() {
    solicitud = JSON.parse(localStorage.getItem('solicitud_actual') || '{}');

    if (!solicitud.vehiculo) {
        solicitud = {
            vehiculo: { marca: 'Toyota', modelo: 'Corolla', anio: '2024', placa: 'AIG-0638' },
            servicio: { tipo_aceite: 'sintetico', precio_aceite: 280, incluir_filtro: true },
            ubicacion: { distrito: 'San Miguel', direccion: 'Av. Ejemplo 123' }
        };
        localStorage.setItem('solicitud_actual', JSON.stringify(solicitud));
    }

    actualizarResumen();
}

function actualizarResumen() {
    const ids = {
        servicio: ['resumenServicio', 'resumenServicioPago'],
        vehiculo: ['resumenVehiculo', 'resumenVehiculoPago'],
        placa: ['resumenPlaca', 'resumenPlacaPago'],
        ubicacion: ['resumenUbicacion', 'resumenUbicacionPago', 'resumenDireccion', 'resumenDireccionPago'],
        distrito: ['resumenDistrito', 'resumenDistritoPago'],
        referencia: ['resumenReferencia', 'resumenReferenciaPago']
    };

    const valores = {
        servicio: 'Cambio de aceite',
        vehiculo: `${solicitud.vehiculo?.marca || ''} ${solicitud.vehiculo?.modelo || ''} ${solicitud.vehiculo?.anio || ''}`.trim(),
        placa: solicitud.vehiculo?.placa || '-',
        ubicacion: `${solicitud.ubicacion?.direccion || ''}, ${solicitud.ubicacion?.distrito || ''}`.trim(),
        distrito: solicitud.ubicacion?.distrito || '-',
        referencia: solicitud.ubicacion?.referencia || '-'
    };

    Object.keys(ids).forEach(key => {
        ids[key].forEach(id => {
            const elem = document.getElementById(id);
            if (elem) elem.textContent = valores[key];
        });
    });

    const total = calcularTotal();
    ['totalPagar', 'totalPago', 'montoTotal', 'montoPagarTarjeta', 'montoEnviar', 'montoYape'].forEach(id => {
        const elem = document.getElementById(id);
        if (elem) elem.textContent = total.toFixed(2);
    });
}

function calcularTotal() {
    let total = 50;

    if (solicitud.servicio?.precio_aceite) {
        total += solicitud.servicio.precio_aceite;
    }

    if (solicitud.servicio?.incluir_filtro) {
        total += 30;
    }

    return total;
}

// ============================================
// SELECCIÓN DE MÉTODO DE PAGO
// ============================================
function seleccionarMetodo(metodo) {
    // Limpiar intervalos de Yape si estaban activos
    limpiarYapeIntervalos();

    // Remover selección anterior
    document.querySelectorAll('.metodo-card, .metodo-pago, .payment-method').forEach(card => {
        card.classList.remove('selected', 'seleccionado', 'active');
        card.style.border = '';
    });

    // Seleccionar nuevo
    const card = document.querySelector(`[data-metodo="${metodo}"]`) ||
                 document.querySelector(`[onclick*="${metodo}"]`);

    if (card) {
        card.classList.add('selected', 'seleccionado', 'active');
        card.style.border = '2px solid #FFCD11';
    }

    metodoSeleccionado = metodo;

    // Ocultar todos los formularios
    ['formularioTarjeta', 'formularioYape', 'formularioYapePlin'].forEach(id => {
        const form = document.getElementById(id);
        if (form) form.style.display = 'none';
    });

    // Mostrar formulario correspondiente
    if (metodo === 'tarjeta') {
        const form = document.getElementById('formularioTarjeta');
        if (form) {
            form.style.display = 'block';
            setTimeout(() => {
                form.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
        }
    } else if (metodo === 'yape') {
        // Mostrar formulario de Yape con QR
        const form = document.getElementById('formularioYape');
        if (form) {
            form.style.display = 'block';
            // Resetear vista a estado inicial
            resetearVistaYape();
            setTimeout(() => {
                form.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
        }
    } else if (metodo === 'plin') {
        // Plin usa el formulario manual
        const form = document.getElementById('formularioYapePlin');
        if (form) {
            form.style.display = 'block';
            const appNombre = document.getElementById('appNombre');
            if (appNombre) appNombre.textContent = 'Plin';
            setTimeout(() => {
                form.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
        }
    }
}

// ============================================
// YAPE - GENERAR QR
// ============================================
async function generarQRYape() {
    mostrarModal('modalCargando');

    try {
        const servicioId = solicitud.servicio_id || 1;

        const response = await fetch('/api/pagos/yape/crear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${obtenerToken()}`
            },
            body: JSON.stringify({
                servicio_id: servicioId,
                monto: calcularTotal()
            })
        });

        const data = await response.json();
        ocultarModal('modalCargando');

        if (data.success) {
            yapeOrderId = data.order_id;
            mostrarQRYape(data);
            iniciarPollingYape();
            iniciarTimerYape(data.expira_en_minutos || 15);
        } else {
            mostrarError(data.user_message || 'Error generando código QR. Intenta de nuevo.');
        }

    } catch (error) {
        ocultarModal('modalCargando');
        console.error('Error:', error);
        mostrarError('Error de conexión. Verifica tu conexión a internet.');
    }
}

function mostrarQRYape(data) {
    // Ocultar botón de generar, mostrar QR
    const generarSection = document.getElementById('yapeGenerarQR');
    const qrSection = document.getElementById('yapeQRContainer');

    if (generarSection) generarSection.style.display = 'none';
    if (qrSection) qrSection.style.display = 'block';

    // Mostrar imagen QR
    const qrImage = document.getElementById('yapeQRImage');
    if (qrImage) {
        if (data.qr_code) {
            // Si viene en base64
            qrImage.src = data.qr_code.startsWith('data:') ? data.qr_code : `data:image/png;base64,${data.qr_code}`;
        } else if (data.qr_url) {
            qrImage.src = data.qr_url;
        }
    }

    // Mostrar deep link si está disponible (para móviles)
    if (data.deep_link) {
        const deepLinkContainer = document.getElementById('yapeDeepLinkContainer');
        const deepLink = document.getElementById('yapeDeepLink');

        if (deepLinkContainer) deepLinkContainer.style.display = 'block';
        if (deepLink) deepLink.href = data.deep_link;
    }
}

function resetearVistaYape() {
    const generarSection = document.getElementById('yapeGenerarQR');
    const qrSection = document.getElementById('yapeQRContainer');
    const deepLinkContainer = document.getElementById('yapeDeepLinkContainer');

    if (generarSection) generarSection.style.display = 'block';
    if (qrSection) qrSection.style.display = 'none';
    if (deepLinkContainer) deepLinkContainer.style.display = 'none';

    yapeOrderId = null;
    limpiarYapeIntervalos();
}

// ============================================
// YAPE - POLLING PARA VERIFICAR ESTADO
// ============================================
function iniciarPollingYape() {
    // Verificar cada 3 segundos
    yapePollingInterval = setInterval(async () => {
        if (!yapeOrderId) {
            limpiarYapeIntervalos();
            return;
        }

        try {
            const response = await fetch(`/api/pagos/yape/estado/${yapeOrderId}`, {
                headers: {
                    'Authorization': `Bearer ${obtenerToken()}`
                }
            });

            const data = await response.json();

            if (data.pagado) {
                // Pago completado
                limpiarYapeIntervalos();
                onYapePagoExitoso(data);
            } else if (data.estado === 'expired' || data.estado === 'cancelado') {
                // QR expirado o cancelado
                limpiarYapeIntervalos();
                mostrarError('El código QR ha expirado. Genera uno nuevo.');
                resetearVistaYape();
            }

        } catch (error) {
            console.error('Error verificando estado:', error);
        }

    }, 3000);
}

function iniciarTimerYape(minutos) {
    yapeExpirationTime = Date.now() + (minutos * 60 * 1000);

    yapeTimerInterval = setInterval(() => {
        const ahora = Date.now();
        const restante = yapeExpirationTime - ahora;

        if (restante <= 0) {
            limpiarYapeIntervalos();
            document.getElementById('yapeTimer').textContent = '00:00';
            mostrarError('El código QR ha expirado. Genera uno nuevo.');
            resetearVistaYape();
            return;
        }

        const minutosRestantes = Math.floor(restante / 60000);
        const segundosRestantes = Math.floor((restante % 60000) / 1000);

        const timerElement = document.getElementById('yapeTimer');
        if (timerElement) {
            timerElement.textContent = `${String(minutosRestantes).padStart(2, '0')}:${String(segundosRestantes).padStart(2, '0')}`;
        }

    }, 1000);
}

function limpiarYapeIntervalos() {
    if (yapePollingInterval) {
        clearInterval(yapePollingInterval);
        yapePollingInterval = null;
    }

    if (yapeTimerInterval) {
        clearInterval(yapeTimerInterval);
        yapeTimerInterval = null;
    }
}

function onYapePagoExitoso(data) {
    // Guardar información del pago
    solicitud.pago = {
        metodo: 'yape',
        monto: data.monto,
        estado: 'pagado',
        order_id: data.order_id,
        transaction_id: data.transaction_id,
        fecha: new Date().toISOString()
    };

    solicitud.estado = 'pagado';
    localStorage.setItem('solicitud_actual', JSON.stringify(solicitud));

    // Mostrar éxito
    const mensajeExito = document.getElementById('mensajeExito');
    if (mensajeExito) {
        mensajeExito.textContent = '¡Tu pago con Yape fue confirmado! Ahora buscaremos un mecánico disponible.';
    }
    mostrarModal('modalExito');

    // Redirigir después de 2 segundos
    setTimeout(() => {
        irABuscarMecanico();
    }, 2000);
}

async function cancelarPagoYape() {
    if (yapeOrderId) {
        try {
            await fetch(`/api/pagos/yape/cancelar/${yapeOrderId}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${obtenerToken()}`
                }
            });
        } catch (error) {
            console.error('Error cancelando:', error);
        }
    }

    limpiarYapeIntervalos();
    resetearVistaYape();

    // Ocultar formulario de Yape
    const form = document.getElementById('formularioYape');
    if (form) form.style.display = 'none';

    // Deseleccionar método
    metodoSeleccionado = null;
    document.querySelectorAll('.metodo-card').forEach(card => {
        card.classList.remove('selected', 'seleccionado', 'active');
        card.style.border = '';
    });
}

// ============================================
// CULQI - PROCESAR PAGO CON TARJETA
// ============================================
function procesarPagoTarjeta() {
    if (!culqiPublicKey) {
        alert('Culqi no está disponible. Intenta con otro método de pago.');
        return;
    }

    const total = calcularTotal();
    
    // Configurar monto en Culqi (en centavos)
    Culqi.settings({
        title: 'MITA - Cambio de Aceite',
        currency: 'PEN',
        amount: Math.round(total * 100), // Culqi usa centavos
        description: `Servicio para ${solicitud.vehiculo?.placa || 'vehículo'}`,
        iins:false,
        style: {
            logo: '/static/img/logo-serviplus.png',
            bannerColor: '#1A2332',
            buttonBackground: '#FFCD11',
            buttonText: '#1A2332',
            linksColor: '#FFCD11',
            priceColor: '#FFCD11'
        }
    });

    // Abrir modal de Culqi
    Culqi.open();
}

// ============================================
// CALLBACK DE CULQI (cuando genera token)
// ============================================
function culqi() {
    if (Culqi.token) {
        // Token generado exitosamente
        const token = Culqi.token.id;
        console.log('Token Culqi generado:', token);
        
        enviarPagoAlBackend(token);
        
    } else if (Culqi.error) {
        // Error en Culqi
        console.error('Error Culqi:', Culqi.error);
        alert(`Error: ${Culqi.error.user_message}`);
    }
}

// ============================================
// ENVIAR PAGO AL BACKEND
// ============================================
async function enviarPagoAlBackend(tokenId) {
    mostrarModal('modalCargando');
    
    try {
        const response = await fetch('/api/pagos/tarjeta', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                token_id: tokenId,
                servicio_id: 1, // Por ahora fijo, luego será dinámico
                monto: calcularTotal(),
                email: solicitud.email || 'demo@serviplus.com'
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            // Pago exitoso
            console.log('Pago exitoso:', data);
            
            // Guardar en localStorage
            solicitud.pago = {
                metodo: 'culqi',
                pago_id: data.pago_id,
                culqi_charge_id: data.culqi_charge_id,
                monto: data.monto,
                estado: data.estado,
                fecha: new Date().toISOString()
            };
            localStorage.setItem('solicitud_actual', JSON.stringify(solicitud));
            
            ocultarModal('modalCargando');
            mostrarModal('modalExito');
            
            // Redirigir después de 2 segundos
            setTimeout(() => {
                irABuscarMecanico();
            }, 2000);
            
        } else {
            // Error en el pago
            throw new Error(data.message || 'Error procesando el pago');
        }
        
    } catch (error) {
        console.error('Error:', error);
        ocultarModal('modalCargando');
        alert('Error procesando el pago: ' + error.message);
    }
}

// ============================================
// PLIN - COMPROBANTE MANUAL
// ============================================
let comprobanteSeleccionado = null;

function handleFileSelect(event) {
    const file = event.target.files[0];

    if (!file) return;

    if (!file.type.startsWith('image/')) {
        mostrarError('Por favor selecciona una imagen válida (JPG, PNG)');
        return;
    }

    if (file.size > 5 * 1024 * 1024) {
        mostrarError('La imagen es muy grande. Máximo 5MB.');
        return;
    }

    comprobanteSeleccionado = file;

    const reader = new FileReader();
    reader.onload = function(e) {
        const preview = document.getElementById('imagePreview');
        const previewContainer = document.getElementById('previewContainer');
        const uploadArea = document.getElementById('uploadArea');

        if (preview) preview.src = e.target.result;
        if (previewContainer) previewContainer.style.display = 'block';
        if (uploadArea) uploadArea.style.display = 'none';

        const btnEnviar = document.getElementById('btnEnviarComprobante');
        if (btnEnviar) btnEnviar.disabled = false;
    };
    reader.readAsDataURL(file);
}

function removerImagen() {
    comprobanteSeleccionado = null;

    const preview = document.getElementById('imagePreview');
    const previewContainer = document.getElementById('previewContainer');
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const btnEnviar = document.getElementById('btnEnviarComprobante');

    if (preview) preview.src = '';
    if (previewContainer) previewContainer.style.display = 'none';
    if (uploadArea) uploadArea.style.display = 'flex';
    if (fileInput) fileInput.value = '';
    if (btnEnviar) btnEnviar.disabled = true;
}

async function enviarComprobante() {
    if (!comprobanteSeleccionado) {
        mostrarError('Por favor sube el comprobante de pago');
        return;
    }

    mostrarModal('modalCargando');

    setTimeout(() => {
        ocultarModal('modalCargando');

        solicitud.pago = {
            metodo: metodoSeleccionado,
            monto: calcularTotal(),
            estado: 'pendiente_confirmacion',
            fecha: new Date().toISOString()
        };

        solicitud.estado = 'pendiente_pago';
        localStorage.setItem('solicitud_actual', JSON.stringify(solicitud));

        const codigoFinal = document.getElementById('codigoServicioFinal');
        if (codigoFinal) {
            codigoFinal.textContent = `SERV-${Date.now().toString().slice(-8)}`;
        }

        mostrarModal('modalPendiente');

    }, 2000);
}

// ============================================
// UTILIDADES
// ============================================
function obtenerEmailUsuario() {
    const usuario = JSON.parse(localStorage.getItem('usuario') || '{}');
    return usuario.email || solicitud.email || null;
}

function obtenerToken() {
    return localStorage.getItem('access_token') || '';
}

function traducirErrorCulqi(error) {
    const mensajes = {
        'invalid_card_number': 'Número de tarjeta inválido',
        'invalid_cvv': 'Código de seguridad (CVV) inválido',
        'invalid_expiration_month': 'Mes de expiración inválido',
        'invalid_expiration_year': 'Año de expiración inválido',
        'expired_card': 'La tarjeta ha expirado',
        'insufficient_funds': 'Fondos insuficientes',
        'stolen_card': 'Tarjeta reportada como robada',
        'lost_card': 'Tarjeta reportada como perdida',
        'card_declined': 'Tarjeta rechazada por el banco',
        'processing_error': 'Error procesando el pago',
        'fraudulent': 'Transacción rechazada por seguridad'
    };

    if (error && error.user_message) {
        return error.user_message;
    }

    if (error && error.type && mensajes[error.type]) {
        return mensajes[error.type];
    }

    return 'Error procesando el pago. Intenta de nuevo.';
}

function mostrarError(mensaje) {
    let toast = document.getElementById('toastError');

    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toastError';
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #dc2626;
            color: white;
            padding: 1rem 2rem;
            border-radius: 10px;
            z-index: 999999;
            max-width: 90%;
            text-align: center;
            box-shadow: 0 4px 20px rgba(220, 38, 38, 0.4);
            animation: slideUp 0.3s ease;
        `;
        document.body.appendChild(toast);

        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideUp {
                from { opacity: 0; transform: translateX(-50%) translateY(20px); }
                to { opacity: 1; transform: translateX(-50%) translateY(0); }
            }
        `;
        document.head.appendChild(style);
    }

    toast.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${mensaje}`;
    toast.style.display = 'block';

    setTimeout(() => {
        toast.style.display = 'none';
    }, 5000);
}

function copiarNumero() {
    const numero = document.getElementById('numeroDestino')?.textContent || '';
    navigator.clipboard.writeText(numero.replace(/\s/g, ''));
    mostrarMensaje('Número copiado');
}

function copiarCodigo() {
    const codigo = document.getElementById('codigoOperacion')?.textContent || '';
    navigator.clipboard.writeText(codigo);
    mostrarMensaje('Código copiado');
}

function mostrarMensaje(texto) {
    let toast = document.getElementById('toastMensaje');

    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toastMensaje';
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #10b981;
            color: white;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            z-index: 999999;
        `;
        document.body.appendChild(toast);
    }

    toast.textContent = texto;
    toast.style.display = 'block';

    setTimeout(() => {
        toast.style.display = 'none';
    }, 2000);
}

// ============================================
// NAVEGACIÓN
// ============================================
function irABuscarMecanico() {
    limpiarYapeIntervalos();
    solicitud.estado = 'buscando_mecanico';
    localStorage.setItem('solicitud_actual', JSON.stringify(solicitud));
    window.location.href = '/cliente/buscando-mecanico';
}

function volverAlInicio() {
    limpiarYapeIntervalos();
    window.location.href = '/cliente/home';
}

function verMisSolicitudes() {
    limpiarYapeIntervalos();
    window.location.href = '/cliente/mis-servicios';
}

// ============================================
// MODALES
// ============================================
function mostrarModal(modalId) {
    let modal = document.getElementById(modalId);

    if (!modal) {
        modal = document.createElement('div');
        modal.id = modalId;
        modal.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.9);display:flex;align-items:center;justify-content:center;z-index:999999';

        if (modalId === 'modalCargando') {
            modal.innerHTML = `
                <div style="background:#1a2332;border-radius:20px;padding:3rem;text-align:center;border:3px solid #FFCD11;min-width:300px">
                    <div style="width:70px;height:70px;border:5px solid rgba(255,205,17,0.3);border-top-color:#FFCD11;border-radius:50%;animation:spin 1s linear infinite;margin:0 auto 1.5rem"></div>
                    <h2 style="color:#FFCD11;margin:0 0 0.5rem 0">Procesando...</h2>
                    <p style="color:#9ca3af;margin:0">Por favor espera</p>
                </div>
                <style>@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}</style>
            `;
        } else if (modalId === 'modalExito') {
            modal.innerHTML = `
                <div style="background:#1a2332;border-radius:20px;padding:3rem;text-align:center;border:3px solid #10b981;min-width:300px">
                    <div style="width:90px;height:90px;background:#10b981;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 1.5rem">
                        <svg width="60" height="60" viewBox="0 0 24 24" fill="none">
                            <path d="M20 6L9 17L4 12" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </div>
                    <h2 style="color:#10b981;margin:0 0 0.5rem 0">¡Pago exitoso!</h2>
                    <p id="mensajeExito" style="color:#9ca3af;margin:0">Redirigiendo...</p>
                </div>
            `;
        }

        document.body.appendChild(modal);
    }

    modal.style.display = 'flex';
}

function ocultarModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
}

// ============================================
// EXPORTS GLOBALES
// ============================================
window.seleccionarMetodo = seleccionarMetodo;
window.procesarPagoTarjeta = procesarPagoTarjeta;
window.generarQRYape = generarQRYape;
window.cancelarPagoYape = cancelarPagoYape;
window.enviarComprobante = enviarComprobante;
window.irABuscarMecanico = irABuscarMecanico;
window.volverAlInicio = volverAlInicio;
window.verMisSolicitudes = verMisSolicitudes;
window.handleFileSelect = handleFileSelect;
window.removerImagen = removerImagen;
window.copiarNumero = copiarNumero;
window.copiarCodigo = copiarCodigo;
window.culqi = culqi;
