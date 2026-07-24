// ============================================
// MITA - AUTH MANAGER
// Ruta: app/static/js/core/auth-manager.js
// ============================================

class AuthManager {
    constructor() {
        this.apiUrl = window.location.origin;
        this.init();
    }

    init() {
        console.log('[Auth] Auth Manager inicializado');
    }

    async login(telefono, password) {
        try {
            const response = await fetch(`${this.apiUrl}/api/v1/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    identifier: telefono,
                    password: password 
                })
            });

            if (!response.ok) {
                const error = await response.json();
                return {
                    success: false,
                    error: error.detail || 'Error de autenticación'
                };
            }

            const data = await response.json();
            
            localStorage.setItem('token', data.access_token);
            if (data.refresh_token) {
                localStorage.setItem('refresh_token', data.refresh_token);
            }
            sessionStorage.setItem('userId', data.usuario.id.toString());
            sessionStorage.setItem('userRole', data.usuario.rol);
            sessionStorage.setItem('userName', data.usuario.nombre_completo);
            sessionStorage.setItem('userPhone', data.usuario.telefono);

            console.log(`[Auth] ✅ Login: ${data.usuario.nombre_completo}`);

            return {
                success: true,
                usuario: data.usuario,
                token: data.access_token
            };

        } catch (error) {
            console.error('[Auth] Error:', error);
            return {
                success: false,
                error: 'Error de conexión'
            };
        }
    }

    logout() {
        localStorage.removeItem('token');
        localStorage.removeItem('refresh_token');
        sessionStorage.clear();
        
        console.log('[Auth] ✅ Logout');
        window.location.href = '/login';
    }

    async getCurrentUser() {
        const token = localStorage.getItem('token');
        
        if (!token) return null;

        try {
            const response = await fetch(`${this.apiUrl}/api/v1/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                this.logout();
                return null;
            }

            return await response.json();

        } catch (error) {
            console.error('[Auth] Error:', error);
            return null;
        }
    }

    isAuthenticated() {
        return !!localStorage.getItem('token');
    }

    getUserRole() {
        return sessionStorage.getItem('userRole');
    }

    getUserId() {
        const id = sessionStorage.getItem('userId');
        return id ? parseInt(id) : null;
    }

    getUserName() {
        return sessionStorage.getItem('userName');
    }

    getUserPhone() {
        return sessionStorage.getItem('userPhone');
    }

    getToken() {
        return localStorage.getItem('token');
    }

    async changePassword(currentPassword, newPassword) {
        const token = this.getToken();
        
        try {
            const response = await fetch(`${this.apiUrl}/api/v1/auth/change-password`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword
                })
            });

            if (!response.ok) {
                const error = await response.json();
                return {
                    success: false,
                    error: error.detail || 'Error al cambiar contraseña'
                };
            }

            return {
                success: true,
                message: 'Contraseña actualizada'
            };

        } catch (error) {
            return {
                success: false,
                error: 'Error de conexión'
            };
        }
    }

    async crearCuenta(telefono, password, solicitudId = null) {
        try {
            const response = await fetch(`${this.apiUrl}/api/v1/auth/crear-cuenta`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    telefono: telefono,
                    password: password,
                    solicitud_id: solicitudId
                })
            });

            if (!response.ok) {
                const error = await response.json();
                return {
                    success: false,
                    error: error.detail || 'Error al crear cuenta'
                };
            }

            const data = await response.json();
            
            localStorage.setItem('token', data.access_token);
            sessionStorage.setItem('userId', data.usuario.id.toString());
            sessionStorage.setItem('userRole', data.usuario.rol);
            sessionStorage.setItem('userName', data.usuario.nombre_completo);
            sessionStorage.setItem('userPhone', data.usuario.telefono);

            console.log('[Auth] ✅ Cuenta creada y login automático');

            return {
                success: true,
                usuario: data.usuario
            };

        } catch (error) {
            return {
                success: false,
                error: 'Error de conexión'
            };
        }
    }
}

window.AuthManager = AuthManager;

const authManager = new AuthManager();
window.authManager = authManager;

console.log('[Auth] Auth Manager cargado ✅');