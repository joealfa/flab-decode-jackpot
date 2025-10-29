/**
 * Chart Optimizer - Lazy load charts for better performance
 * Only initialize charts when they become visible in the viewport
 */

// Track which charts have been initialized
window.initializedCharts = new Set();

// Lazy chart initializer using IntersectionObserver
window.lazyChartObserver = null;

/**
 * Initialize charts only when they enter the viewport
 */
window.initializeLazyCharts = function() {
    // Create observer if not exists
    if (!window.lazyChartObserver) {
        window.lazyChartObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting && entry.target.dataset.chartId) {
                    const chartId = entry.target.dataset.chartId;
                    
                    // Initialize this specific chart if not already done
                    if (!window.initializedCharts.has(chartId)) {
                        requestAnimationFrame(() => {
                            initializeSpecificChart(chartId);
                            window.initializedCharts.add(chartId);
                        });
                        
                        // Stop observing this chart
                        window.lazyChartObserver.unobserve(entry.target);
                    }
                }
            });
        }, {
            rootMargin: '50px',  // Load charts slightly before they come into view
            threshold: 0.01
        });
    }

    // Observe all chart canvases
    document.querySelectorAll('canvas[data-chart-id]').forEach(canvas => {
        window.lazyChartObserver.observe(canvas);
    });
};

/**
 * Initialize a specific chart by ID
 */
window.initializeSpecificChart = function(chartId) {
    if (!chartData || !window.Chart) return;

    const canvas = document.getElementById(chartId);
    if (!canvas) return;

    // Check if canvas is actually visible
    if (canvas.offsetWidth === 0 || canvas.offsetHeight === 0) return;

    try {
        switch(chartId) {
            case 'frequencyChart':
                if (chartData.number_frequency) {
                    chartInstances.frequencyChart = new Chart(canvas, {
                        type: 'bar',
                        data: {
                            labels: chartData.number_frequency.labels,
                            datasets: [{
                                label: 'Frequency',
                                data: chartData.number_frequency.values,
                                backgroundColor: 'rgba(99, 102, 241, 0.8)',
                                borderColor: 'rgba(99, 102, 241, 1)',
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { display: false }
                            },
                            scales: {
                                y: { beginAtZero: true }
                            },
                            animation: {
                                duration: 500  // Faster animation
                            }
                        }
                    });
                }
                break;

            case 'sumChart':
                if (chartData.sum_distribution) {
                    chartInstances.sumChart = new Chart(canvas, {
                        type: 'line',
                        data: {
                            labels: chartData.sum_distribution.labels,
                            datasets: [{
                                label: 'Frequency',
                                data: chartData.sum_distribution.values,
                                backgroundColor: 'rgba(16, 185, 129, 0.2)',
                                borderColor: 'rgba(16, 185, 129, 1)',
                                borderWidth: 2,
                                fill: true,
                                tension: 0.4
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { display: false }
                            },
                            scales: {
                                y: { beginAtZero: true }
                            },
                            animation: {
                                duration: 500
                            }
                        }
                    });
                }
                break;

            case 'evenOddChart':
                if (chartData.even_odd_patterns) {
                    chartInstances.evenOddChart = new Chart(canvas, {
                        type: 'pie',
                        data: {
                            labels: chartData.even_odd_patterns.labels,
                            datasets: [{
                                data: chartData.even_odd_patterns.values,
                                backgroundColor: [
                                    'rgba(239, 68, 68, 0.8)',
                                    'rgba(245, 158, 11, 0.8)',
                                    'rgba(16, 185, 129, 0.8)',
                                    'rgba(99, 102, 241, 0.8)',
                                    'rgba(139, 92, 246, 0.8)'
                                ]
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            animation: {
                                duration: 500
                            }
                        }
                    });
                }
                break;

            case 'dayChart':
                if (chartData.day_distribution) {
                    chartInstances.dayChart = new Chart(canvas, {
                        type: 'bar',
                        data: {
                            labels: chartData.day_distribution.labels,
                            datasets: [{
                                label: 'Number of Draws',
                                data: chartData.day_distribution.values,
                                backgroundColor: 'rgba(139, 92, 246, 0.8)',
                                borderColor: 'rgba(139, 92, 246, 1)',
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { display: false }
                            },
                            scales: {
                                y: { beginAtZero: true }
                            },
                            animation: {
                                duration: 500
                            }
                        }
                    });
                }
                break;

            case 'heatmapMonth':
                if (chartData.heatmap && chartData.heatmap.by_month) {
                    chartInstances.heatmapMonth = createHeatmap(chartId, chartData.heatmap.by_month);
                }
                break;

            case 'heatmapYear':
                if (chartData.heatmap && chartData.heatmap.by_year) {
                    chartInstances.heatmapYear = createHeatmap(chartId, chartData.heatmap.by_year);
                }
                break;

            case 'heatmapDay':
                if (chartData.heatmap && chartData.heatmap.by_day) {
                    chartInstances.heatmapDay = createHeatmap(chartId, chartData.heatmap.by_day);
                }
                break;

            case 'trendTopNumbers':
                if (chartData.trends && chartData.trends.top_numbers_over_time) {
                    chartInstances.trendTopNumbers = new Chart(canvas, {
                        type: 'line',
                        data: {
                            labels: chartData.trends.top_numbers_over_time.labels,
                            datasets: chartData.trends.top_numbers_over_time.datasets.map((dataset, idx) => ({
                                label: dataset.label,
                                data: dataset.data,
                                borderColor: getColorForIndex(idx),
                                backgroundColor: getColorForIndex(idx, 0.1),
                                borderWidth: 2,
                                fill: false,
                                tension: 0.1
                            }))
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: true,
                            plugins: {
                                legend: { display: true, position: 'top' }
                            },
                            scales: {
                                y: { beginAtZero: true }
                            },
                            animation: {
                                duration: 500
                            }
                        }
                    });
                }
                break;

            case 'trendAvgSum':
                if (chartData.trends && chartData.trends.average_sum_trend) {
                    chartInstances.trendAvgSum = new Chart(canvas, {
                        type: 'line',
                        data: {
                            labels: chartData.trends.average_sum_trend.labels,
                            datasets: [{
                                label: 'Average Sum',
                                data: chartData.trends.average_sum_trend.data,
                                borderColor: 'rgba(99, 102, 241, 1)',
                                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                                borderWidth: 2,
                                fill: true,
                                tension: 0.4
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: true,
                            plugins: {
                                legend: { display: false }
                            },
                            scales: {
                                y: { beginAtZero: false }
                            },
                            animation: {
                                duration: 500
                            }
                        }
                    });
                }
                break;

            case 'trendEvenOdd':
                if (chartData.trends && chartData.trends.even_odd_ratio_trend) {
                    chartInstances.trendEvenOdd = new Chart(canvas, {
                        type: 'line',
                        data: {
                            labels: chartData.trends.even_odd_ratio_trend.labels,
                            datasets: [{
                                label: 'Even Number Ratio',
                                data: chartData.trends.even_odd_ratio_trend.data,
                                borderColor: 'rgba(245, 158, 11, 1)',
                                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                                borderWidth: 2,
                                fill: true,
                                tension: 0.4
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: true,
                            plugins: {
                                legend: { display: false }
                            },
                            scales: {
                                y: {
                                    beginAtZero: false,
                                    max: 1,
                                    ticks: {
                                        callback: function(value) {
                                            return (value * 100).toFixed(0) + '%';
                                        }
                                    }
                                }
                            },
                            animation: {
                                duration: 500
                            }
                        }
                    });
                }
                break;

            case 'trendConsistency':
                if (chartData.trends && chartData.trends.consistency_trend) {
                    chartInstances.trendConsistency = new Chart(canvas, {
                        type: 'line',
                        data: {
                            labels: chartData.trends.consistency_trend.labels,
                            datasets: [{
                                label: 'Consistency Score',
                                data: chartData.trends.consistency_trend.data,
                                borderColor: 'rgba(16, 185, 129, 1)',
                                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                                borderWidth: 2,
                                fill: true,
                                tension: 0.3
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: true,
                            plugins: {
                                legend: { display: false }
                            },
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    max: 1
                                }
                            },
                            animation: {
                                duration: 500
                            }
                        }
                    });
                }
                break;
        }
    } catch (error) {
        console.error(`Error initializing chart ${chartId}:`, error);
    }
};

/**
 * Debounce function to limit how often a function can be called
 */
window.debounce = function(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};
