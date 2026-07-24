/* ============================================
   MITA - CATEGORÍAS DINÁMICAS (HOME)
   Rellena el slider de servicios desde la API.
   Mejora progresiva: si la API falla, se conservan las
   tarjetas de fallback renderizadas en el servidor.
   ============================================ */

document.addEventListener('DOMContentLoaded', function () {
    cargarCategoriasHome();
});

async function cargarCategoriasHome() {
    const slider = document.getElementById('sliderServicios');
    if (!slider) return;

    try {
        const res = await fetch('/api/v1/servicios/categorias');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();

        if (!data.success || !Array.isArray(data.categorias) || data.categorias.length === 0) {
            return; // Sin datos: se mantiene el fallback estático
        }

        slider.innerHTML = data.categorias.map(renderCategoriaCard).join('');

        // Reinicializar dots/scroll del slider ya con las tarjetas nuevas
        if (typeof window.initServicesSlider === 'function') {
            window.initServicesSlider();
        }
    } catch (err) {
        console.warn('⚠️ No se pudieron cargar categorías (se usa fallback):', err.message);
    }
}

function renderCategoriaCard(cat) {
    const proximamente = !!cat.proximamente;
    const color = cat.color || '#FFCD11';
    const icono = cat.icono || 'fas fa-tools';
    const descripcion = cat.descripcion || '';

    // Handler: activas → formulario genérico; próximamente → modal
    const onclick = proximamente
        ? `mostrarProximamenteCategoria('${escapeAttr(cat.nombre)}')`
        : `irACategoria('${escapeAttr(cat.codigo)}')`;

    const badge = proximamente
        ? `<span class="discount-badge badge-proximamente">Próximamente</span>`
        : `<span class="discount-badge">Desde S/50</span>`;

    return `
        <div class="service-card-modern ${proximamente ? 'card-proximamente' : ''}" onclick="${onclick}">
            <div class="card-image" style="background: linear-gradient(135deg, ${color}22, ${color}44);"></div>
            <div class="card-overlay"></div>
            ${badge}
            <div class="card-content">
                <div class="card-icon" style="color: ${color};"><i class="${icono}"></i></div>
                <h3 class="card-title">${escapeHtml(cat.nombre)}</h3>
                <p class="card-description">${escapeHtml(descripcion)}</p>
            </div>
        </div>
    `;
}

// Navegar al formulario genérico de solicitud con la categoría seleccionada
function irACategoria(codigo) {
    try { sessionStorage.setItem('mita_categoria', codigo); } catch (e) {}
    window.location.href = '/cliente/solicitar?categoria=' + encodeURIComponent(codigo);
}

function mostrarProximamenteCategoria(nombre) {
    // Reutiliza el modal "Próximamente" del home si está disponible
    if (typeof window.mostrarProximamente === 'function') {
        window.mostrarProximamente('servicios');
    } else {
        alert(nombre + ' estará disponible próximamente en MITA.');
    }
}

function escapeHtml(str) {
    return String(str == null ? '' : str)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function escapeAttr(str) {
    return String(str == null ? '' : str).replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

window.irACategoria = irACategoria;
window.mostrarProximamenteCategoria = mostrarProximamenteCategoria;

console.log('✅ Categorías dinámicas cargadas');
