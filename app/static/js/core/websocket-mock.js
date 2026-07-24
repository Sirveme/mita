// ============================================
// MITA - WEBSOCKET MOCK (SIN BACKEND)
// Ubicación: app/static/js/core/websocket-mock.js
// ============================================

class WebSocketMock {
    constructor() {
        this.isConnected = false;
        this.userId = null;
        this.userRole = null;
        this.handlers = {};
        this.messageQueue = [];
        this.simulatedUsers = new Map();
        
        console.log('[WS Mock] WebSocket Mock inicializado');
    }

    // ============================================
    // CONEXIÓN (SIMULADA)
    // ============================================
    
    async connect(userId, userRole) {
        return new Promise((resolve) => {
            this.userId = userId;
            this.userRole = userRole;
            
            console.log(`[WS Mock] 🔌 Conectando como ${userRole} (ID: ${userId})...`);
            
            setTimeout(() => {
                this.isConnected = true;
                console.log('[WS Mock] ✅ Conexión establecida (SIMULADA)');
                
                // Trigger connected event
                this.trigger('connected', {
                    userId: this.userId,
                    userRole: this.userRole
                });
                
                // Simular mensajes iniciales
                this.simulateInitialMessages();
                
                resolve(true);
            }, 500);
        });
    }

    disconnect() {
        this.isConnected = false;
        this.trigger('disconnected');
        console.log('[WS Mock] 🔌 Desconectado');
    }

    // ============================================
    // ENVIAR MENSAJES (SIMULADOS)
    // ============================================
    
    send(message) {
        if (!this.isConnected) {
            console.warn('[WS Mock] No conectado, encolando mensaje');
            this.messageQueue.push(message);
            return false;
        }

        console.log(`[WS Mock] 📤 Enviando: ${message.tipo}`);
        
        // Simular respuesta del servidor
        this.simulateServerResponse(message);
        
        return true;
    }

    // ============================================
    // MÉTODOS ESPECÍFICOS
    // ============================================
    
    sendChatMessage(destinatarioId, mensaje, servicioId = null) {
        const msg = {
            tipo: 'chat',
            destinatario_id: destinatarioId,
            mensaje: mensaje,
            servicio_id: servicioId,
            timestamp: new Date().toISOString()
        };
        
        this.send(msg);
        
        // Simular respuesta inteligente después de 1-3 segundos
        const delay = 1000 + Math.random() * 2000;
        
        setTimeout(() => {
            // Mostrar indicador "escribiendo..."
            this.trigger('typing', {
                usuario_id: destinatarioId,
                escribiendo: true
            });
            
            // Después de 1-2 segundos, enviar respuesta
            setTimeout(() => {
                this.trigger('typing', {
                    usuario_id: destinatarioId,
                    escribiendo: false
                });
                
                this.simulateChatResponse(destinatarioId, mensaje, servicioId);
            }, 1000 + Math.random() * 1000);
        }, delay);
    }

    acceptService(servicioId) {
        return this.send({
            tipo: 'aceptar_servicio',
            servicio_id: servicioId,
            timestamp: new Date().toISOString()
        });
    }

    sendServiceStatusUpdate(servicioId, nuevoEstado, notas = null) {
        return this.send({
            tipo: 'estado_servicio',
            servicio_id: servicioId,
            nuevo_estado: nuevoEstado,
            notas: notas,
            timestamp: new Date().toISOString()
        });
    }

    sendLocationUpdate(latitude, longitude, servicioId) {
        return this.send({
            tipo: 'ubicacion',
            servicio_id: servicioId,
            latitude: latitude,
            longitude: longitude,
            timestamp: new Date().toISOString()
        });
    }

    // ============================================
    // SIMULACIÓN DE RESPUESTAS
    // ============================================
    
    simulateServerResponse(message) {
        const { tipo } = message;
        
        // Ping → Pong
        if (tipo === 'ping') {
            setTimeout(() => {
                this.trigger('pong', {
                    timestamp: new Date().toISOString()
                });
            }, 100);
        }
        
        // Aceptar servicio → Confirmación
        if (tipo === 'aceptar_servicio') {
            setTimeout(() => {
                this.trigger('servicio_aceptado', {
                    servicio_id: message.servicio_id,
                    mensaje: 'Servicio asignado exitosamente'
                });
                
                // Notificar al cliente (simulado)
                this.trigger('tecnico_asignado', {
                    servicio_id: message.servicio_id,
                    tecnico: {
                        id: this.userId,
                        nombre: 'Carlos Rodríguez',
                        telefono: '987654323',
                        foto: null,
                        calificacion: 4.8
                    },
                    tiempo_estimado: 25
                });
            }, 500);
        }
        
        // Cambio de estado → Notificación
        if (tipo === 'estado_servicio') {
            setTimeout(() => {
                const mensajes = {
                    'en_camino': 'El técnico está en camino',
                    'llegado': 'El técnico ha llegado',
                    'en_proceso': 'El servicio está en progreso',
                    'completado': 'El servicio ha sido completado'
                };
                
                this.trigger('estado_servicio_actualizado', {
                    servicio_id: message.servicio_id,
                    estado_nuevo: message.nuevo_estado,
                    mensaje: mensajes[message.nuevo_estado] || 'Estado actualizado',
                    timestamp: new Date().toISOString()
                });
            }, 300);
        }
    }

    simulateChatResponse(destinatarioId, mensajeOriginal, servicioId) {
        // Respuestas contextuales según lo que escribió el usuario
        let respuesta = '';
        
        const msgLower = mensajeOriginal.toLowerCase();
        
        // Saludos
        if (msgLower.match(/hola|buenos|buenas|saludos/i)) {
            const respuestas = [
                '¡Hola! ¿En qué puedo ayudarte?',
                'Hola, ¿cómo estás?',
                '¡Buenas! Dime en qué puedo ayudarte',
                'Hola, estoy a tu disposición'
            ];
            respuesta = respuestas[Math.floor(Math.random() * respuestas.length)];
        }
        // Preguntas sobre llegada/tiempo
        else if (msgLower.match(/llegaste|llegas|cuánto|cuando|tiempo|demora/i)) {
            const respuestas = [
                'Estoy en camino, llegaré en aproximadamente 15 minutos',
                'Salgo en 5 minutos, llegaré en unos 20 minutos',
                'Ya estoy cerca, unos 10 minutos más',
                'Calculo llegar en 15-20 minutos'
            ];
            respuesta = respuestas[Math.floor(Math.random() * respuestas.length)];
        }
        // Preguntas sobre ubicación
        else if (msgLower.match(/dónde|donde|ubicación|ubicacion|dirección|direccion/i)) {
            const respuestas = [
                'Voy por la Av. Arequipa, altura del Óvalo Gutiérrez',
                'Estoy llegando a tu zona',
                'Ya pasé el primer cruce, falta poco',
                'Voy llegando, estoy a 2 cuadras'
            ];
            respuesta = respuestas[Math.floor(Math.random() * respuestas.length)];
        }
        // Confirmaciones
        else if (msgLower.match(/ok|okay|bien|perfecto|vale|entendido|gracias/i)) {
            const respuestas = [
                '👍',
                'Perfecto, nos vemos pronto',
                'De acuerdo 👍',
                'Genial, cualquier cosa me avisas',
                'Okay, en un momento llego'
            ];
            respuesta = respuestas[Math.floor(Math.random() * respuestas.length)];
        }
        // Preguntas sobre el servicio
        else if (msgLower.match(/servicio|aceite|filtro|revision|trabajo/i)) {
            const respuestas = [
                'Llevo todo lo necesario para el servicio',
                'Tengo el aceite y filtros que solicitaste',
                'Todo listo para el cambio de aceite',
                'Sí, llevo las herramientas y repuestos necesarios'
            ];
            respuesta = respuestas[Math.floor(Math.random() * respuestas.length)];
        }
        // Preguntas sobre precio
        else if (msgLower.match(/precio|costo|cuanto|pago|cobrar/i)) {
            const respuestas = [
                'El precio se mantiene según lo acordado: S/.350',
                'Es el precio que conversamos, S/.350',
                'Como quedamos, S/.350 total'
            ];
            respuesta = respuestas[Math.floor(Math.random() * respuestas.length)];
        }
        // Consultas generales
        else if (msgLower.includes('?')) {
            const respuestas = [
                'Déjame revisar eso y te confirmo',
                'Sí, sin problema',
                'Claro, cuenta con eso',
                'Por supuesto, lo tengo en cuenta'
            ];
            respuesta = respuestas[Math.floor(Math.random() * respuestas.length)];
        }
        // Default
        else {
            const respuestas = [
                'Entendido, gracias por avisar',
                'Okay, perfecto',
                'De acuerdo 👍',
                'Recibido, gracias',
                'Perfecto, en un momento llego',
                'Sí, claro',
                'Entendido, nos vemos pronto'
            ];
            respuesta = respuestas[Math.floor(Math.random() * respuestas.length)];
        }
        
        // Enviar respuesta simulada
        this.trigger('chat_message', {
            mensaje_id: Date.now(),
            emisor_id: destinatarioId,
            emisor_nombre: 'Carlos Rodríguez',
            mensaje: respuesta,
            servicio_id: servicioId,
            timestamp: new Date().toISOString(),
            leido: false
        });
        
        console.log('[WS Mock] 🤖 Respuesta automática:', respuesta);
    }

    simulateInitialMessages() {
        // Simular bienvenida
        setTimeout(() => {
            if (this.userRole === 'cliente') {
                showToast('Conectado al sistema en tiempo real', 'success');
            } else if (this.userRole === 'tecnico') {
                showToast('Listo para recibir servicios', 'success');
                
                // Simular nuevo servicio después de 5 segundos
                setTimeout(() => {
                    this.simulateNewService();
                }, 5000);
            }
        }, 1000);
    }

    simulateNewService() {
        this.trigger('nuevo_servicio', {
            servicio_id: 123,
            tipo: 'cambio_aceite',
            cliente: {
                nombre: 'Juan Pérez',
                telefono: '987654321',
                direccion: 'Av. Arequipa 1234, Miraflores'
            },
            vehiculo: {
                marca: 'Toyota',
                modelo: 'Corolla',
                anio: 2020,
                placa: 'ABC-123'
            },
            monto: 350,
            distancia: 2.5,
            tiempo_estimado: 8
        });
        
        showToast('Nuevo servicio disponible cerca de ti', 'info', {
            duration: 10000,
            action: {
                label: 'Ver detalle',
                callback: () => {
                    console.log('Mostrar detalle del servicio');
                }
            }
        });
    }

    // ============================================
    // EVENT HANDLERS
    // ============================================
    
    on(event, handler) {
        this.handlers[event] = handler;
    }

    off(event) {
        delete this.handlers[event];
    }

    trigger(event, data = null) {
        if (this.handlers[event]) {
            this.handlers[event](data);
        }
        
        // Log
        if (event !== 'pong') {
            console.log(`[WS Mock] 📩 Evento: ${event}`, data);
        }
    }

    // ============================================
    // UTILIDADES
    // ============================================
    
    isOnline() {
        return this.isConnected;
    }

    getStats() {
        return {
            connected: this.isConnected,
            userId: this.userId,
            userRole: this.userRole,
            messageQueueLength: this.messageQueue.length,
            state: this.isConnected ? 'OPEN' : 'CLOSED'
        };
    }

    log(message, level = 'info') {
        const prefix = '[WS Mock]';
        console.log(prefix, message);
    }
}

// ============================================
// EXPORTAR
// ============================================

window.WebSocketMock = WebSocketMock;

console.log('[WS Mock] WebSocketMock cargado ✅');