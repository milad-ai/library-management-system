// Persian Date Converter
function toPersianDate(dateString) {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    const options = {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        calendar: 'persian',
        numberingSystem: 'arab'
    };
    
    return new Intl.DateTimeFormat('fa-IR', options).format(date);
}

// Format Numbers with Persian Digits
function toPersianDigits(number) {
    if (!number && number !== 0) return '';
    
    const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
    return number.toString().replace(/\d/g, digit => persianDigits[digit]);
}

// Format Phone Number
function formatPhoneNumber(phone) {
    if (!phone) return '';
    
    // Remove non-digit characters
    const cleaned = phone.replace(/\D/g, '');
    
    // Format: ۰۹۱۲-۳۴۵-۶۷۸۹
    const match = cleaned.match(/^(\d{4})(\d{3})(\d{4})$/);
    if (match) {
        return `${toPersianDigits(match[1])}-${toPersianDigits(match[2])}-${toPersianDigits(match[3])}`;
    }
    
    return phone;
}

// Logout confirmation
function confirmLogout() {
    return confirm('آیا مطمئن هستید که می‌خواهید از سیستم خارج شوید؟');
}

// Auto-focus on first input in forms
document.addEventListener('DOMContentLoaded', function() {
    // Focus on first input in forms
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        const firstInput = form.querySelector('input[type="text"], input[type="password"], input[type="email"], input[type="number"]');
        if (firstInput && !firstInput.disabled && !firstInput.hidden) {
            firstInput.focus();
        }
    });
    
    // Convert dates to Persian
    document.querySelectorAll('.persian-date').forEach(element => {
        const dateString = element.textContent || element.getAttribute('data-date');
        if (dateString) {
            element.textContent = toPersianDate(dateString);
        }
    });
    
    // Convert numbers to Persian digits
    document.querySelectorAll('.persian-digits').forEach(element => {
        const number = element.textContent;
        element.textContent = toPersianDigits(number);
    });
    
    // Format phone numbers
    document.querySelectorAll('.phone-number').forEach(element => {
        const phone = element.textContent;
        element.textContent = formatPhoneNumber(phone);
    });
    
    // Confirm before delete
    document.querySelectorAll('.confirm-delete').forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('آیا مطمئن هستید؟ این عمل قابل بازگشت نیست.')) {
                e.preventDefault();
            }
        });
    });
    
    // Confirm logout
    const logoutLinks = document.querySelectorAll('a[href*="logout"]');
    logoutLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            if (!confirmLogout()) {
                e.preventDefault();
            }
        });
    });
    
    // Auto-calculate due date for borrowing
    const borrowDaysInput = document.getElementById('borrow-days');
    const dueDateDisplay = document.getElementById('due-date-display');
    
    if (borrowDaysInput && dueDateDisplay) {
        function updateDueDate() {
            const days = parseInt(borrowDaysInput.value) || 14;
            const today = new Date();
            const dueDate = new Date(today.getTime() + (days * 24 * 60 * 60 * 1000));
            
            const options = {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                calendar: 'persian'
            };
            
            dueDateDisplay.textContent = new Intl.DateTimeFormat('fa-IR', options).format(dueDate);
        }
        
        borrowDaysInput.addEventListener('input', updateDueDate);
        updateDueDate();
    }
    
    // Search form auto-submit
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.form.submit();
            }, 500);
        });
    }
    
    // Copy to clipboard
    document.querySelectorAll('.copy-btn').forEach(button => {
        button.addEventListener('click', function() {
            const textToCopy = this.getAttribute('data-copy');
            navigator.clipboard.writeText(textToCopy).then(() => {
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="bi bi-check"></i> کپی شد';
                this.classList.remove('btn-outline-secondary');
                this.classList.add('btn-success');
                
                setTimeout(() => {
                    this.innerHTML = originalText;
                    this.classList.remove('btn-success');
                    this.classList.add('btn-outline-secondary');
                }, 2000);
            });
        });
    });
    
    // Print functionality
    document.querySelectorAll('.print-btn').forEach(button => {
        button.addEventListener('click', function() {
            window.print();
        });
    });
    
    // Auto-refresh stats every 60 seconds
    if (window.location.pathname === '/dashboard') {
        setInterval(() => {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    // Update stats on dashboard
                    document.querySelectorAll('.stat-total-books').forEach(el => {
                        el.textContent = toPersianDigits(data.total_books);
                    });
                    document.querySelectorAll('.stat-total-members').forEach(el => {
                        el.textContent = toPersianDigits(data.total_members);
                    });
                    document.querySelectorAll('.stat-total-borrowed').forEach(el => {
                        el.textContent = toPersianDigits(data.total_borrowed);
                    });
                    document.querySelectorAll('.stat-overdue').forEach(el => {
                        el.textContent = toPersianDigits(data.overdue_books);
                    });
                })
                .catch(error => console.error('Error fetching stats:', error));
        }, 60000);
    }
});

// Toast Notification
function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.id = toastId;
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="bi ${type === 'success' ? 'bi-check-circle' : 'bi-exclamation-circle'} me-2"></i>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '1055';
    document.body.appendChild(container);
    return container;
}

// Export functions to global scope
window.toPersianDate = toPersianDate;
window.toPersianDigits = toPersianDigits;
window.formatPhoneNumber = formatPhoneNumber;
window.showToast = showToast;
window.confirmLogout = confirmLogout;
