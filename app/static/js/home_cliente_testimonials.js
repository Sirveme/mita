// ============================================
// TESTIMONIOS - FUNCIONES
// ============================================

const testimonios = {
    1: {
        video: '/static/vid/testimonio-aceite-5.mp4',
        nombre: 'Carlos Mendoza',
        servicio: 'Cambio de aceite',
        iniciales: 'CM',
        color: 'linear-gradient(135deg, #FFCD11, #FF6B35)',
        rating: 5
    },
    2: {
        video: '/static/vid/testimonio-electrico.mp4',
        nombre: 'Roberto',
        servicio: 'Electricidad',
        iniciales: 'ML',
        color: 'linear-gradient(135deg, #FF6B35, #F97316)',
        rating: 5
    },
    3: {
        video: '/static/vid/testimonio-refri-2.mp4',
        nombre: 'María López García',
        servicio: 'Gasfitería',
        iniciales: 'RG',
        color: 'linear-gradient(135deg, #3B82F6, #1D4ED8)',
        rating: 5
    }
};

function reproducirTestimonio(id) {
    const modal = document.getElementById('videoModal');
    const video = document.getElementById('testimonioVideo');
    const userInfo = document.getElementById('modalUserInfo');
    const testimonio = testimonios[id];
    
    if (!testimonio) {
        console.error('Testimonio no encontrado:', id);
        return;
    }
    
    // Configurar video
    const source = video.querySelector('source');
    if (source) {
        source.src = testimonio.video;
        video.load();
    }
    
    // Configurar info del usuario
    userInfo.innerHTML = `
        <div class="user-info">
            <div class="avatar-placeholder" style="background: ${testimonio.color};">${testimonio.iniciales}</div>
            <div class="user-details">
                <h4 class="user-name">${testimonio.nombre}</h4>
                <span class="service-tag">
                    <i class="fas fa-check-circle"></i> ${testimonio.servicio}
                </span>
            </div>
        </div>
        <div class="rating-container">
            <div class="stars">
                ${'<i class="fas fa-star"></i>'.repeat(testimonio.rating)}
            </div>
            <span class="rating-text">${testimonio.rating}.0</span>
        </div>
    `;
    
    // Mostrar modal
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
    
    // Intentar reproducir
    video.play().catch(e => console.log('Autoplay bloqueado:', e));
}

function cerrarModalVideo() {
    const modal = document.getElementById('videoModal');
    const video = document.getElementById('testimonioVideo');
    
    if (video) {
        video.pause();
        video.currentTime = 0;
    }
    
    modal.classList.remove('show');
    document.body.style.overflow = '';
}

// Cerrar modal con Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        cerrarModalVideo();
    }
});

console.log('✅ Testimonios JS cargado');