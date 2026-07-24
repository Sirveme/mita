/* ============================================
   HERO ANIMATIONS
   ============================================ */

let currentIconStep = 1;
let iconInterval;

document.addEventListener('DOMContentLoaded', function() {
    initHeroAnimations();
});

function initHeroAnimations() {
    // Iniciar animación cíclica de iconos
    iconInterval = setInterval(animateIcons, 3000);
}

function animateIcons() {
    // Remover active de todos
    document.querySelectorAll('.icon-circle').forEach(circle => {
        circle.classList.remove('active');
    });
    
    // Avanzar al siguiente paso
    currentIconStep++;
    if (currentIconStep > 3) {
        currentIconStep = 1;
    }
    
    // Activar el paso actual
    const currentCircle = document.querySelector(`.icon-circle[data-step="${currentIconStep}"]`);
    if (currentCircle) {
        currentCircle.classList.add('active');
    }
}

function scrollToServices() {
    const servicesSection = document.querySelector('.services-section');
    if (servicesSection) {
        servicesSection.scrollIntoView({ 
            behavior: 'smooth',
            block: 'start'
        });
    }
}

// Detener animación cuando el usuario sale de la página
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        clearInterval(iconInterval);
    } else {
        iconInterval = setInterval(animateIcons, 3000);
    }
});

// Export para uso global
window.scrollToServices = scrollToServices;

console.log('✅ Hero animations loaded');