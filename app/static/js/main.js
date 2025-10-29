/**
 * Fortune Lab - Main JavaScript
 */

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

// Console welcome message
console.log('%cFortune Lab', 'font-size: 24px; font-weight: bold; color: #6366f1;');
console.log('%cDecoding the Jackpot with Data Science', 'font-size: 14px; color: #64748b;');
