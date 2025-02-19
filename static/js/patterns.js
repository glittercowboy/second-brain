document.addEventListener('DOMContentLoaded', function() {
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    let entriesChart = null;
    let wordsChart = null;

    // Common chart options for minimal, modern look
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: {
                type: 'time',
                time: {
                    unit: 'day',
                    displayFormats: {
                        day: 'MMM d'
                    }
                },
                grid: {
                    display: false
                },
                border: {
                    display: false
                },
                ticks: {
                    font: {
                        family: 'Courier Prime',
                        size: 11
                    },
                    color: '#999',
                    maxRotation: 0,
                    autoSkipPadding: 40
                }
            },
            y: {
                beginAtZero: true,
                grid: {
                    color: '#f9f9f9',
                    drawBorder: false,
                    lineWidth: 1
                },
                border: {
                    display: false
                },
                ticks: {
                    font: {
                        family: 'Courier Prime',
                        size: 11
                    },
                    color: '#999',
                    padding: 10,
                    maxTicksLimit: 5
                }
            }
        },
        plugins: {
            legend: {
                display: false
            },
            tooltip: {
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                titleColor: '#666',
                bodyColor: '#666',
                borderColor: '#f5f5f5',
                borderWidth: 1,
                cornerRadius: 4,
                padding: 12,
                titleFont: {
                    family: 'Courier Prime',
                    size: 12
                },
                bodyFont: {
                    family: 'Courier Prime',
                    size: 12
                },
                displayColors: false,
                callbacks: {
                    title: function(context) {
                        return new Date(context[0].parsed.x).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric'
                        });
                    }
                }
            }
        },
        elements: {
            line: {
                tension: 0.3,
                borderWidth: 1.5,
                borderColor: '#666',
                fill: {
                    target: 'origin',
                    above: 'rgba(102, 102, 102, 0.03)'
                }
            },
            point: {
                radius: 2,
                backgroundColor: '#666',
                hoverRadius: 4,
                hitRadius: 30
            }
        },
        interaction: {
            mode: 'index',
            intersect: false
        },
        animation: {
            duration: 1000,
            easing: 'easeOutQuart'
        }
    };

    // Update all charts
    function updateCharts(startDate, endDate) {
        const params = new URLSearchParams();
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);

        fetch('/api/journal_stats?' + params.toString())
            .then(response => response.json())
            .then(data => {
                // Update date inputs with first entry date if not set
                if (!startDateInput.value) {
                    startDateInput.value = data.first_entry_date;
                }
                if (!endDateInput.value) {
                    endDateInput.value = new Date().toISOString().split('T')[0];
                }

                // Entries per day chart
                const entriesCtx = document.getElementById('entriesChart').getContext('2d');
                if (entriesChart) entriesChart.destroy();
                entriesChart = new Chart(entriesCtx, {
                    type: 'line',
                    data: {
                        labels: data.dates,
                        datasets: [{
                            data: data.entries_per_day,
                            borderColor: '#666',
                            backgroundColor: '#666'
                        }]
                    },
                    options: chartOptions
                });

                // Words per entry chart
                const wordsCtx = document.getElementById('wordsChart').getContext('2d');
                if (wordsChart) wordsChart.destroy();
                wordsChart = new Chart(wordsCtx, {
                    type: 'line',
                    data: {
                        labels: data.dates,
                        datasets: [{
                            data: data.words_per_entry,
                            borderColor: '#666',
                            backgroundColor: '#666'
                        }]
                    },
                    options: chartOptions
                });
            });
    }

    // Event listeners
    startDateInput.addEventListener('change', () => {
        updateCharts(startDateInput.value, endDateInput.value);
    });

    endDateInput.addEventListener('change', () => {
        updateCharts(startDateInput.value, endDateInput.value);
    });

    // Initial load
    updateCharts();
});
