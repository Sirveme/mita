// ============================================
// MITA - DEMO COMPLETO (SIN BACKEND)
// Ubicación: app/static/js/demo.js
// ============================================

// ============================================
// AUTO-INICIALIZACIÓN DEMO
// ============================================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🎬 INICIANDO DEMO MITA...\n');
    
    // Esperar a que carguen todos los scripts
    await waitForScripts();
    
    // Auto-login si no hay sesión
    if (!authMock.isAuthenticated()) {
        console.log('📝 No hay sesión, iniciando como CLIENTE...');
        authMock.autoLogin('cliente');
    }
    
    // Conectar WebSocket Mock
    const userId = authMock.getUserId();
    const userRole = authMock.getUserRole();
    
    if (userId && userRole) {
        // Usar WebSocket Mock en lugar del real
        window.wsManager = new WebSocketManager();
        await window.wsManager.connect(userId, userRole);
        
        // Configurar event listeners
        setupWebSocketEvents();
    }
    
    // Mostrar info de demo
    mostrarInfoDemo();
});

// ============================================
// ESPERAR SCRIPTS
// ============================================

function waitForScripts() {
    return new Promise((resolve) => {
        const checkInterval = setInterval(() => {
            if (window.authMock && window.notificationUI && window.WebSocketMock && window.chatWidget) {
                clearInterval(checkInterval);
                resolve();
            }
        }, 100);
        
        // Timeout después de 5 segundos
        setTimeout(() => {
            clearInterval(checkInterval);
            resolve();
        }, 5000);
    });
}

// ============================================
// SETUP WEBSOCKET EVENTS
// ============================================

function setupWebSocketEvents() {
    const ws = window.wsManager;
    
    // Chat message → Abrir widget y mostrar mensaje
    ws.on('chat_message', (data) => {
        // Configurar contacto si no está configurado
        if (!window.chatWidget.currentChat) {
            window.chatWidget.setContact({
                userId: data.emisor_id,
                nombre: data.emisor_nombre,
                foto: data.emisor_foto || null,
                estado: 'En línea',
                servicioId: data.servicio_id
            });
        }
        
        // Agregar mensaje al widget
        window.chatWidget.receiveMessage(data);
        
        // Mostrar toast SOLO si el chat está cerrado
        if (!window.chatWidget.isOpen) {
            notificationUI.showChatMessage(
                data.emisor_nombre,
                data.mensaje,
                data.emisor_foto
            );
        }
    });
    
    // Técnico asignado → Configurar chat automáticamente
    ws.on('tecnico_asignado', (data) => {
        notificationUI.showTecnicoAsignado(data.tecnico);
        
        // Configurar chat con el técnico
        window.chatWidget.setContact({
            userId: data.tecnico.id,
            nombre: data.tecnico.nombre,
            foto: data.tecnico.foto,
            estado: 'En línea',
            servicioId: data.servicio_id
        });
    });
    
    // Estado servicio actualizado
    ws.on('estado_servicio_actualizado', (data) => {
        notificationUI.showServiceUpdate(
            data.servicio_id,
            data.estado_nuevo,
            data.mensaje
        );
    });
    
    // Indicador de escritura
    ws.on('typing', (data) => {
        if (data.escribiendo) {
            window.chatWidget.showTypingIndicator();
        } else {
            window.chatWidget.hideTypingIndicator();
        }
    });
    
    // Nuevo servicio (para técnicos)
    ws.on('nuevo_servicio', (data) => {
        if (authMock.getUserRole() === 'tecnico') {
            const mensaje = `
                <div style="line-height: 1.6;">
                    <strong>Nuevo servicio disponible</strong><br>
                    📍 ${data.cliente.direccion}<br>
                    🚗 ${data.vehiculo.marca} ${data.vehiculo.modelo}<br>
                    💰 S/.${data.monto}<br>
                    📏 ${data.distancia} km - ${data.tiempo_estimado} min
                </div>
            `;
            
            showToast(mensaje, 'info', {
                duration: 15000,
                action: {
                    label: 'Aceptar servicio',
                    callback: () => {
                        ws.acceptService(data.servicio_id);
                        showToast('Servicio aceptado correctamente', 'success');
                        
                        // Configurar chat con el cliente
                        window.chatWidget.setContact({
                            userId: data.cliente.id,
                            nombre: data.cliente.nombre,
                            foto: null,
                            estado: 'En línea',
                            servicioId: data.servicio_id
                        });
                    }
                }
            });
        }
    });
    
    console.log('✅ Event listeners configurados (incluyendo Chat Widget)');
}

// ============================================
// MOSTRAR INFO DEMO
// ============================================

function mostrarInfoDemo() {
    const usuario = authMock.getCurrentUser();
    
    console.log('\n' + '='.repeat(70));
    console.log('🎭 MODO DEMO ACTIVO - DATOS FICTICIOS');
    console.log('='.repeat(70));
    console.log(`👤 Usuario actual: ${usuario?.nombre_completo}`);
    console.log(`📧 Email: ${usuario?.email}`);
    console.log(`🎯 Rol: ${usuario?.rol}`);
    console.log(`🔌 WebSocket: ${window.wsManager?.isConnected ? 'Conectado (Mock)' : 'Desconectado'}`);
    console.log('='.repeat(70));
    console.log('\n💡 COMANDOS DISPONIBLES:\n');
    console.log('   🔐 AUTENTICACIÓN:');
    console.log('   authMock.quickLogin("cliente")   - Login como cliente');
    console.log('   authMock.quickLogin("tecnico")   - Login como técnico');
    console.log('   authMock.quickLogin("admin")     - Login como admin');
    console.log('   authMock.logout()                - Cerrar sesión');
    console.log('   authMock.listarUsuarios()        - Ver todos los usuarios');
    console.log('\n   💬 CHAT:');
    console.log('   demoChat()                       - Demostrar chat widget');
    console.log('   demoChatCompleto()               - Conversación completa');
    console.log('   chatWidget.open()                - Abrir chat');
    console.log('\n   🔔 NOTIFICACIONES:');
    console.log('   demoNotificaciones()             - Mostrar todas las notificaciones');
    console.log('   showToast("Mensaje", "success")  - Toast simple');
    console.log('\n   🔧 SERVICIOS:');
    console.log('   demoServicioCompleto()           - Flujo completo de servicio');
    console.log('\n   📊 INFO:');
    console.log('   wsManager.getStats()             - Estadísticas WebSocket');
    console.log('   authMock.getCurrentUser()        - Usuario actual');
    console.log('   verEstadoSistema()               - Estado completo');
    console.log('='.repeat(70) + '\n');
}

// ============================================
// DEMOS PREDEFINIDOS
// ============================================

window.demoChat = function() {
    console.log('💬 Demo: Chat widget...');
    
    if (!window.chatWidget) {
        console.error('❌ Chat widget no disponible');
        return;
    }
    
    // Configurar contacto
    chatWidget.setContact({
        userId: 3,
        nombre: 'Carlos Rodríguez',
        foto: null,
        estado: 'En línea',
        servicioId: 123
    });
    
    // Abrir chat
    setTimeout(() => {
        chatWidget.open();
    }, 500);
    
    // Cliente envía mensaje
    setTimeout(() => {
        chatWidget.addMessage({
            id: Date.now(),
            texto: '¿Ya saliste del taller?',
            emisor: 'yo',
            timestamp: new Date().toISOString()
        });
    }, 1500);
    
    // Mostrar "escribiendo..."
    setTimeout(() => {
        chatWidget.showTypingIndicator();
    }, 3000);
    
    // Técnico responde
    setTimeout(() => {
        chatWidget.hideTypingIndicator();
        chatWidget.receiveMessage({
            mensaje_id: Date.now(),
            emisor_nombre: 'Carlos Rodríguez',
            mensaje: 'Sí, estoy en camino. Llegaré en 10 minutos 🚗',
            timestamp: new Date().toISOString()
        });
    }, 5000);
    
    // Cliente responde
    setTimeout(() => {
        chatWidget.addMessage({
            id: Date.now(),
            texto: 'Perfecto, te espero 👍',
            emisor: 'yo',
            timestamp: new Date().toISOString()
        });
    }, 7000);
    
    console.log('✅ Demo de chat widget iniciado');
};

window.demoChatCompleto = function() {
    console.log('💬 Demo: Conversación completa...');
    
    if (!window.chatWidget) {
        console.error('❌ Chat widget no disponible');
        return;
    }
    
    // Configurar
    chatWidget.setContact({
        userId: 3,
        nombre: 'Carlos Rodríguez',
        foto: null,
        estado: 'En línea',
        servicioId: 123
    });
    
    chatWidget.open();
    
    const conversacion = [
        { tiempo: 1000, emisor: 'yo', texto: 'Hola, ¿ya vienes?' },
        { tiempo: 3000, typing: true },
        { tiempo: 5000, emisor: 'tecnico', texto: 'Sí, salgo en 5 minutos' },
        { tiempo: 7000, emisor: 'yo', texto: 'Ok, ¿cuánto demorarás?' },
        { tiempo: 9000, typing: true },
        { tiempo: 11000, emisor: 'tecnico', texto: 'Aproximadamente 20 minutos' },
        { tiempo: 13000, emisor: 'yo', texto: 'Perfecto, gracias' },
        { tiempo: 15000, emisor: 'tecnico', texto: '👍' }
    ];
    
    conversacion.forEach(msg => {
        setTimeout(() => {
            if (msg.typing) {
                chatWidget.showTypingIndicator();
            } else if (msg.emisor === 'yo') {
                chatWidget.addMessage({
                    id: Date.now(),
                    texto: msg.texto,
                    emisor: 'yo',
                    timestamp: new Date().toISOString()
                });
            } else {
                chatWidget.hideTypingIndicator();
                chatWidget.receiveMessage({
                    mensaje_id: Date.now(),
                    emisor_nombre: 'Carlos Rodríguez',
                    mensaje: msg.texto,
                    timestamp: new Date().toISOString()
                });
            }
        }, msg.tiempo);
    });
    
    console.log('✅ Demo de conversación completa iniciado (16 segundos)');
};

window.demoNotificaciones = function() {
    console.log('🔔 Demo: Todas las notificaciones...');
    
    const demos = [
        () => showToast('Operación exitosa', 'success'),
        () => showToast('Nuevo mensaje recibido', 'info'),
        () => showToast('Revisa la información', 'warning'),
        () => showToast('Error al procesar', 'error'),
        () => notificationUI.showChatMessage('Carlos', 'Hola, ¿cómo estás?'),
        () => notificationUI.showTecnicoAsignado({
            nombre: 'Carlos Rodríguez',
            calificacion: 4.8,
            foto: null
        }),
        () => notificationUI.showServiceUpdate(123, 'en_camino', 'El técnico está en camino'),
        () => {
            const id = notificationUI.showLoading('Procesando pago...');
            setTimeout(() => {
                notificationUI.hide(id);
                showToast('Pago procesado exitosamente', 'success');
            }, 3000);
        }
    ];
    
    demos.forEach((demo, index) => {
        setTimeout(demo, index * 2000);
    });
    
    console.log('✅ Demo de notificaciones iniciado');
};

window.demoServicioCompleto = function() {
    console.log('🔧 Demo: Flujo completo de servicio...');
    
    const estados = [
        { tiempo: 0, estado: null, mensaje: 'Solicitud de servicio creada' },
        { tiempo: 2000, estado: 'asignado', mensaje: 'Técnico asignado a tu servicio' },
        { tiempo: 5000, estado: 'en_camino', mensaje: 'El técnico está en camino' },
        { tiempo: 8000, estado: 'llegado', mensaje: 'El técnico ha llegado' },
        { tiempo: 11000, estado: 'en_proceso', mensaje: 'Servicio en progreso' },
        { tiempo: 14000, estado: 'completado', mensaje: '¡Servicio completado exitosamente!' }
    ];
    
    estados.forEach(({ tiempo, estado, mensaje }) => {
        setTimeout(() => {
            if (estado === 'asignado') {
                notificationUI.showTecnicoAsignado({
                    nombre: 'Carlos Rodríguez',
                    calificacion: 4.8,
                    foto: null
                });
            } else if (estado) {
                notificationUI.showServiceUpdate(123, estado, mensaje);
            } else {
                showToast(mensaje, 'info');
            }
        }, tiempo);
    });
    
    console.log('✅ Demo de servicio completo iniciado (17 segundos)');
};

window.demoCambiarUsuario = function(tipo = 'tecnico') {
    console.log(`🔄 Cambiando a ${tipo}...`);
    authMock.logout();
    authMock.autoLogin(tipo);
    location.reload();
};

// ============================================
// HELPERS GLOBALES
// ============================================

window.verEstadoSistema = function() {
    const usuario = authMock.getCurrentUser();
    const wsStats = wsManager?.getStats();
    
    console.log('\n📊 ESTADO DEL SISTEMA:');
    console.log('='.repeat(50));
    console.log('Usuario:', usuario?.nombre_completo, `(${usuario?.rol})`);
    console.log('WebSocket:', wsStats?.connected ? '✅ Conectado' : '❌ Desconectado');
    console.log('Notificaciones:', notificationUI ? '✅ Activo' : '❌ Inactivo');
    console.log('Chat Widget:', chatWidget ? '✅ Activo' : '❌ Inactivo');
    console.log('='.repeat(50) + '\n');
};

// ============================================
// AUTO-MOSTRAR DEMO AL INICIAR
// ============================================

setTimeout(() => {
    if (window.location.search.includes('demo=auto')) {
        console.log('🎬 Auto-demo activado...');
        demoServicioCompleto();
    }
}, 2000);

console.log('[Demo] Script de demo cargado ✅');



// ============================================
// AUTO-CONFIGURAR CHAT AL CARGAR
// Agregar a base_pwa.html o demo.js
// ============================================

// Configurar chat automáticamente después de conectar WS
document.addEventListener('DOMContentLoaded', () => {
    // Esperar a que todo esté listo
    setTimeout(() => {
        if (window.chatWidget && window.wsManager && window.authMock) {
            const userRole = authMock.getUserRole();
            
            // Si es cliente, configurar chat con técnico por defecto
            if (userRole === 'cliente') {
                chatWidget.setContact({
                    userId: 3,
                    nombre: 'Carlos Rodríguez',
                    foto: null,
                    estado: 'En línea',
                    servicioId: 123
                });
                
                console.log('[Chat] ✅ Chat configurado automáticamente con técnico');
            }
            // Si es técnico, configurar chat con cliente por defecto
            else if (userRole === 'tecnico') {
                chatWidget.setContact({
                    userId: 1,
                    nombre: 'Juan Pérez García',
                    foto: null,
                    estado: 'En línea',
                    servicioId: 123
                });
                
                console.log('[Chat] ✅ Chat configurado automáticamente con cliente');
            }
        }
    }, 2000);
});