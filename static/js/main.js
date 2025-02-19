let page = 1;
const entriesPerPage = 10;
let loading = false;
let currentCategory = 'all';
let searchQuery = '';
let currentEditId = null;
let currentDeleteId = null;
let hasMoreEntries = true;  // New flag to track if there are more entries

// Initialize the page
document.addEventListener('DOMContentLoaded', async () => {
    await loadCategories();
    await loadEntries();
    setupInfiniteScroll();
    setupSearch();
});

// Load categories and create tabs
async function loadCategories() {
    const response = await fetch('/api/categories');
    const categories = await response.json();
    
    const nav = document.querySelector('.categories');
    nav.innerHTML = `<span class="category-tab active" data-category="all">All</span>`;
    
    categories.forEach(category => {
        nav.innerHTML += `<span class="category-tab" data-category="${category}">${category}</span>`;
    });

    // Add click handlers for category tabs
    document.querySelectorAll('.category-tab').forEach(tab => {
        tab.addEventListener('click', async (e) => {
            document.querySelectorAll('.category-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentCategory = tab.dataset.category;
            resetEntriesState();
            await loadEntries();
        });
    });
}

// Load entries with infinite scroll
async function loadEntries() {
    if (loading || !hasMoreEntries) return;
    
    loading = true;
    const loadingSpinner = document.getElementById('loadingSpinner');
    loadingSpinner.style.display = 'block';
    loadingSpinner.textContent = 'Loading more entries...';
    
    const params = new URLSearchParams({
        page: page,
        per_page: entriesPerPage,
        category: currentCategory,
        search: searchQuery
    });

    try {
        const response = await fetch(`/api/entries?${params}`);
        const entries = await response.json();
        
        if (entries.length > 0) {
            const container = document.getElementById('journalEntries');
            
            entries.forEach(entry => {
                const categories = entry.category ? entry.category.split(',').map(c => c.trim()) : [];
                const keywords = entry.keywords ? entry.keywords.split(',').map(k => k.trim()) : [];
                
                const entryHtml = `
                    <article class="entry" data-entry-id="${entry.id}">
                        <div class="entry-date">${formatDate(entry.date)}</div>
                        <div class="entry-content">${highlightSearchTerms(entry.content)}</div>
                        <div class="entry-footer">
                            <div class="entry-tags">
                                ${categories.map(cat => `<span class="entry-tag">${cat}</span>`).join('')}
                            </div>
                            ${keywords.length > 0 ? `
                                <div class="entry-keywords">
                                    Keywords: ${keywords.join(', ')}
                                </div>
                            ` : ''}
                        </div>
                        <div class="entry-actions">
                            <button class="entry-action-btn" onclick="editEntry(${entry.id})">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="entry-action-btn" onclick="deleteEntry(${entry.id})">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </article>
                `;
                container.innerHTML += entryHtml;
            });
            
            page++;
            
            // If we got fewer entries than requested, we've reached the end
            if (entries.length < entriesPerPage) {
                hasMoreEntries = false;
                loadingSpinner.textContent = 'No more entries';
            }
        } else {
            hasMoreEntries = false;
            loadingSpinner.textContent = 'No more entries';
        }
    } catch (error) {
        console.error('Error loading entries:', error);
        loadingSpinner.textContent = 'Error loading entries';
    } finally {
        loading = false;
    }
}

// Reset entries loading state
function resetEntriesState() {
    page = 1;
    hasMoreEntries = true;
    document.getElementById('journalEntries').innerHTML = '';
    document.getElementById('loadingSpinner').style.display = 'none';
}

// Setup infinite scroll
function setupInfiniteScroll() {
    let scrollTimeout;
    window.addEventListener('scroll', () => {
        if (scrollTimeout) {
            clearTimeout(scrollTimeout);
        }
        
        scrollTimeout = setTimeout(() => {
            if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 1000) {
                loadEntries();
            }
        }, 100);  // Debounce scroll events
    });
}

// Setup search functionality
function setupSearch() {
    const searchInput = document.getElementById('searchInput');
    let debounceTimeout;

    searchInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(async () => {
            searchQuery = e.target.value;
            resetEntriesState();
            await loadEntries();
        }, 300);
    });
}

// Edit functionality
function editEntry(id) {
    currentEditId = id;
    const entry = document.querySelector(`[data-entry-id="${id}"]`);
    const content = entry.querySelector('.entry-content').textContent;
    document.getElementById('editContent').value = content;
    document.getElementById('editModal').style.display = 'block';
}

function closeEditModal() {
    document.getElementById('editModal').style.display = 'none';
    currentEditId = null;
}

async function saveEdit() {
    const content = document.getElementById('editContent').value;
    try {
        const response = await fetch(`/api/entries/${currentEditId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ content })
        });
        
        if (response.ok) {
            closeEditModal();
            resetEntriesState();
            await loadEntries();
        }
    } catch (error) {
        console.error('Error updating entry:', error);
    }
}

// Delete functionality
function deleteEntry(id) {
    currentDeleteId = id;
    document.getElementById('deleteModal').style.display = 'block';
}

function closeDeleteModal() {
    document.getElementById('deleteModal').style.display = 'none';
    currentDeleteId = null;
}

async function confirmDelete() {
    try {
        const response = await fetch(`/api/entries/${currentDeleteId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            closeDeleteModal();
            resetEntriesState();
            await loadEntries();
        }
    } catch (error) {
        console.error('Error deleting entry:', error);
    }
}

// Helper function to format dates
function formatDate(dateString) {
    const options = { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    return new Date(dateString).toLocaleDateString('en-US', options);
}

// Helper function to highlight search terms
function highlightSearchTerms(content) {
    if (!searchQuery) return content;
    
    const escapedQuery = searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${escapedQuery})`, 'gi');
    return content.replace(regex, '<span class="highlight">$1</span>');
}
