// Custom JavaScript para o Sistema de Gestão de Rede

$(document).ready(function() {
    // Inicializar tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();
    
    // Inicializar popovers
    $('[data-bs-toggle="popover"]').popover();
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        $('.alert').alert('close');
    }, 5000);
    
    // Form validation enhancements
    $('form').on('submit', function(e) {
        const form = $(this);
        const requiredFields = form.find('[required]');
        let valid = true;
        
        requiredFields.each(function() {
            const field = $(this);
            if (!field.val().trim()) {
                field.addClass('is-invalid');
                valid = false;
            } else {
                field.removeClass('is-invalid');
            }
        });
        
        if (!valid) {
            e.preventDefault();
            showToast('Por favor, preencha todos os campos obrigatórios.', 'warning');
        }
    });
    
    // Remove invalid class when user starts typing
    $('input, select, textarea').on('input change', function() {
        $(this).removeClass('is-invalid');
    });
    
    // Confirmação para ações destrutivas
    $('.btn-danger, a[data-confirm]').on('click', function(e) {
        const message = $(this).data('confirm') || 'Tem certeza que deseja realizar esta ação?';
        if (!confirm(message)) {
            e.preventDefault();
            e.stopPropagation();
            return false;
        }
    });
    
    // File input label update
    $('.custom-file-input').on('change', function() {
        const fileName = $(this).val().split('\\').pop();
        $(this).next('.custom-file-label').text(fileName || 'Escolher arquivo...');
    });
    
    // Tab persistence
    $('a[data-bs-toggle="tab"]').on('click', function() {
        const tabId = $(this).attr('href');
        localStorage.setItem('activeTab', tabId);
    });
    
    const activeTab = localStorage.getItem('activeTab');
    if (activeTab) {
        $('a[href="' + activeTab + '"]').tab('show');
    }
    
    // Auto-format numbers
    $('.format-number').on('blur', function() {
        const value = $(this).val().replace(/[^\d]/g, '');
        if (value) {
            $(this).val(parseFloat(value).toLocaleString('pt-BR'));
        }
    });
    
    // Auto-format currency
    $('.format-currency').on('blur', function() {
        const value = $(this).val().replace(/[^\d]/g, '');
        if (value) {
            $(this).val('R$ ' + (parseFloat(value) / 100).toLocaleString('pt-BR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }));
        }
    });
    
    // Search with debounce
    let searchTimeout;
    $('.search-input').on('input', function() {
        clearTimeout(searchTimeout);
        const searchTerm = $(this).val();
        
        searchTimeout = setTimeout(() => {
            if (searchTerm.length >= 2 || searchTerm.length === 0) {
                $(this).closest('form').submit();
            }
        }, 500);
    });
    
    // Toggle sidebar on mobile
    $('.navbar-toggler').on('click', function() {
        $('.sidebar').toggleClass('show');
    });
    
    // Close sidebar when clicking outside on mobile
    $(document).on('click', function(e) {
        if ($(window).width() <= 768) {
            if (!$(e.target).closest('.sidebar, .navbar-toggler').length) {
                $('.sidebar').removeClass('show');
            }
        }
    });
});

// Função para mostrar toasts/notificações
function showToast(message, type = 'info') {
    // Remove existing toasts
    $('.toast-container').remove();
    
    const toast = $(`
        <div class="toast-container position-fixed bottom-0 end-0 p-3">
            <div class="toast align-items-center text-white bg-${type} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        </div>
    `);
    
    $('body').append(toast);
    $('.toast').toast('show');
    
    // Remove toast after hide
    $('.toast').on('hidden.bs.toast', function() {
        $(this).closest('.toast-container').remove();
    });
}

// Função para carregar dados via AJAX
function loadData(url, callback) {
    showLoading();
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (callback) callback(data);
        })
        .catch(error => {
            hideLoading();
            showToast('Erro ao carregar dados: ' + error, 'danger');
        });
}

// Funções para mostrar/ocultar loading
function showLoading() {
    $('body').append(`
        <div class="loading-overlay">
            <div class="loading-spinner"></div>
            <p>Carregando...</p>
        </div>
    `);
}

function hideLoading() {
    $('.loading-overlay').remove();
}

// Função para exportar dados
function exportToCSV(data, filename) {
    const csv = convertToCSV(data);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

function convertToCSV(objArray) {
    const array = typeof objArray != 'object' ? JSON.parse(objArray) : objArray;
    let str = '';
    
    // Headers
    const headers = Object.keys(array[0]);
    str += headers.join(',') + '\r\n';
    
    // Data
    for (let i = 0; i < array.length; i++) {
        let line = '';
        for (let index in array[i]) {
            if (line != '') line += ',';
            line += array[i][index];
        }
        str += line + '\r\n';
    }
    
    return str;
}

// Função para validar IP
function isValidIP(ip) {
    const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/;
    if (!ipRegex.test(ip)) return false;
    
    const parts = ip.split('.');
    for (let part of parts) {
        if (parseInt(part) > 255) return false;
    }
    
    return true;
}

// Função para validar email
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Debounce function para otimização
function debounce(func, wait) {
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

// Inicializar datepicker se existir
if ($('.datepicker').length) {
    $('.datepicker').attr('type', 'date');
}