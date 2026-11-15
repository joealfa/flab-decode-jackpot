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

function formatNumber(num) {
    return new Intl.NumberFormat().format(num);
}

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

const observerOptions = {
    threshold: 0.05,  // Reduced threshold for better performance
    rootMargin: '0px 0px -30px 0px'
};

let observerCallback = (entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
            observer.unobserve(entry.target);
        }
    });
};

const observer = new IntersectionObserver(observerCallback, observerOptions);

document.addEventListener('DOMContentLoaded', () => {
    requestAnimationFrame(() => {
        const elements = document.querySelectorAll('.card, .feature-card, .prediction-item');
        elements.forEach(el => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            el.style.transition = 'opacity 0.3s ease-out, transform 0.3s ease-out';
            el.style.willChange = 'opacity, transform';  // Hint browser for optimization
            observer.observe(el);
        });
    });
});

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

/** In-app toasts and optional desktop notifications for background jobs. */
const JobNotifier = (() => {
    function container() {
        let element = document.getElementById('aiToastContainer');
        if (!element) {
            element = document.createElement('div');
            element.id = 'aiToastContainer';
            element.className = 'ai-toast-container';
            element.setAttribute('aria-live', 'polite');
            document.body.appendChild(element);
        }
        return element;
    }

    function toast({ title, message, type = 'success', icon = 'fa-robot', actionLabel, actionIcon = 'fa-eye', onAction }) {
        const element = document.createElement('div');
        element.className = `ai-toast ${type}`;
        element.setAttribute('role', 'status');
        element.innerHTML = `
            <i class="fas ${type === 'error' ? 'fa-exclamation-triangle' : icon} ai-toast-icon"></i>
            <div class="ai-toast-body">
                <strong>${escapeHtml(title)}</strong>
                <p>${escapeHtml(message)}</p>
                ${onAction ? `<button type="button" class="btn btn-primary btn-sm ai-toast-view"><i class="fas ${actionIcon}"></i> ${escapeHtml(actionLabel)}</button>` : ''}
            </div>
            <button type="button" class="ai-toast-close" aria-label="Dismiss">&times;</button>
        `;
        element.querySelector('.ai-toast-close').addEventListener('click', () => element.remove());
        const action = element.querySelector('.ai-toast-view');
        if (action) {
            action.addEventListener('click', () => {
                element.remove();
                onAction();
            });
        }
        container().appendChild(element);
    }

    // Desktop notifications only fire while the tab is hidden; the toast covers the visible case.
    function desktop(title, body, tag, onClick) {
        if (!('Notification' in window) || Notification.permission !== 'granted' || !document.hidden) return;
        const notification = new Notification(`Fortune Lab: ${title}`, {
            body,
            tag,
            icon: '/static/favicon.svg'
        });
        notification.onclick = () => {
            window.focus();
            if (onClick) onClick();
            notification.close();
        };
    }

    function canRequestPermission() {
        return 'Notification' in window && Notification.permission === 'default';
    }

    async function requestPermission() {
        if (!('Notification' in window)) return 'unsupported';
        return Notification.requestPermission();
    }

    return { container, toast, desktop, canRequestPermission, requestPermission };
})();

/**
 * Tracks background AI analyses on every page. Pending runs are stored in
 * localStorage so the user is still notified after navigating or reloading.
 */
const AIJobs = (() => {
    const STORAGE_KEY = 'fortuneLab.aiJobs';
    const POLL_MS = 8000;
    let timer = null;
    let polling = false;

    function load() {
        try {
            const jobs = JSON.parse(localStorage.getItem(STORAGE_KEY));
            return Array.isArray(jobs) ? jobs : [];
        } catch {
            return [];
        }
    }

    function save(jobs) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(jobs));
        renderIndicator(jobs);
    }

    function track(job) {
        if (!job || !job.filename) return;
        const jobs = load();
        if (!jobs.some(item => item.filename === job.filename)) {
            jobs.push({ filename: job.filename, game_type: job.game_type || '' });
            save(jobs);
        }
        start();
    }

    // Returns true only for the caller that removed the job, so a result is
    // announced once even when several tabs are polling.
    function untrack(filename) {
        const jobs = load();
        const remaining = jobs.filter(item => item.filename !== filename);
        if (remaining.length === jobs.length) return false;
        save(remaining);
        return true;
    }

    async function poll() {
        if (polling) return;
        polling = true;
        try {
            const jobs = load();
            renderIndicator(jobs);
            if (jobs.length === 0) {
                stop();
                return;
            }
            for (const job of jobs) {
                let record;
                try {
                    const response = await fetch(`/api/ai-analysis/${encodeURIComponent(job.filename)}`);
                    if (response.status === 404) {
                        untrack(job.filename);
                        continue;
                    }
                    const result = await response.json();
                    if (!result.success) continue;
                    record = result.analysis;
                } catch {
                    continue;
                }
                document.dispatchEvent(new CustomEvent('ai-job-updated', { detail: record }));
                if ((record.status === 'completed' || record.status === 'failed') && untrack(job.filename)) {
                    notify(record);
                }
            }
        } finally {
            polling = false;
        }
    }

    function start() {
        renderIndicator(load());
        if (!timer) {
            timer = setInterval(poll, POLL_MS);
        }
    }

    function stop() {
        clearInterval(timer);
        timer = null;
    }

    function open(filename) {
        if (typeof viewAIAnalysis === 'function') {
            viewAIAnalysis(filename);
        } else {
            window.location.href = '/?ai=' + encodeURIComponent(filename);
        }
    }

    function notify(record) {
        const done = record.status === 'completed';
        const game = record.game_type || 'lottery report';
        const title = done ? 'AI analysis ready' : 'AI analysis failed';
        const message = done
            ? `The AI analysis for ${game} is ready and saved to history.`
            : `${game}: ${record.error || 'The AI analysis did not finish.'}`;
        const onOpen = done ? () => open(record.filename) : null;

        JobNotifier.toast({
            title,
            message,
            type: done ? 'success' : 'error',
            icon: 'fa-robot',
            actionLabel: 'View',
            onAction: onOpen
        });
        JobNotifier.desktop(title, message, record.filename, onOpen);
    }

    function renderIndicator(jobs) {
        let indicator = document.getElementById('aiJobIndicator');
        if (jobs.length === 0) {
            if (indicator) indicator.remove();
            return;
        }
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'aiJobIndicator';
            indicator.className = 'ai-job-indicator';
            indicator.title = 'You will be notified when the analysis is ready.';
            JobNotifier.container().prepend(indicator);
        }
        const label = jobs.length === 1 ? '1 AI analysis running' : `${jobs.length} AI analyses running`;
        indicator.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${escapeHtml(label)}`;
    }

    window.addEventListener('storage', event => {
        if (event.key === STORAGE_KEY) start();
    });
    document.addEventListener('DOMContentLoaded', () => {
        if (load().length > 0) {
            start();
            poll();
        }
    });

    return {
        track,
        untrack,
        canRequestNotifications: JobNotifier.canRequestPermission,
        requestNotifications: JobNotifier.requestPermission
    };
})();

/**
 * Tracks background data-loading (scrape) tasks on every page so the user can
 * keep using the app. Shows a floating progress card, hidden while the page's
 * own progress bar ([data-scrape-inline]) is on screen, and notifies on finish.
 */
const ScrapeJobs = (() => {
    const STORAGE_KEY = 'fortuneLab.scrapeJobs';
    const POLL_MS = 2000;
    const watching = new Map();
    let timer = null;
    let polling = false;
    let inlineVisible = false;

    function load() {
        try {
            const jobs = JSON.parse(localStorage.getItem(STORAGE_KEY));
            return Array.isArray(jobs) ? jobs.filter(job => job && job.task_id) : [];
        } catch {
            return [];
        }
    }

    function save(jobs) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(jobs));
    }

    function track(job) {
        if (!job || !job.task_id) return;
        const entry = {
            task_id: job.task_id,
            game_type: job.game_type || '',
            start_date: job.start_date || '',
            end_date: job.end_date || ''
        };
        const jobs = load();
        if (!jobs.some(item => item.task_id === entry.task_id)) {
            jobs.push(entry);
            save(jobs);
        }
        watching.set(entry.task_id, { job: entry, progress: null });
        render();
        start();
    }

    // Returns true only for the caller that removed the job, so a result is
    // announced once even when several tabs are polling.
    function untrack(taskId) {
        const jobs = load();
        const remaining = jobs.filter(item => item.task_id !== taskId);
        if (remaining.length === jobs.length) return false;
        save(remaining);
        return true;
    }

    function list() {
        return load();
    }

    function syncWatching() {
        for (const job of load()) {
            if (!watching.has(job.task_id)) {
                watching.set(job.task_id, { job, progress: null });
            }
        }
    }

    function finish(taskId, job, progress) {
        watching.delete(taskId);
        document.dispatchEvent(new CustomEvent('scrape-job-updated', { detail: { job, progress } }));
        if (untrack(taskId)) notify(job, progress);
    }

    async function poll() {
        if (polling) return;
        polling = true;
        try {
            syncWatching();
            if (watching.size === 0) {
                stop();
                return;
            }
            for (const [taskId, state] of [...watching]) {
                let response;
                try {
                    response = await fetch(`/api/progress/${encodeURIComponent(taskId)}`);
                } catch {
                    continue;
                }
                if (response.status === 404) {
                    finish(taskId, state.job, null);
                    continue;
                }
                let result;
                try {
                    result = await response.json();
                } catch {
                    continue;
                }
                if (!result.success || !result.progress) continue;
                const progress = result.progress;
                if (progress.status === 'completed' || progress.status === 'failed') {
                    finish(taskId, state.job, progress);
                } else {
                    state.progress = progress;
                    document.dispatchEvent(new CustomEvent('scrape-job-updated', { detail: { job: state.job, progress } }));
                }
            }
        } finally {
            polling = false;
            render();
        }
    }

    function start() {
        syncWatching();
        render();
        if (!timer && watching.size > 0) {
            timer = setInterval(poll, POLL_MS);
            poll();
        }
    }

    function stop() {
        clearInterval(timer);
        timer = null;
    }

    function analyze(filename) {
        if (typeof openAnalysisModal === 'function') {
            openAnalysisModal(filename);
        } else {
            window.location.href = '/?analyze=' + encodeURIComponent(filename);
        }
    }

    function notify(job, progress) {
        const game = job.game_type || 'Lottery';
        let title;
        let message;
        let type = 'success';
        let onAnalyze = null;

        if (progress && progress.status === 'completed') {
            const data = progress.result || {};
            title = 'Lottery data ready';
            message = data.total_draws !== undefined
                ? `${data.cached ? 'Loaded' : 'Scraped'} ${data.total_draws} ${game} draws${data.cached ? ' from cache' : ''}.`
                : `${game}: ${progress.message || 'Data loading finished.'}`;
            if (data.filename) onAnalyze = () => analyze(data.filename);
        } else if (progress) {
            title = 'Data loading failed';
            message = `${game}: ${progress.message || 'The data could not be loaded.'}`;
            type = 'error';
        } else {
            title = 'Data loading status unavailable';
            message = `${game}: the task already finished or was interrupted. Check Saved Results.`;
            type = 'error';
        }

        // The home page shows the result inline when its progress bar is on screen.
        if (!inlineVisible || document.hidden) {
            JobNotifier.toast({
                title,
                message,
                type,
                icon: 'fa-database',
                actionLabel: 'Analyze',
                actionIcon: 'fa-chart-bar',
                onAction: onAnalyze
            });
        }
        JobNotifier.desktop(title, message, `scrape-${job.task_id}`, onAnalyze);
    }

    function render() {
        let widget = document.getElementById('scrapeJobWidget');
        if (watching.size === 0 || inlineVisible) {
            if (widget) widget.remove();
            return;
        }
        if (!widget) {
            widget = document.createElement('div');
            widget.id = 'scrapeJobWidget';
            widget.className = 'scrape-job-widget';
            widget.title = 'Loading continues in the background. You will be notified when it finishes.';
            JobNotifier.container().prepend(widget);
        }
        widget.innerHTML = [...watching.values()].map(({ job, progress }) => {
            const percentage = Math.max(0, Math.min(100, parseInt(progress?.percentage, 10) || 0));
            const message = progress?.message || 'Starting...';
            return `
                <div class="scrape-job-row">
                    <div class="scrape-job-title">
                        <span><i class="fas fa-download"></i> ${escapeHtml(job.game_type || 'Lottery data')}</span>
                        <span>${percentage}%</span>
                    </div>
                    <div class="scrape-job-bar"><div class="scrape-job-fill" style="width: ${percentage}%"></div></div>
                    <small>${escapeHtml(message)}</small>
                </div>
            `;
        }).join('');
    }

    function observeInline() {
        const inline = document.querySelector('[data-scrape-inline]');
        if (!inline || !('IntersectionObserver' in window)) return;
        new IntersectionObserver(entries => {
            inlineVisible = entries.some(entry => entry.isIntersecting);
            render();
        }).observe(inline);
    }

    window.addEventListener('storage', event => {
        if (event.key === STORAGE_KEY) start();
    });
    document.addEventListener('DOMContentLoaded', () => {
        observeInline();
        if (load().length > 0) start();
    });

    return { track, list, canRequestNotifications: JobNotifier.canRequestPermission, requestNotifications: JobNotifier.requestPermission };
})();
