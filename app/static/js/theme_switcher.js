/* ============================================
   THEME SWITCHER
   ============================================ */

// Verificar tema guardado
const savedTheme = localStorage.getItem('serviplus-theme') || 'blue';

// Aplicar tema al cargar
document.addEventListener('DOMContentLoaded', function() {
    applyTheme(savedTheme);
    createThemeSwitcher();
});

function applyTheme(theme) {
    if (theme === 'brown') {
        document.documentElement.setAttribute('data-theme', 'brown');
    } else {
        document.documentElement.removeAttribute('data-theme');
    }
    localStorage.setItem('serviplus-theme', theme);
}

function createThemeSwitcher() {
    // Verificar si ya existe
    if (document.querySelector('.theme-switcher')) return;
    
    const switcher = document.createElement('div');
    switcher.className = 'theme-switcher';
    switcher.innerHTML = `
        <span class="theme-label">Tema</span>
        <div class="theme-toggle" onclick="toggleTheme()">
            <div class="theme-toggle-slider"></div>
        </div>
    `;
    
    document.body.appendChild(switcher);
}

function toggleTheme() {
    const currentTheme = localStorage.getItem('serviplus-theme') || 'blue';
    const newTheme = currentTheme === 'blue' ? 'brown' : 'blue';
    
    applyTheme(newTheme);
    
    // Animación suave
    document.body.style.transition = 'all 0.5s ease';
    
    // Notificación
    const temaTexto = newTheme === 'blue' ? 'Azul Noche' : 'Marrón Cálido';
    if (typeof mostrarNotificacion === 'function') {
        mostrarNotificacion(`Tema cambiado a ${temaTexto}`, 'success');
    }
}

// Export para uso global
window.toggleTheme = toggleTheme;
window.applyTheme = applyTheme;

console.log('✅ Theme switcher loaded');