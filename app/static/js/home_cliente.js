// home_cliente.js

// ========================================
// ANIMACIÓN DEL HERO
// ========================================

let currentStep = 1;
let heroAnimationInterval;

document.addEventListener('DOMContentLoaded', function() {
    // Iniciar animación de iconos del hero
    startHeroAnimation();
    
    // Resto de inicializaciones...
    initServicesSlider();
    animateStats();
});

function startHeroAnimation() {
    const icons = document.querySelectorAll('.icon-circle');
    const steps = document.querySelectorAll('.step');
    
    if (icons.length === 0) return;
    
    heroAnimationInterval = setInterval(() => {
        // Remover clase active de todos
        icons.forEach(icon => icon.classList.remove('active'));
        steps.forEach(step => step.style.transform = 'scale(1)');
        
        // Agregar active al actual
        const currentIcon = icons[currentStep - 1];
        const currentStepEl = document.getElementById(`step${currentStep}`);
        
        if (currentIcon) currentIcon.classList.add('active');
        if (currentStepEl) {
            currentStepEl.style.transform = 'scale(1.05)';
            currentStepEl.style.transition = 'transform 0.3s ease';
        }
        
        // Siguiente paso
        currentStep = currentStep >= 3 ? 1 : currentStep + 1;
    }, 3000);
}

function scrollToServices() {
    const servicesSection = document.querySelector('.services-section');
    if (servicesSection) {
        servicesSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// Limpiar intervalo al salir
window.addEventListener('beforeunload', () => {
    if (heroAnimationInterval) {
        clearInterval(heroAnimationInterval);
    }
});



console.log('MITA - Home Cliente cargado');

// Función para navegar a solicitud de servicio
function irAServicio(tipo) {
    window.location.href = `/cliente/servicio/${tipo}`;
}

// Marcar item de navegación activo según la página actual
document.addEventListener('DOMContentLoaded', function() {
    const path = window.location.pathname;
    const navItems = document.querySelectorAll('.nav-item');
    
    navItems.forEach(item => {
        if (item.getAttribute('href') === path) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
});

// Animación de entrada para las cards
document.addEventListener('DOMContentLoaded', function() {
    const cards = document.querySelectorAll('.service-card');
    
    cards.forEach((card, index) => {
        setTimeout(() => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = 'all 0.5s ease';
            
            setTimeout(() => {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, 50);
        }, index * 100);
    });
});


// ========================================
// CONTROL DEL VIDEO HERO
// ========================================

let video;
let isPlaying = false;
let isMuted = true;

document.addEventListener('DOMContentLoaded', function() {
    video = document.getElementById('videoIntro');
    
    if (video) {
        // Iniciar video automáticamente en mute
        video.muted = true;
        video.play().catch(err => {
            console.log('Autoplay bloqueado:', err);
            // Si el autoplay falla, mostrar botón de play
            updatePlayButton(false);
        });
        
        // Eventos del video
        video.addEventListener('play', () => {
            isPlaying = true;
            updatePlayButton(true);
        });
        
        video.addEventListener('pause', () => {
            isPlaying = false;
            updatePlayButton(false);
        });
        
        video.addEventListener('timeupdate', updateProgress);
        
        video.addEventListener('ended', () => {
            video.currentTime = 0;
            video.play();
        });
    }
    
    // Inicializar slider de servicios
    initServicesSlider();
    
    // Animación de estadísticas
    animateStats();
});

// Toggle Play/Pause
function togglePlayPause() {
    if (!video) return;
    
    if (video.paused) {
        video.play();
    } else {
        video.pause();
    }
}

// Toggle Mute
function toggleMute() {
    if (!video) return;
    
    video.muted = !video.muted;
    isMuted = video.muted;
    updateMuteButton();
}

// Actualizar botón de play/pause
function updatePlayButton(playing) {
    const iconPlay = document.getElementById('iconPlay');
    if (iconPlay) {
        iconPlay.textContent = playing ? '⏸️' : '▶️';
    }
}

// Actualizar botón de mute
function updateMuteButton() {
    const iconSound = document.getElementById('iconSound');
    if (iconSound) {
        iconSound.textContent = isMuted ? '🔇' : '🔊';
    }
}

// Actualizar barra de progreso
function updateProgress() {
    const progressFill = document.getElementById('progressFill');
    if (progressFill && video) {
        const percentage = (video.currentTime / video.duration) * 100;
        progressFill.style.width = percentage + '%';
    }
}

// Scroll suave a servicios
function scrollToServices() {
    const servicesSection = document.querySelector('.services-section');
    if (servicesSection) {
        servicesSection.scrollIntoView({ behavior: 'smooth' });
    }
}

// ========================================
// SLIDER DE SERVICIOS
// ========================================

function initServicesSlider() {
    const slider = document.getElementById('sliderServicios');
    const dotsContainer = document.getElementById('sliderDots');
    
    if (!slider || !dotsContainer) return;
    
    const cards = slider.querySelectorAll('.service-card-modern');
    
    // Crear dots
    cards.forEach((_, index) => {
        const dot = document.createElement('div');
        dot.className = 'dot';
        if (index === 0) dot.classList.add('active');
        dot.onclick = () => scrollToCard(index);
        dotsContainer.appendChild(dot);
    });
    
    // Detectar scroll para actualizar dots
    slider.addEventListener('scroll', () => {
        updateActiveDot(slider, dotsContainer);
    });
}

function scrollToCard(index) {
    const slider = document.getElementById('sliderServicios');
    const cards = slider.querySelectorAll('.service-card-modern');
    
    if (cards[index]) {
        cards[index].scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
    }
}

function updateActiveDot(slider, dotsContainer) {
    const cards = slider.querySelectorAll('.service-card-modern');
    const dots = dotsContainer.querySelectorAll('.dot');
    
    cards.forEach((card, index) => {
        const rect = card.getBoundingClientRect();
        const sliderRect = slider.getBoundingClientRect();
        
        // Si la card está en el centro del viewport
        if (rect.left >= sliderRect.left && rect.right <= sliderRect.right) {
            dots.forEach(dot => dot.classList.remove('active'));
            if (dots[index]) dots[index].classList.add('active');
        }
    });
}

// ========================================
// NAVEGACIÓN A SERVICIOS
// ========================================

function irAServicio(tipo) {
    window.location.href = `/cliente/servicio/${tipo}`;
}

// ========================================
// ANIMACIÓN DE ESTADÍSTICAS
// ========================================

function animateStats() {
    const statNumbers = document.querySelectorAll('.stat-number');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateNumber(entry.target);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });
    
    statNumbers.forEach(stat => observer.observe(stat));
}

function animateNumber(element) {
    const target = parseInt(element.getAttribute('data-target'));
    const duration = 2000;
    const increment = target / (duration / 16);
    let current = 0;
    
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            element.textContent = target + (target === 98 ? '%' : '+');
            clearInterval(timer);
        } else {
            element.textContent = Math.floor(current) + (target === 98 ? '%' : '+');
        }
    }, 16);
}

// ========================================
// REPRODUCIR TESTIMONIO EN VIDEO
// ========================================

function reproducirTestimonio(id) {
    mostrarNotificacion('Reproduciendo testimonio...', 'info');
    // TODO: Implementar modal con video
}

// ========================================
// POLÍTICAS Y MODALES
// ========================================

function abrirPolitica(tipo) {
    mostrarNotificacion(`Abriendo política de ${tipo}...`, 'info');
    // TODO: Implementar modal o redirección
}

function abrirNotificaciones() {
    mostrarNotificacion('Tienes 3 notificaciones nuevas', 'info');
    // TODO: Implementar panel de notificaciones
}

function abrirPerfil() {
    window.location.href = '/cliente/perfil';
}