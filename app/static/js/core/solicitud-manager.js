// ============================================
// MITA - SOLICITUD MANAGER
// Ruta: app/static/js/core/solicitud-manager.js
// ============================================

class SolicitudManager {
    constructor() {
        this.apiUrl = window.location.origin;
        this.deviceId = this.getDeviceId();
        this.init();
    }

    init() {
        console.log('[Solicitud] Manager inicializado');
        console.log('[Solicitud] Device ID:', this.deviceId);
    }

    getDeviceId() {
        let deviceId = localStorage.getItem('device_id');
        if (!deviceId) {
            deviceId = 'device_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
            localStorage.setItem('device_id', deviceId);
        }
        return deviceId;
    }

    async crearSolicitud(datos) {
        try {
            // Agregar device_id automático
            datos.device_id = this.deviceId;
            
            // Agregar push_token si está disponible
            try {
                if (window.pushManager && typeof window.pushManager.getToken === 'function') {
                    datos.push_token = await window.pushManager.getToken();
                }
            } catch (pushError) {
                console.log('[Solicitud] Push token no disponible:', pushError.message);
                datos.push_token = null;
            }

            const response = await fetch(`${this.apiUrl}/api/v1/solicitudes/crear`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(datos)
            });

            if (!response.ok) {
                const error = await response.json();
                return {
                    success: false,
                    error: error.detail || 'Error al crear solicitud'
                };
            }

            const data = await response.json();
            
            // ============================================
            // FIX: Servidor retorna "id" NO "solicitud_id"
            // ============================================
            
            // Guardar ID en localStorage
            localStorage.setItem('solicitud_actual_id', data.id.toString());
            localStorage.setItem('solicitud_actual', JSON.stringify({
                id: data.id,
                device_id: data.device_id,
                estado: data.estado,
                tipo_servicio: data.tipo_servicio,
                created_at: data.created_at
            }));

            console.log('[Solicitud] ✅ Creada:', data.id);

            return {
                success: true,
                solicitud_id: data.id,  // ← Cambio aquí
                id: data.id,            // ← Agregar también
                estado: data.estado,
                data: data              // ← Incluir objeto completo
            };

        } catch (error) {
            console.error('[Solicitud] Error:', error);
            return {
                success: false,
                error: 'Error de conexión'
            };
        }
    }

    async obtenerSolicitud(solicitudId) {
        try {
            const telefono = sessionStorage.getItem('temp_telefono');
            
            const url = new URL(`${this.apiUrl}/api/v1/solicitudes/${solicitudId}`);
            url.searchParams.append('device_id', this.deviceId);
            if (telefono) {
                url.searchParams.append('telefono', telefono);
            }

            const response = await fetch(url);

            if (!response.ok) {
                const error = await response.json();
                return {
                    success: false,
                    error: error.detail || 'Error al obtener solicitud'
                };
            }

            const data = await response.json();
            
            return {
                success: true,
                solicitud: data
            };

        } catch (error) {
            console.error('[Solicitud] Error:', error);
            return {
                success: false,
                error: 'Error de conexión'
            };
        }
    }

    async enviarMensaje(solicitudId, mensaje, remitenteNombre) {
        try {
            const response = await fetch(`${this.apiUrl}/api/v1/solicitudes/chat/enviar`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    solicitud_id: solicitudId,
                    remitente_tipo: 'cliente',
                    remitente_id: null,
                    remitente_nombre: remitenteNombre,
                    tipo_mensaje: 'texto',
                    contenido: mensaje
                })
            });

            if (!response.ok) {
                const error = await response.json();
                return {
                    success: false,
                    error: error.detail || 'Error al enviar mensaje'
                };
            }

            const data = await response.json();
            
            return {
                success: true,
                mensaje: data
            };

        } catch (error) {
            console.error('[Solicitud] Error:', error);
            return {
                success: false,
                error: 'Error de conexión'
            };
        }
    }

    async obtenerMensajes(solicitudId, limit = 50) {
        try {
            const response = await fetch(
                `${this.apiUrl}/api/v1/solicitudes/chat/${solicitudId}/mensajes?limit=${limit}`
            );

            if (!response.ok) {
                return {
                    success: false,
                    error: 'Error al obtener mensajes'
                };
            }

            const data = await response.json();
            
            return {
                success: true,
                mensajes: data
            };

        } catch (error) {
            return {
                success: false,
                error: 'Error de conexión'
            };
        }
    }

    async calificarServicio(solicitudId, calificacion, comentario = null) {
        try {
            const response = await fetch(
                `${this.apiUrl}/api/v1/solicitudes/${solicitudId}/calificar?device_id=${this.deviceId}`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        calificacion: calificacion,
                        comentario: comentario
                    })
                }
            );

            if (!response.ok) {
                const error = await response.json();
                return {
                    success: false,
                    error: error.detail || 'Error al calificar'
                };
            }

            const data = await response.json();
            
            return {
                success: true,
                message: data.message
            };

        } catch (error) {
            return {
                success: false,
                error: 'Error de conexión'
            };
        }
    }

    getSolicitudActual() {
        const id = localStorage.getItem('solicitud_actual');
        return id ? parseInt(id) : null;
    }

    guardarDatosTemporales(nombre, telefono) {
        sessionStorage.setItem('temp_nombre', nombre);
        sessionStorage.setItem('temp_telefono', telefono);
    }

    getDatosTemporales() {
        return {
            nombre: sessionStorage.getItem('temp_nombre'),
            telefono: sessionStorage.getItem('temp_telefono')
        };
    }
}

window.SolicitudManager = SolicitudManager;

const solicitudManager = new SolicitudManager();
window.solicitudManager = solicitudManager;

console.log('[Solicitud] Solicitud Manager cargado ✅');