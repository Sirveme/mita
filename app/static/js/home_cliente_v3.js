/* ========================================
   MITA - HOME V3 JAVASCRIPT
   Professional Hybrid Version
   ======================================== */

// Variables globales
let video;
let isVideoPlaying = false;
let isVideoMuted = true;
let currentTestimonialIndex = 0;
let testimonialSlider;

// ========================================
// INICIALIZACIÓN
// ========================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('MITA V3 - Professional Hybrid Loaded');
    
    // Inicializar componentes
    initVideo();
    initHeaderScroll();
    initTestimonials();
    initScrollAnimations();
    initSmoothScroll();
    
    // Intentar reproducir video automáticamente
    setTimeout(() => {
        autoPlayVideo();
    }, 500);
});

// ========================================
// CONTROL DEL VIDEO
// ========================================

function initVideo() {
    video = document.getElementById('heroVideo');
    
    if (!video) return;
    
    // Event listeners del video
    video.addEventListener('loadedmetadata', function() {
        console.log('Video cargado:', video.duration + 's');
    });
    
    video.addEventListener('timeupdate', updateVideoProgress);
    
    video.addEventListener('ended', showVideoEndCTA);
    
    video.addEventListener('play', function() {
        isVideoPlaying = true;
        updatePlayIcon();
    });
    
    video.addEventListener('pause', function() {
        isVideoPlaying = false;
        updatePlayIcon();
    });
    
    // Click en el video para play/pause
    video.addEventListener('click', toggleVideoPlay);
}

function autoPlayVideo() {
    if (!video) return;
    
    video.muted = true;
    video.play().then(() => {
        console.log('Video reproduciendo automáticamente');
        isVideoPlaying = true;
        updatePlayIcon();
    }).catch(err => {
        console.log('Autoplay bloqueado:', err);
        // Mostrar botón de play prominente si falla
        isVideoPlaying = false;
        updatePlayIcon();
    });
}

function toggleVideoPlay() {
    if (!video) return;
    
    if (video.paused) {
        video.play();
        hideVideoEndCTA();
    } else {
        video.pause();
    }
}

function toggleVideoMute() {
    if (!video) return;
    
    video.muted = !video.muted;
    isVideoMuted = video.muted;
    updateVolumeIcon();
}

function updatePlayIcon() {
    const playIcon = document.getElementById('playIcon');
    if (playIcon) {
        playIcon.className = isVideoPlaying ? 'fas fa-pause' : 'fas fa-play';
    }
}

function updateVolumeIcon() {
    const volumeIcon = document.getElementById('volumeIcon');
    if (volumeIcon) {
        volumeIcon.className = isVideoMuted ? 'fas fa-volume-mute' : 'fas fa-volume-up';
    }
}

function updateVideoProgress() {
    if (!video) return;
    
    const progressBar = document.getElementById('videoProgress');
    if (progressBar) {
        const percentage = (video.currentTime / video.duration) * 100;
        progressBar.style.width = percentage + '%';
    }
}

function showVideoEndCTA() {
    const endCTA = document.getElementById('videoEndCTA');
    if (endCTA) {
        endCTA.classList.add('show');
    }
}

function hideVideoEndCTA() {
    const endCTA = document.getElementById('videoEndCTA');
    if (endCTA) {
        endCTA.classList.remove('show');
    }
}

// ========================================
// HEADER SCROLL EFFECT
// ========================================

function initHeaderScroll() {
    const header = document.querySelector('.header-professional');
    
    if (!header) return;
    
    let lastScroll = 0;
    
    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        
        if (currentScroll > 100) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
        
        lastScroll = currentScroll;
    });
}

// ========================================
// SMOOTH SCROLL
// ========================================

function initSmoothScroll() {
    const links = document.querySelectorAll('a[href^="#"]');
    
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            
            if (href === '#' || !href) return;
            
            e.preventDefault();
            
            const target = document.querySelector(href);
            
            if (target) {
                const headerHeight = 80;
                const targetPosition = target.offsetTop - headerHeight;
                
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
}

function scrollToServices() {
    const servicesSection = document.querySelector('.services-professional');
    
    if (servicesSection) {
        const headerHeight = 80;
        const targetPosition = servicesSection.offsetTop - headerHeight;
        
        window.scrollTo({
            top: targetPosition,
            behavior: 'smooth'
        });
    }
}

// ========================================
// TESTIMONIALS SLIDER
// ========================================

function initTestimonials() {
    testimonialSlider = document.getElementById('testimonialsSlider');
    const dotsContainer = document.getElementById('testimonialsDots');
    
    if (!testimonialSlider || !dotsContainer) return;
    
    const cards = testimonialSlider.querySelectorAll('.testimonial-card-pro');
    
    // Crear dots
    cards.forEach((_, index) => {
        const dot = document.createElement('span');
        dot.className = 'dot';
        if (index === 0) dot.classList.add('active');
        dot.onclick = () => goToTestimonialPro(index);
        dotsContainer.appendChild(dot);
    });
    
    // Detectar scroll para actualizar dots
    testimonialSlider.addEventListener('scroll', updateTestimonialDots);
    
    // Auto-scroll cada 5 segundos
    /*
    setInterval(() => {
        nextTestimonialPro();
    }, 5000);
    */
}

function updateTestimonialDots() {
    if (!testimonialSlider) return;
    
    const cards = testimonialSlider.querySelectorAll('.testimonial-card-pro');
    const dots = document.querySelectorAll('.testimonials-dots .dot');
    
    cards.forEach((card, index) => {
        const rect = card.getBoundingClientRect();
        const sliderRect = testimonialSlider.getBoundingClientRect();
        
        // Detectar card más visible
        const visibility = Math.max(0, Math.min(
            rect.right - sliderRect.left,
            sliderRect.right - rect.left
        ));
        
        if (visibility > card.offsetWidth * 0.6) {
            currentTestimonialIndex = index;
            dots.forEach(dot => dot.classList.remove('active'));
            if (dots[index]) dots[index].classList.add('active');
        }
    });
}

function nextTestimonialPro() {
    if (!testimonialSlider) return;
    
    const cards = testimonialSlider.querySelectorAll('.testimonial-card-pro');
    const nextIndex = (currentTestimonialIndex + 1) % cards.length;
    
    scrollToTestimonialCard(nextIndex);
}

function prevTestimonialPro() {
    if (!testimonialSlider) return;
    
    const cards = testimonialSlider.querySelectorAll('.testimonial-card-pro');
    const prevIndex = currentTestimonialIndex === 0 
        ? cards.length - 1 
        : currentTestimonialIndex - 1;
    
    scrollToTestimonialCard(prevIndex);
}

function goToTestimonialPro(index) {
    scrollToTestimonialCard(index);
}

function scrollToTestimonialCard(index) {
    if (!testimonialSlider) return;
    
    const cards = testimonialSlider.querySelectorAll('.testimonial-card-pro');
    
    if (cards[index]) {
        cards[index].scrollIntoView({
            behavior: 'smooth',
            inline: 'center',
            block: 'nearest'
        });
        currentTestimonialIndex = index;
    }
}

// ========================================
// SCROLL ANIMATIONS
// ========================================

function initScrollAnimations() {
    const animatedElements = document.querySelectorAll(
        '.process-step, .service-card-pro, .guarantee-card, .testimonial-card-pro'
    );
    
    const observerOptions = {
        threshold: 0.15,
        rootMargin: '0px 0px -80px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '0';
                entry.target.style.transform = 'translateY(40px)';
                
                setTimeout(() => {
                    entry.target.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }, 100);
                
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    animatedElements.forEach(el => observer.observe(el));
}

// ========================================
// NAVEGACIÓN A SERVICIOS
// ========================================

function irAServicio(tipo) {
    // Animación de feedback
    mostrarNotificacion(`Cargando servicio de ${tipo}...`, 'info');
    
    // Pequeño delay para feedback visual
    setTimeout(() => {
        window.location.href = `/cliente/servicio/${tipo}`;
    }, 300);
}

// ========================================
// MENÚ MÓVIL
// ========================================

function toggleMobileMenu() {
    mostrarNotificacion('Menú móvil próximamente', 'info');
    
    // TODO: Implementar menú hamburguesa móvil
    // const mobileMenu = document.createElement('div');
    // mobileMenu.className = 'mobile-menu-overlay';
    // ...
}

// ========================================
// NOTIFICACIONES
// ========================================

function abrirNotificaciones() {
    mostrarNotificacion('Tienes 3 notificaciones nuevas', 'info');
    
    // TODO: Implementar panel de notificaciones
}

function abrirPerfil() {
    window.location.href = '/cliente/perfil';
}

// ========================================
// SISTEMA DE NOTIFICACIONES TOAST
// ========================================

function mostrarNotificacion(mensaje, tipo = 'info') {
    // Remover notificaciones previas
    const prevToast = document.querySelector('.toast-notification-v3');
    if (prevToast) {
        prevToast.remove();
    }
    
    // Crear nueva notificación
    const toast = document.createElement('div');
    toast.className = `toast-notification-v3 toast-${tipo}`;
    
    // Icono según tipo
    let iconClass = 'fa-info-circle';
    if (tipo === 'success') iconClass = 'fa-check-circle';
    if (tipo === 'error') iconClass = 'fa-exclamation-circle';
    if (tipo === 'warning') iconClass = 'fa-exclamation-triangle';
    
    toast.innerHTML = `
        <i class="fas ${iconClass} toast-icon-v3"></i>
        <span class="toast-message-v3">${mensaje}</span>
    `;
    
    // Agregar al body
    document.body.appendChild(toast);
    
    // Mostrar con animación
    setTimeout(() => {
        toast.classList.add('show');
    }, 100);
    
    // Ocultar y remover
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            toast.remove();
        }, 400);
    }, 3500);
}

// ========================================
// CONTADOR ANIMADO DE STATS
// ========================================

function animateCounters() {
    const counters = document.querySelectorAll('.cta-stat strong');
    
    counters.forEach(counter => {
        const text = counter.textContent;
        const isPercentage = text.includes('/');
        
        let target;
        if (isPercentage) {
            target = parseFloat(text.replace(/[^0-9.]/g, ''));
        } else {
            target = parseInt(text.replace(/[^0-9]/g, ''));
        }
        
        const duration = 2000;
        const increment = target / (duration / 16);
        let current = 0;
        
        const updateCounter = () => {
            current += increment;
            
            if (current < target) {
                if (isPercentage) {
                    counter.textContent = current.toFixed(1) + '/5';
                } else {
                    counter.textContent = Math.floor(current).toLocaleString() + '+';
                }
                requestAnimationFrame(updateCounter);
            } else {
                if (isPercentage) {
                    counter.textContent = target.toFixed(1) + '/5';
                } else {
                    counter.textContent = target.toLocaleString() + '+';
                }
            }
        };
        
        updateCounter();
    });
}

// Observar cuando stats entran en viewport
const statsObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            animateCounters();
            statsObserver.unobserve(entry.target);
        }
    });
}, { threshold: 0.5 });

const ctaStats = document.querySelector('.cta-stats');
if (ctaStats) {
    statsObserver.observe(ctaStats);
}

// ========================================
// LAZY LOADING DE IMÁGENES
// ========================================

function initLazyLoading() {
    const images = document.querySelectorAll('img[data-src]');
    
    const imageObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
                imageObserver.unobserve(img);
            }
        });
    });
    
    images.forEach(img => imageObserver.observe(img));
}

initLazyLoading();

// ========================================
// DETECTAR MOBILE
// ========================================

function isMobile() {
    return window.innerWidth <= 768;
}

// ========================================
// PREVENIR ZOOM EN INPUTS (MÓVIL)
// ========================================

function preventInputZoom() {
    if (isMobile()) {
        const inputs = document.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.addEventListener('focus', function() {
                const viewport = document.querySelector('meta[name=viewport]');
                if (viewport) {
                    viewport.setAttribute('content', 
                        'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0'
                    );
                }
            });
            
            input.addEventListener('blur', function() {
                const viewport = document.querySelector('meta[name=viewport]');
                if (viewport) {
                    viewport.setAttribute('content', 
                        'width=device-width, initial-scale=1.0'
                    );
                }
            });
        });
    }
}

preventInputZoom();

// ========================================
// KEYBOARD NAVIGATION
// ========================================

document.addEventListener('keydown', (e) => {
    // Escape para cerrar modales
    if (e.key === 'Escape') {
        hideVideoEndCTA();
    }
    
    // Espacio para play/pause video
    if (e.key === ' ' && document.activeElement.tagName !== 'INPUT') {
        e.preventDefault();
        toggleVideoPlay();
    }
    
    // Flechas para testimonios
    if (e.key === 'ArrowLeft') {
        prevTestimonialPro();
    }
    if (e.key === 'ArrowRight') {
        nextTestimonialPro();
    }
});

// ========================================
// PERFORMANCE: THROTTLE SCROLL EVENTS
// ========================================

function throttle(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ========================================
// ANALYTICS TRACKING (Placeholder)
// ========================================

function trackEvent(category, action, label) {
    console.log('Track Event:', { category, action, label });
    
    // TODO: Integrar con Google Analytics
    // gtag('event', action, {
    //     'event_category': category,
    //     'event_label': label
    // });
}

// Trackear clicks en servicios
document.querySelectorAll('.service-card-pro').forEach(card => {
    card.addEventListener('click', function() {
        const serviceName = this.querySelector('h3').textContent;
        trackEvent('Services', 'Click', serviceName);
    });
});

// Trackear reproducción de video
if (video) {
    video.addEventListener('play', () => {
        trackEvent('Video', 'Play', 'Hero Video');
    });
    
    video.addEventListener('ended', () => {
        trackEvent('Video', 'Complete', 'Hero Video');
    });
}

// ========================================
// VISIBILITY CHANGE: PAUSAR VIDEO
// ========================================

document.addEventListener('visibilitychange', function() {
    if (document.hidden && video && !video.paused) {
        video.pause();
    }
});

// ========================================
// RESIZE HANDLER (Optimizado)
// ========================================

let resizeTimer;
window.addEventListener('resize', throttle(() => {
    console.log('Window resized');
    
    // Ajustar slider de testimonios si es necesario
    if (testimonialSlider) {
        updateTestimonialDots();
    }
}, 250));

// ========================================
// CLEANUP AL SALIR
// ========================================

window.addEventListener('beforeunload', () => {
    if (video) {
        video.pause();
        video.currentTime = 0;
    }
});

// ========================================
// SERVICE WORKER (PWA - Opcional)
// ========================================

if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        // navigator.serviceWorker.register('/sw.js')
        //     .then(reg => console.log('Service Worker registrado'))
        //     .catch(err => console.log('Service Worker error:', err));
    });
}

// ========================================
// EXPORT FUNCIONES GLOBALES
// ========================================

window.toggleVideoPlay = toggleVideoPlay;
window.toggleVideoMute = toggleVideoMute;
window.scrollToServices = scrollToServices;
window.irAServicio = irAServicio;
window.abrirNotificaciones = abrirNotificaciones;
window.abrirPerfil = abrirPerfil;
window.toggleMobileMenu = toggleMobileMenu;
window.nextTestimonialPro = nextTestimonialPro;
window.prevTestimonialPro = prevTestimonialPro;
window.goToTestimonialPro = goToTestimonialPro;
window.mostrarNotificacion = mostrarNotificacion;

console.log('✅ MITA V3 inicializado correctamente');