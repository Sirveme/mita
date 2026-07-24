/* ========================================
   MITA - HOME V2 JAVASCRIPT
   ======================================== */

// Variables globales
let currentTestimonialIndex = 0;
let testimonialInterval;

// ========================================
// INICIALIZACIÓN
// ========================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('MITA V2 - Loaded');
    
    // Inicializar componentes
    initHeaderScroll();
    initTestimonialCarousel();
    initScrollAnimations();
    
    // Smooth scroll para links internos
    initSmoothScroll();
});

// ========================================
// HEADER SCROLL EFFECT
// ========================================

function initHeaderScroll() {
    const header = document.querySelector('.header-glass');
    
    if (!header) return;
    
    let lastScroll = 0;
    
    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        
        // Agregar clase cuando se hace scroll
        if (currentScroll > 50) {
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
            
            if (href === '#') return;
            
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

// ========================================
// SCROLL TO SERVICES
// ========================================

function scrollToServices() {
    const servicesSection = document.querySelector('.services-premium');
    
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
// CAROUSEL DE TESTIMONIOS
// ========================================

function initTestimonialCarousel() {
    const slides = document.querySelectorAll('.testimonial-slide');
    const dots = document.querySelectorAll('.carousel-dots .dot');
    
    if (slides.length === 0) return;
    
    // Activar primer slide
    showTestimonial(0);
    
    // Auto-rotate cada 5 segundos
    testimonialInterval = setInterval(() => {
        nextTestimonial();
    }, 5000);
    
    // Pausar auto-rotate al hover
    const carousel = document.querySelector('.testimonials-carousel');
    
    if (carousel) {
        carousel.addEventListener('mouseenter', () => {
            clearInterval(testimonialInterval);
        });
        
        carousel.addEventListener('mouseleave', () => {
            testimonialInterval = setInterval(() => {
                nextTestimonial();
            }, 5000);
        });
    }
}

function showTestimonial(index) {
    const slides = document.querySelectorAll('.testimonial-slide');
    const dots = document.querySelectorAll('.carousel-dots .dot');
    
    // Remover active de todos
    slides.forEach(slide => slide.classList.remove('active'));
    dots.forEach(dot => dot.classList.remove('active'));
    
    // Activar el actual
    if (slides[index]) slides[index].classList.add('active');
    if (dots[index]) dots[index].classList.add('active');
    
    currentTestimonialIndex = index;
}

function nextTestimonial() {
    const slides = document.querySelectorAll('.testimonial-slide');
    const nextIndex = (currentTestimonialIndex + 1) % slides.length;
    showTestimonial(nextIndex);
}

function prevTestimonial() {
    const slides = document.querySelectorAll('.testimonial-slide');
    const prevIndex = currentTestimonialIndex === 0 
        ? slides.length - 1 
        : currentTestimonialIndex - 1;
    showTestimonial(prevIndex);
}

function goToTestimonial(index) {
    showTestimonial(index);
}

// ========================================
// SCROLL ANIMATIONS (Intersection Observer)
// ========================================

function initScrollAnimations() {
    const animatedElements = document.querySelectorAll(
        '.step-card, .service-card-premium, .why-item'
    );
    
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '0';
                entry.target.style.transform = 'translateY(30px)';
                
                setTimeout(() => {
                    entry.target.style.transition = 'all 0.6s ease';
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
    // Mostrar loading
    mostrarNotificacion('Cargando servicio...', 'info');
    
    // Redirigir después de un pequeño delay para feedback visual
    setTimeout(() => {
        window.location.href = `/cliente/servicio/${tipo}`;
    }, 300);
}

// ========================================
// VIDEO DEMO
// ========================================

function verDemo() {
    mostrarNotificacion('Demo próximamente disponible', 'info');
    
    // TODO: Implementar modal con video demo
    // const modal = document.createElement('div');
    // modal.className = 'video-modal';
    // ...
}

// ========================================
// NOTIFICACIONES
// ========================================

function abrirNotificaciones() {
    mostrarNotificacion('Tienes 3 notificaciones nuevas', 'info');
    
    // TODO: Implementar panel de notificaciones
    // Podría ser un dropdown o modal
}

// ========================================
// PERFIL DE USUARIO
// ========================================

function abrirPerfil() {
    window.location.href = '/cliente/perfil';
}

// ========================================
// UTILIDADES - NOTIFICACIONES TOAST
// ========================================

function mostrarNotificacion(mensaje, tipo = 'info') {
    // Crear elemento de notificación
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${tipo}`;
    
    // Icono según tipo
    let icono = 'ℹ️';
    if (tipo === 'success') icono = '✅';
    if (tipo === 'error') icono = '❌';
    if (tipo === 'warning') icono = '⚠️';
    
    toast.innerHTML = `
        <span class="toast-icon">${icono}</span>
        <span class="toast-message">${mensaje}</span>
    `;
    
    // Agregar al body
    document.body.appendChild(toast);
    
    // Mostrar con animación
    setTimeout(() => {
        toast.classList.add('show');
    }, 100);
    
    // Ocultar y remover después de 3 segundos
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3000);
}

// ========================================
// CONTADOR ANIMADO DE STATS
// ========================================

function animateCounters() {
    const counters = document.querySelectorAll('.stat-mini strong');
    
    counters.forEach(counter => {
        const target = parseInt(counter.textContent.replace(/[^0-9]/g, ''));
        const duration = 2000;
        const increment = target / (duration / 16);
        let current = 0;
        
        const updateCounter = () => {
            current += increment;
            
            if (current < target) {
                counter.textContent = Math.floor(current).toLocaleString() + '+';
                requestAnimationFrame(updateCounter);
            } else {
                counter.textContent = target.toLocaleString() + '+';
            }
        };
        
        updateCounter();
    });
}

// Iniciar contadores cuando sean visibles
const statsObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            animateCounters();
            statsObserver.unobserve(entry.target);
        }
    });
}, { threshold: 0.5 });

const heroStats = document.querySelector('.hero-stats');
if (heroStats) {
    statsObserver.observe(heroStats);
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

// Iniciar lazy loading
initLazyLoading();

// ========================================
// PREVENIR SCROLL HORIZONTAL
// ========================================

function preventHorizontalScroll() {
    document.body.style.overflowX = 'hidden';
}

preventHorizontalScroll();

// ========================================
// DETECTAR MOBILE
// ========================================

function isMobile() {
    return window.innerWidth <= 768;
}

// ========================================
// OPTIMIZACIÓN DE RESIZE
// ========================================

let resizeTimer;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
        // Código que se ejecuta después de que el usuario deja de hacer resize
        console.log('Resize completed');
    }, 250);
});

// ========================================
// KEYBOARD NAVIGATION
// ========================================

document.addEventListener('keydown', (e) => {
    // Escape para cerrar modales (cuando los implementemos)
    if (e.key === 'Escape') {
        // Cerrar cualquier modal abierto
    }
    
    // Flechas para navegar testimonios
    if (e.key === 'ArrowLeft') {
        prevTestimonial();
    }
    if (e.key === 'ArrowRight') {
        nextTestimonial();
    }
});

// ========================================
// ANALYTICS (Placeholder)
// ========================================

function trackEvent(category, action, label) {
    console.log('Track Event:', category, action, label);
    
    // TODO: Integrar con Google Analytics o similar
    // gtag('event', action, {
    //     'event_category': category,
    //     'event_label': label
    // });
}

// Trackear clicks en servicios
document.querySelectorAll('.service-card-premium').forEach(card => {
    card.addEventListener('click', function() {
        const serviceName = this.querySelector('h3').textContent;
        trackEvent('Services', 'Click', serviceName);
    });
});

// ========================================
// CLEANUP AL SALIR
// ========================================

window.addEventListener('beforeunload', () => {
    if (testimonialInterval) {
        clearInterval(testimonialInterval);
    }
});

// ========================================
// EXPORT FUNCIONES PARA USO GLOBAL
// ========================================

window.scrollToServices = scrollToServices;
window.irAServicio = irAServicio;
window.verDemo = verDemo;
window.abrirNotificaciones = abrirNotificaciones;
window.abrirPerfil = abrirPerfil;
window.nextTestimonial = nextTestimonial;
window.prevTestimonial = prevTestimonial;
window.goToTestimonial = goToTestimonial;
window.mostrarNotificacion = mostrarNotificacion;