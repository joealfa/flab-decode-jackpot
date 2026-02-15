/**
 * Fortune Lab - Main JavaScript
 */

/**
 * Escape HTML special characters to prevent XSS.
 * @param {string} str - The string to escape
 * @returns {string} The escaped string
 */
function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Utility function to format numbers
function formatNumber(num) {
    return new Intl.NumberFormat().format(num);
}

// Smooth scroll for anchors
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth'
            });
        }
    });
});

// Add animation on scroll - Optimized with debouncing
const observerOptions = {
    threshold: 0.05,  // Reduced threshold for better performance
    rootMargin: '0px 0px -30px 0px'
};

let observerCallback = (entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
            // Unobserve after animating to reduce overhead
            observer.unobserve(entry.target);
        }
    });
};

const observer = new IntersectionObserver(observerCallback, observerOptions);

// Observe all cards - use requestAnimationFrame for better performance
document.addEventListener('DOMContentLoaded', () => {
    requestAnimationFrame(() => {
        const elements = document.querySelectorAll('.card, .feature-card, .prediction-item');
        // Batch observe to reduce layout thrashing
        elements.forEach(el => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            el.style.transition = 'opacity 0.3s ease-out, transform 0.3s ease-out';
            el.style.willChange = 'opacity, transform';  // Hint browser for optimization
            observer.observe(el);
        });
    });
});

// Form validation
function validateForm(form) {
    const inputs = form.querySelectorAll('[required]');
    let isValid = true;

    inputs.forEach(input => {
        if (!input.value) {
            isValid = false;
            input.classList.add('error');
        } else {
            input.classList.remove('error');
        }
    });

    return isValid;
}

// Export functionality for analysis results
function exportToJSON(data, filename) {
    const dataStr = JSON.stringify(data, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
}

// Print functionality
function printDashboard() {
    window.print();
}

/**
 * Show a styled alert modal instead of browser alert().
 * @param {string} message - The message to display
 * @param {string} [type='info'] - Type: 'info', 'success', 'error', 'warning'
 */
function showAlert(message, type = 'info') {
    const modal = document.getElementById('alertModal');
    const icon = document.getElementById('alertModalIcon');
    const title = document.getElementById('alertModalTitle');
    const msg = document.getElementById('alertModalMessage');

    const config = {
        info:    { icon: 'fa-info-circle',        title: 'Notice' },
        success: { icon: 'fa-check-circle',       title: 'Success' },
        error:   { icon: 'fa-exclamation-circle',  title: 'Error' },
        warning: { icon: 'fa-exclamation-triangle', title: 'Warning' }
    };

    const c = config[type] || config.info;
    icon.className = 'alert-modal-icon ' + type;
    icon.innerHTML = '<i class="fas ' + c.icon + '"></i>';
    title.textContent = c.title;
    msg.textContent = message;
    modal.style.display = 'flex';

    // Focus the OK button for keyboard accessibility
    modal.querySelector('.alert-modal-btn').focus();
}

function closeAlertModal(event) {
    if (event && event.target !== event.currentTarget) return;
    document.getElementById('alertModal').style.display = 'none';
}
