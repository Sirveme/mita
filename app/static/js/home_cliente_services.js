/* ============================================
   SERVICES SLIDER
   ============================================ */

let sliderServicios;
let dotsContainer;

document.addEventListener('DOMContentLoaded', function() {
    initServicesSlider();
});

function initServicesSlider() {
    sliderServicios = document.getElementById('sliderServicios');
    dotsContainer = document.getElementById('sliderDots');
    
    if (!sliderServicios) return;

    // Crear dots si existen en el HTML (idempotente: se limpia antes de reconstruir)
    if (dotsContainer) {
        dotsContainer.innerHTML = '';
        const cards = sliderServicios.querySelectorAll('.service-card-modern');
        cards.forEach((_, index) => {
            const dot = document.createElement('span');
            dot.className = 'dot';
            if (index === 0) dot.classList.add('active');
            dot.onclick = () => scrollToCard(index);
            dotsContainer.appendChild(dot);
        });
    }
    
    // Actualizar dots al hacer scroll
    sliderServicios.addEventListener('scroll', updateDots);
}

function scrollToCard(index) {
    const cards = sliderServicios.querySelectorAll('.service-card-modern');
    if (cards[index]) {
        cards[index].scrollIntoView({ 
            behavior: 'smooth', 
            block: 'nearest', 
            inline: 'center' 
        });
    }
}

function updateDots() {
    if (!dotsContainer) return;
    
    const cards = sliderServicios.querySelectorAll('.service-card-modern');
    const scrollLeft = sliderServicios.scrollLeft;
    const cardWidth = cards[0].offsetWidth;
    const currentIndex = Math.round(scrollLeft / cardWidth);
    
    const dots = dotsContainer.querySelectorAll('.dot');
    dots.forEach((dot, index) => {
        dot.classList.toggle('active', index === currentIndex);
    });
}

function irAServicio(tipo) {
    window.location.href = `/cliente/servicio/${tipo}`;
}

// Export para uso global
window.irAServicio = irAServicio;
window.initServicesSlider = initServicesSlider;  // permite reinicializar tras render dinámico

console.log('✅ Services slider loaded');