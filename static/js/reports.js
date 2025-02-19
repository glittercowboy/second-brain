document.addEventListener('DOMContentLoaded', function() {
    const timeRange = document.getElementById('timeRange');
    const reportDate = document.getElementById('reportDate');
    const generateButton = document.getElementById('generateReport');
    const tabButtons = document.querySelectorAll('.tab-button');
    const reportTitle = document.getElementById('reportTitle');
    const reportDateRange = document.getElementById('reportDateRange');
    const reportContent = document.getElementById('reportContent');
    const loadingIndicator = document.querySelector('.loading-indicator');
    const lastGenerated = document.getElementById('lastGenerated');

    let currentCategory = 'work';
    let currentReport = null;

    // Set initial date to today
    reportDate.valueAsDate = new Date();

    // Format date range for display
    function formatDateRange(start, end) {
        const formatDate = (date) => {
            return date.toLocaleDateString('en-US', {
                month: 'long',
                day: 'numeric',
                year: 'numeric'
            });
        };
        return `${formatDate(start)} - ${formatDate(end)}`;
    }

    // Format relative time
    function formatRelativeTime(date) {
        const now = new Date();
        const diff = now - date;
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (minutes < 1) return 'Just now';
        if (minutes < 60) return `${minutes}m ago`;
        if (hours < 24) return `${hours}h ago`;
        if (days < 30) return `${days}d ago`;
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric'
        });
    }

    // Calculate date range based on selected time range and date
    function getDateRange(selectedDate, range) {
        const end = new Date(selectedDate);
        const start = new Date(selectedDate);

        switch(range) {
            case 'week':
                start.setDate(end.getDate() - 6); // Last 7 days
                break;
            case 'month':
                start.setMonth(end.getMonth() - 1); // Last month
                break;
            case 'year':
                start.setFullYear(end.getFullYear() - 1); // Last year
                break;
        }

        return { start, end };
    }

    // Check if a report exists
    async function checkExistingReport() {
        const dateRange = getDateRange(reportDate.valueAsDate, timeRange.value);
        const params = new URLSearchParams({
            start_date: dateRange.start.toISOString().split('T')[0],
            end_date: dateRange.end.toISOString().split('T')[0],
            category: currentCategory,
            time_range: timeRange.value
        });

        try {
            const response = await fetch('/api/get_report?' + params.toString());
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error checking report:', error);
            return null;
        }
    }

    // Update report display
    async function updateReport(forceGenerate = false) {
        loadingIndicator.classList.remove('hidden');
        
        const dateRange = getDateRange(reportDate.valueAsDate, timeRange.value);
        
        try {
            let report;
            if (!forceGenerate) {
                report = await checkExistingReport();
            }

            if (!report || forceGenerate) {
                const params = new URLSearchParams({
                    start_date: dateRange.start.toISOString().split('T')[0],
                    end_date: dateRange.end.toISOString().split('T')[0],
                    category: currentCategory,
                    time_range: timeRange.value
                });

                const response = await fetch('/api/generate_report?' + params.toString());
                report = await response.json();
            }

            // Update title and date range
            reportTitle.textContent = `${currentCategory.charAt(0).toUpperCase() + currentCategory.slice(1)} Report`;
            reportDateRange.textContent = formatDateRange(dateRange.start, dateRange.end);
            
            if (report.generated_at) {
                lastGenerated.textContent = `Generated ${formatRelativeTime(new Date(report.generated_at))}`;
            }

            // Update content
            reportContent.innerHTML = report.content;
            currentReport = report;

        } catch (error) {
            console.error('Error updating report:', error);
            reportContent.innerHTML = '<p class="error">Error generating report. Please try again.</p>';
        } finally {
            loadingIndicator.classList.add('hidden');
        }
    }

    // Event listeners
    timeRange.addEventListener('change', () => updateReport(false));
    reportDate.addEventListener('change', () => updateReport(false));
    generateButton.addEventListener('click', () => updateReport(true));

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Update active tab
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');

            // Update category and refresh report
            currentCategory = button.dataset.category;
            updateReport(false);
        });
    });

    // Initial load
    updateReport(false);
});
