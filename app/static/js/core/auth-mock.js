// ============================================
// MITA - AUTH MOCK (SIN BASE DE DATOS)
// Ubicación: app/static/js/core/auth-mock.js
// ============================================

class AuthMock {
    constructor() {
        this.usuarios = [
            // CLIENTES
            {
                id: 1,
                email: 'cliente1@demo.com',
                password: 'demo123',
                nombre_completo: 'Juan Pérez García',
                telefono: '987654321',
                rol: 'cliente',
                foto: null
            },
            {
                id: 2,
                email: 'cliente2@demo.com',
                password: 'demo123',
                nombre_completo: 'María González López',
                telefono: '987654322',
                rol: 'cliente',
                foto: null
            },
            // TÉCNICOS
            {
                id: 3,
                email: 'tecnico1@demo.com',
                password: 'demo123',
                nombre_completo: 'Carlos Rodríguez Sánchez',
                telefono: '987654323',
                rol: 'tecnico',
                foto: null,
                especialidad: 'Mecánica Automotriz',
                calificacion: 4.8,
                servicios_completados: 245
            },
            {
                id: 4,
                email: 'tecnico2@demo.com',
                password: 'demo123',
                nombre_completo: 'Luis Mendoza Torres',
                telefono: '987654324',
                rol: 'tecnico',
                foto: null,
                especialidad: 'Electricidad Automotriz',
                calificacion: 4.6,
                servicios_completados: 189
            },
            // ADMIN
            {
                id: 5,
                email: 'admin@demo.com',
                password: 'admin123',
                nombre_completo: 'Admin MITA',
                telefono: '987654325',
                rol: 'admin',
                foto: null
            }
        ];
        
        this.init();
    }

    init() {
        console.log('[Auth Mock] Sistema de autenticación mock cargado');
        console.log(`[Auth Mock] ${this.usuarios.length} usuarios disponibles`);
    }

    // ============================================
    // LOGIN
    // ============================================
    
    login(email, password) {
        const usuario = this.usuarios.find(u => 
            u.email === email && u.password === password
        );

        if (!usuario) {
            return {
                success: false,
                error: 'Credenciales inválidas'
            };
        }

        // Generar token fake
        const token = this.generateFakeToken(usuario);
        
        // Guardar en localStorage
        localStorage.setItem('token', token);
        sessionStorage.setItem('userId', usuario.id.toString());
        sessionStorage.setItem('userRole', usuario.rol);
        sessionStorage.setItem('userName', usuario.nombre_completo);
        sessionStorage.setItem('userEmail', usuario.email);

        console.log(`[Auth Mock] ✅ Login exitoso: ${usuario.nombre_completo} (${usuario.rol})`);

        return {
            success: true,
            usuario: {
                id: usuario.id,
                email: usuario.email,
                nombre_completo: usuario.nombre_completo,
                rol: usuario.rol,
                telefono: usuario.telefono,
                foto: usuario.foto
            },
            token: token
        };
    }

    // ============================================
    // LOGIN RÁPIDO (sin formulario)
    // ============================================
    
    quickLogin(userType = 'cliente') {
        let usuario;
        
        if (userType === 'cliente') {
            usuario = this.usuarios.find(u => u.rol === 'cliente');
        } else if (userType === 'tecnico') {
            usuario = this.usuarios.find(u => u.rol === 'tecnico');
        } else if (userType === 'admin') {
            usuario = this.usuarios.find(u => u.rol === 'admin');
        }

        if (!usuario) {
            console.error(`[Auth Mock] No hay usuario ${userType}`);
            return null;
        }

        return this.login(usuario.email, usuario.password);
    }

    // ============================================
    // LOGOUT
    // ============================================
    
    logout() {
        localStorage.removeItem('token');
        sessionStorage.removeItem('userId');
        sessionStorage.removeItem('userRole');
        sessionStorage.removeItem('userName');
        sessionStorage.removeItem('userEmail');
        
        console.log('[Auth Mock] ✅ Logout exitoso');
    }

    // ============================================
    // OBTENER USUARIO ACTUAL
    // ============================================
    
    getCurrentUser() {
        const userId = sessionStorage.getItem('userId');
        
        if (!userId) {
            return null;
        }

        const usuario = this.usuarios.find(u => u.id === parseInt(userId));
        
        return usuario || null;
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

    // ============================================
    // OBTENER USUARIOS POR ROL
    // ============================================
    
    getUsuariosPorRol(rol) {
        return this.usuarios.filter(u => u.rol === rol);
    }

    getTecnicos() {
        return this.getUsuariosPorRol('tecnico');
    }

    getClientes() {
        return this.getUsuariosPorRol('cliente');
    }

    // ============================================
    // TOKEN FAKE
    // ============================================
    
    generateFakeToken(usuario) {
        const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
        const payload = btoa(JSON.stringify({
            sub: usuario.id.toString(),
            email: usuario.email,
            rol: usuario.rol,
            exp: Math.floor(Date.now() / 1000) + (30 * 24 * 60 * 60) // 30 días
        }));
        const signature = btoa('fake-signature-for-demo');
        
        return `${header}.${payload}.${signature}`;
    }

    // ============================================
    // HELPERS PARA DEMO
    // ============================================
    
    listarUsuarios() {
        console.log('\n' + '='.repeat(60));
        console.log('👥 USUARIOS DISPONIBLES PARA DEMO:');
        console.log('='.repeat(60));
        
        const porRol = {
            'cliente': [],
            'tecnico': [],
            'admin': []
        };
        
        this.usuarios.forEach(u => {
            porRol[u.rol].push(u);
        });
        
        Object.keys(porRol).forEach(rol => {
            console.log(`\n📋 ${rol.toUpperCase()}:`);
            porRol[rol].forEach(u => {
                console.log(`   ${u.email} / ${u.password}`);
                console.log(`   → ${u.nombre_completo}`);
            });
        });
        
        console.log('\n' + '='.repeat(60));
        console.log('💡 Para login rápido:');
        console.log('   authMock.quickLogin("cliente")');
        console.log('   authMock.quickLogin("tecnico")');
        console.log('   authMock.quickLogin("admin")');
        console.log('='.repeat(60) + '\n');
    }

    // ============================================
    // AUTO-LOGIN PARA DEMO
    // ============================================
    
    autoLogin(role = 'cliente') {
        console.log(`[Auth Mock] 🚀 Auto-login como ${role}...`);
        const result = this.quickLogin(role);
        
        if (result && result.success) {
            console.log(`[Auth Mock] ✅ Sesión iniciada como: ${result.usuario.nombre_completo}`);
            return result.usuario;
        }
        
        return null;
    }
}

// ============================================
// EXPORTAR E INICIALIZAR
// ============================================

window.AuthMock = AuthMock;

// Crear instancia global
const authMock = new AuthMock();
window.authMock = authMock;

// Auto-inicializar si no hay sesión
document.addEventListener('DOMContentLoaded', () => {
    if (!authMock.isAuthenticated()) {
        console.log('[Auth Mock] No hay sesión activa');
        console.log('[Auth Mock] 💡 Ejecuta: authMock.quickLogin("cliente")');
        authMock.listarUsuarios();
    } else {
        const usuario = authMock.getCurrentUser();
        console.log(`[Auth Mock] ✅ Sesión activa: ${usuario?.nombre_completo} (${usuario?.rol})`);
    }
});

console.log('[Auth Mock] Sistema cargado ✅');