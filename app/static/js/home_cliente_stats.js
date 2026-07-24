/* ============================================
   ANIMATED STATS COUNTER
   ============================================ */

let statsAnimated = false;

document.addEventListener('DOMContentLoaded', function() {
    initStatsObserver();
});

function initStatsObserver() {
    const statsSection = document.querySelector('.stats-section');
    if (!statsSection) return;
    
    // Intersection Observer para animar cuando sea visible
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !statsAnimated) {
                animateStats();
                statsAnimated = true;
            }
        });
    }, { threshold: 0.5 });
    
    observer.observe(statsSection);
}

function animateStats() {
    const statNumbers = document.querySelectorAll('.stat-number');
    
    statNumbers.forEach(stat => {
        const target = parseInt(stat.getAttribute('data-target'));
        const suffix = stat.getAttribute('data-suffix') || ''; // Leer sufijo
        const duration = 2000; // 2 segundos
        const increment = target / (duration / 16); // 60fps
        let current = 0;
        
        const updateCounter = () => {
            current += increment;
            if (current < target) {
                stat.textContent = Math.floor(current);
                requestAnimationFrame(updateCounter);
            } else {
                stat.textContent = target + suffix; // Agregar sufijo
            }
        };
        
        updateCounter();
    });
}