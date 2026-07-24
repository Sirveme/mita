// ============================================
// VARIABLES GLOBALES
// ============================================

let insumos = [];
let categorias = [];
let marcas = [];
let currentPage = 1;
let pageSize = 20;
let totalItems = 0;
let editandoId = null;

// Filtros
let filtros = {
    search: '',
    categoria_id: null,
    marca_id: null,
    activo: null,
    stock_bajo: null
};

// ============================================
// INICIALIZACIÓN
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    cargarCategorias();
    cargarMarcas();
    cargarInsumos();
});

// ============================================
// CARGAR DATOS
// ============================================

async function cargarCategorias() {
    try {
        const response = await fetch('/api/v1/admin/insumos/categorias/listar');
        categorias = await response.json();
        
        // Llenar select en filtro
        const filterSelect = document.getElementById('filterCategoria');
        categorias.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat.id;
            option.textContent = cat.nombre;
            filterSelect.appendChild(option);
        });
        
        // Llenar select en modal
        const modalSelect = document.getElementById('categoria_id');
        modalSelect.innerHTML = '<option value="">Seleccionar...</option>';
        categorias.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat.id;
            option.textContent = cat.nombre;
            modalSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error al cargar categorías:', error);
    }
}

async function cargarMarcas() {
    try {
        const response = await fetch('/api/v1/admin/insumos/marcas/listar');
        marcas = await response.json();
        
        // Llenar select en filtro
        const filterSelect = document.getElementById('filterMarca');
        marcas.forEach(marca => {
            const option = document.createElement('option');
            option.value = marca.id;
            option.textContent = marca.nombre;
            filterSelect.appendChild(option);
        });
        
        // Llenar select en modal
        const modalSelect = document.getElementById('marca_id');
        modalSelect.innerHTML = '<option value="">Seleccionar...</option>';
        marcas.forEach(marca => {
            const option = document.createElement('option');
            option.value = marca.id;
            option.textContent = marca.nombre;
            modalSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error al cargar marcas:', error);
    }
}

async function cargarInsumos() {
    try {
        // Construir URL con parámetros
        const params = new URLSearchParams({
            page: currentPage,
            page_size: pageSize
        });
        
        if (filtros.search) params.append('search', filtros.search);
        if (filtros.categoria_id) params.append('categoria_id', filtros.categoria_id);
        if (filtros.marca_id) params.append('marca_id', filtros.marca_id);
        if (filtros.activo !== null) params.append('activo', filtros.activo);
        if (filtros.stock_bajo) params.append('stock_bajo', filtros.stock_bajo);
        
        const response = await fetch(`/api/v1/admin/insumos/?${params}`);
        const data = await response.json();
        
        insumos = data.items;
        totalItems = data.total;
        
        renderizarTabla();
        renderizarPaginacion();
        actualizarEstadisticas();
        
    } catch (error) {
        console.error('Error al cargar insumos:', error);
        document.getElementById('tableBody').innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; color: #EF4444;">
                    Error al cargar datos. Por favor, intenta de nuevo.
                </td>
            </tr>
        `;
    }
}

// ============================================
// RENDERIZAR TABLA
// ============================================

function renderizarTabla() {
    const tbody = document.getElementById('tableBody');
    
    if (insumos.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; color: rgba(255,255,255,0.6);">
                    No se encontraron insumos
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = insumos.map(insumo => {
        const stockBajo = parseFloat(insumo.stock_actual) < parseFloat(insumo.stock_minimo || 0);
        const stockBadge = stockBajo ? '<span class="badge bajo-stock">Stock Bajo</span>' : '';
        
        return `
            <tr>
                <td>${insumo.codigo_interno || '-'}</td>
                <td><strong>${insumo.nombre}</strong></td>
                <td>${insumo.categoria_nombre || '-'}</td>
                <td>${insumo.marca_nombre || '-'}</td>
                <td>
                    ${parseFloat(insumo.stock_actual).toFixed(2)}
                    ${stockBadge}
                </td>
                <td>S/ ${parseFloat(insumo.precio_publico || 0).toFixed(2)}</td>
                <td>
                    <span class="badge ${insumo.activo ? 'activo' : 'inactivo'}">
                        ${insumo.activo ? 'Activo' : 'Inactivo'}
                    </span>
                </td>
                <td>
                    <button class="btn-action edit" onclick="editarInsumo(${insumo.id})" title="Editar">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-action delete" onclick="eliminarInsumo(${insumo.id})" title="Eliminar">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

// ============================================
// PAGINACIÓN
// ============================================

function renderizarPaginacion() {
    const totalPages = Math.ceil(totalItems / pageSize);
    const pagination = document.getElementById('pagination');
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    let html = `
        <button class="page-btn" onclick="cambiarPagina(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>
            <i class="fas fa-chevron-left"></i>
        </button>
    `;
    
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
            html += `
                <button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="cambiarPagina(${i})">
                    ${i}
                </button>
            `;
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            html += '<span style="color: rgba(255,255,255,0.4);">...</span>';
        }
    }
    
    html += `
        <button class="page-btn" onclick="cambiarPagina(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>
            <i class="fas fa-chevron-right"></i>
        </button>
    `;
    
    pagination.innerHTML = html;
}

function cambiarPagina(page) {
    const totalPages = Math.ceil(totalItems / pageSize);
    if (page < 1 || page > totalPages) return;
    
    currentPage = page;
    cargarInsumos();
}

// ============================================
// ESTADÍSTICAS
// ============================================

function actualizarEstadisticas() {
    document.getElementById('statTotal').textContent = totalItems;
    
    // Calcular activos
    const activos = insumos.filter(i => i.activo).length;
    document.getElementById('statActivos').textContent = activos;
    
    // Calcular stock bajo (aproximado con los items visibles)
    const stockBajo = insumos.filter(i => 
        parseFloat(i.stock_actual) < parseFloat(i.stock_minimo || 0)
    ).length;
    document.getElementById('statStockBajo').textContent = stockBajo;
    
    // Calcular valor total (aproximado)
    const valorTotal = insumos.reduce((sum, i) => 
        sum + (parseFloat(i.stock_actual) * parseFloat(i.precio_publico || 0)), 0
    );
    document.getElementById('statValorTotal').textContent = `S/ ${valorTotal.toFixed(2)}`;
}

// ============================================
// BÚSQUEDA Y FILTROS
// ============================================

let searchTimeout;
function buscarInsumos() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        filtros.search = document.getElementById('searchInput').value;
        currentPage = 1;
        cargarInsumos();
    }, 500);
}

function aplicarFiltros() {
    const categoria = document.getElementById('filterCategoria').value;
    const marca = document.getElementById('filterMarca').value;
    const estado = document.getElementById('filterEstado').value;
    const stock = document.getElementById('filterStock').value;
    
    filtros.categoria_id = categoria || null;
    filtros.marca_id = marca || null;
    filtros.activo = estado === '' ? null : estado === 'true';
    filtros.stock_bajo = stock === 'true' ? true : null;
    
    currentPage = 1;
    cargarInsumos();
}

// ============================================
// MODAL
// ============================================

function mostrarModal(id = null) {
    editandoId = id;
    
    document.getElementById('modalTitle').textContent = id ? 'Editar Insumo' : 'Nuevo Insumo';
    document.getElementById('errorContainer').innerHTML = '';
    document.getElementById('formInsumo').reset();
    
    if (id) {
        cargarDatosInsumo(id);
    } else {
        // Valores por defecto
        document.getElementById('unidad_medida').value = 'unidad';
        document.getElementById('stock_actual').value = 0;
        document.getElementById('stock_minimo').value = 5;
        document.getElementById('stock_maximo').value = 100;
        document.getElementById('activo').checked = true;
    }
    
    document.getElementById('modalInsumo').classList.add('show');
}

function cerrarModal() {
    document.getElementById('modalInsumo').classList.remove('show');
    editandoId = null;
}

async function cargarDatosInsumo(id) {
    try {
        const response = await fetch(`/api/v1/admin/insumos/${id}`);
        const insumo = await response.json();
        
        // Llenar formulario
        document.getElementById('codigo_interno').value = insumo.codigo_interno || '';
        document.getElementById('codigo_barras').value = insumo.codigo_barras || '';
        document.getElementById('nombre').value = insumo.nombre;
        document.getElementById('descripcion').value = insumo.descripcion || '';
        document.getElementById('categoria_id').value = insumo.categoria_id || '';
        document.getElementById('marca_id').value = insumo.marca_id || '';
        document.getElementById('presentacion').value = insumo.presentacion || '';
        document.getElementById('unidad_medida').value = insumo.unidad_medida || 'unidad';
        document.getElementById('stock_actual').value = insumo.stock_actual;
        document.getElementById('stock_minimo').value = insumo.stock_minimo;
        document.getElementById('stock_maximo').value = insumo.stock_maximo;
        document.getElementById('precio_compra').value = insumo.precio_compra || '';
        document.getElementById('precio_venta').value = insumo.precio_venta || '';
        document.getElementById('precio_publico').value = insumo.precio_publico || '';
        document.getElementById('proveedor_principal').value = insumo.proveedor_principal || '';
        document.getElementById('fecha_vencimiento').value = insumo.fecha_vencimiento || '';
        document.getElementById('requiere_refrigeracion').checked = insumo.requiere_refrigeracion || false;
        document.getElementById('activo').checked = insumo.activo;
        document.getElementById('tipo_recomendacion').value = insumo.tipo_recomendacion || '';
        document.getElementById('imagen_url').value = insumo.imagen_url || '';
        
    } catch (error) {
        console.error('Error al cargar insumo:', error);
        mostrarError('Error al cargar los datos del insumo');
    }
}

// ============================================
// GUARDAR INSUMO
// ============================================

async function guardarInsumo(event) {
    event.preventDefault();
    
    const datos = {
        codigo_interno: document.getElementById('codigo_interno').value || null,
        codigo_barras: document.getElementById('codigo_barras').value || null,
        nombre: document.getElementById('nombre').value,
        descripcion: document.getElementById('descripcion').value || null,
        categoria_id: parseInt(document.getElementById('categoria_id').value) || null,
        marca_id: parseInt(document.getElementById('marca_id').value) || null,
        presentacion: document.getElementById('presentacion').value || null,
        unidad_medida: document.getElementById('unidad_medida').value,
        stock_actual: parseFloat(document.getElementById('stock_actual').value),
        stock_minimo: parseFloat(document.getElementById('stock_minimo').value),
        stock_maximo: parseFloat(document.getElementById('stock_maximo').value),
        precio_compra: parseFloat(document.getElementById('precio_compra').value) || null,
        precio_venta: parseFloat(document.getElementById('precio_venta').value) || null,
        precio_publico: parseFloat(document.getElementById('precio_publico').value) || null,
        proveedor_principal: document.getElementById('proveedor_principal').value || null,
        fecha_vencimiento: document.getElementById('fecha_vencimiento').value || null,
        requiere_refrigeracion: document.getElementById('requiere_refrigeracion').checked,
        activo: document.getElementById('activo').checked,
        tipo_recomendacion: document.getElementById('tipo_recomendacion').value || null,
        imagen_url: document.getElementById('imagen_url').value || null,
    };
    
    try {
        const url = editandoId 
            ? `/api/v1/admin/insumos/${editandoId}`
            : '/api/v1/admin/insumos/';
        
        const method = editandoId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(datos)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error al guardar');
        }
        
        cerrarModal();
        cargarInsumos();
        
        // Mostrar notificación de éxito
        alert(editandoId ? 'Insumo actualizado correctamente' : 'Insumo creado correctamente');
        
    } catch (error) {
        console.error('Error:', error);
        mostrarError(error.message);
    }
}

// ============================================
// EDITAR INSUMO
// ============================================

function editarInsumo(id) {
    mostrarModal(id);
}

// ============================================
// ELIMINAR INSUMO
// ============================================

async function eliminarInsumo(id) {
    if (!confirm('¿Estás seguro de desactivar este insumo?\n\nPodrás reactivarlo más tarde.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/v1/admin/insumos/${id}?permanente=false`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error('Error al eliminar');
        }
        
        cargarInsumos();
        alert('Insumo desactivado correctamente');
        
    } catch (error) {
        console.error('Error:', error);
        alert('Error al eliminar el insumo');
    }
}

// ============================================
// UTILIDADES
// ============================================

function mostrarError(mensaje) {
    const errorContainer = document.getElementById('errorContainer');
    errorContainer.innerHTML = `
        <div class="error-message">
            <i class="fas fa-exclamation-circle"></i>
            ${mensaje}
        </div>
    `;
}