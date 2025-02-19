// Configure Chart.js defaults for a minimal, modern look
Chart.defaults.font.family = "'Courier Prime', monospace";
Chart.defaults.color = '#666';
Chart.defaults.scale.grid.color = '#f5f5f5';
Chart.defaults.scale.grid.drawBorder = false;

// Common chart options
const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            display: false
        }
    },
    scales: {
        x: {
            grid: {
                display: false
            }
        },
        y: {
            beginAtZero: true,
            grid: {
                color: '#f5f5f5'
            }
        }
    },
    elements: {
        line: {
            tension: 0.4
        },
        point: {
            radius: 3
        }
    }
};

// Store chart instances to update them later
let entriesChart, wordChart, lengthChart;

// Initialize all charts when the page loads
document.addEventListener('DOMContentLoaded', () => {
    initEntriesChart();
    initWordChart();
    initLengthChart();
    
    // Set up word search input
    const wordInput = document.getElementById('wordInput');
    let debounceTimer;
    
    wordInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            updateWordChart(e.target.value);
        }, 500);
    });
});

// Helper function to format dates
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Initialize the daily entries chart
async function initEntriesChart() {
    const response = await fetch('/api/stats/daily_entries');
    const data = await response.json();
    
    const ctx = document.getElementById('entriesChart').getContext('2d');
    entriesChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => formatDate(d.date)).reverse(),
            datasets: [{
                label: 'Number of Entries',
                data: data.map(d => d.count).reverse(),
                borderColor: '#666',
                backgroundColor: 'rgba(102, 102, 102, 0.1)',
                fill: true
            }]
        },
        options: {
            ...commonOptions,
            scales: {
                ...commonOptions.scales,
                y: {
                    ...commonOptions.scales.y,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

// Initialize the word frequency chart
async function initWordChart() {
    const ctx = document.getElementById('wordChart').getContext('2d');
    wordChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Word Frequency',
                data: [],
                borderColor: '#666',
                backgroundColor: 'rgba(102, 102, 102, 0.1)',
                fill: true
            }]
        },
        options: commonOptions
    });
}

// Update the word frequency chart with new data
async function updateWordChart(word) {
    if (!word) {
        wordChart.data.labels = [];
        wordChart.data.datasets[0].data = [];
        wordChart.update();
        return;
    }
    
    const response = await fetch(`/api/stats/word_frequency?word=${encodeURIComponent(word)}`);
    const data = await response.json();
    
    wordChart.data.labels = data.map(d => formatDate(d.date)).reverse();
    wordChart.data.datasets[0].data = data.map(d => d.count).reverse();
    wordChart.update();
}

// Initialize the entry length chart
async function initLengthChart() {
    const response = await fetch('/api/stats/entry_lengths');
    const data = await response.json();
    
    const ctx = document.getElementById('lengthChart').getContext('2d');
    lengthChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => formatDate(d.date)).reverse(),
            datasets: [{
                label: 'Average Characters',
                data: data.map(d => d.length).reverse(),
                borderColor: '#666',
                backgroundColor: 'rgba(102, 102, 102, 0.1)',
                fill: true
            }]
        },
        options: commonOptions
    });
}
