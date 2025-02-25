import { initWebSocket } from './js/modules/websocket.js';
import { createNewsElement, formatTimeAgo, initInfiniteScroll, loadInitialNews, setActiveTagFilter } from './js/modules/news.js';
import { initTheme } from './js/modules/theme.js';
import { loadTags, toggleTagFilters, getActiveTags } from './js/modules/tags.js';
import { createScrollToTopButton, updateScrollToTopButtonVisibility, setView, setLoading, addLoadingItem } from './js/modules/ui-utils.js';
import { loadCountryData } from './js/modules/countries.js';

let lastUpdate = new Date();
const updateInterval = 30000; // 30 seconds

// Make functions globally available for WebSocket handler
window.handleNewsUpdate = handleNewsUpdate;
window.updateNews = updateNews;
window.toggleTag = toggleTag;

// Function to toggle tag filtering
function toggleTag(tag) {
    // Store current scroll position
    const scrollPosition = window.scrollY;
    
    // Toggle the tag in the UI
    const tagElements = document.querySelectorAll(`.tag[data-tag="${tag}"]`);
    const isActive = [...tagElements].some(el => el.classList.contains('active'));
    
    tagElements.forEach(element => {
        element.classList.toggle('active', !isActive);
    });
    
    // Update the active tags filter
    const activeTags = getActiveTags();
    const tagParam = activeTags.length > 0 ? `?tags=${activeTags.join(',')}` : '';
    
    // Reset and load news with the updated tag filter
    setActiveTagFilter(tagParam);
    
    // Restore scroll position after a slight delay
    setTimeout(() => {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }, 100);
}

async function handleNewsUpdate(newItem) {
    const container = document.getElementById('newsContainer');
    if (!container) return;
    
    const currentElements = Array.from(container.children);
    const currentNews = currentElements.map(el => ({
        timestamp: el.querySelector('.time')?.getAttribute('data-timestamp'),
        element: el
    })).filter(item => item.timestamp); // Filter out items without timestamps
    
    // Create new element for the incoming item
    const newItemWrapper = document.createElement('div');
    newItemWrapper.className = 'news-item';
    const newElement = createNewsElement(newItem);
    if (newElement) {
        newItemWrapper.appendChild(newElement);
        
        // Add new item to the beginning of the list
        container.insertBefore(newItemWrapper, container.firstChild);
        
        // Apply animation
        newItemWrapper.classList.add('news-item-new');
        newItemWrapper.style.opacity = '0';
        newItemWrapper.style.transform = 'translateY(-20px)';
        
        // Trigger animation after DOM update
        requestAnimationFrame(() => {
            newItemWrapper.style.transition = 'all 0.5s cubic-bezier(0.4, 0.0, 0.2, 1)';
            newItemWrapper.style.opacity = '1';
            newItemWrapper.style.transform = 'translateY(0)';
            
            setTimeout(() => {
                newItemWrapper.classList.remove('news-item-new');
                newItemWrapper.style.transition = '';
            }, 500);
        });
    }
}

async function updateNews() {
    try {
        // Get active tags
        const activeTags = getActiveTags();
        const tagParam = activeTags.length > 0 ? `?tags=${activeTags.join(',')}` : '';
        
        // Reset infinite scroll and load initial news
        await loadInitialNews(tagParam);
        
        lastUpdate = new Date();
    } catch (error) {
        console.error('Error updating news:', error);
    }
}

// Initialize everything when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
    initWebSocket();
    initTheme();
    await loadCountryData();
    
    const scrollToTopBtn = createScrollToTopButton();
    window.addEventListener('scroll', updateScrollToTopButtonVisibility);
    
    const newsContainer = document.getElementById('newsContainer');
    const listViewBtn = document.getElementById('listViewBtn');
    const gridViewBtn = document.getElementById('gridViewBtn');
    const searchInput = document.getElementById('searchInput');
    const timeFilter = document.getElementById('timeFilter');
    
    // View switching logic
    listViewBtn.addEventListener('click', () => {
        localStorage.setItem('preferredView', 'list');
        setView('list-view');
        listViewBtn.classList.add('active');
        gridViewBtn.classList.remove('active');
    });
    
    gridViewBtn.addEventListener('click', () => {
        localStorage.setItem('preferredView', 'grid');
        setView('grid-view');
        gridViewBtn.classList.add('active');
        listViewBtn.classList.remove('active');
    });
    
    const preferredView = localStorage.getItem('preferredView') || 'list';
    if (preferredView === 'grid') {
        gridViewBtn.click();
    }
    
    // Search handling with debounce
    let searchTimeout;
    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            setLoading(true);
            updateNews().finally(() => setLoading(false));
        }, 300);
    });
    
    // Time filter handling
    timeFilter.addEventListener('change', () => {
        setLoading(true);
        updateNews().finally(() => setLoading(false));
    });
    
    // Tag filter toggle
    const filterToggle = document.getElementById('filterToggle');
    filterToggle.addEventListener('click', toggleTagFilters);
    
    // Close tag filters when clicking outside
    document.addEventListener('click', (e) => {
        const tagFilters = document.querySelector('.tag-filters');
        const filterToggle = document.getElementById('filterToggle');
        
        if (tagFilters && !tagFilters.contains(e.target) && !filterToggle.contains(e.target)) {
            tagFilters.classList.add('collapsed');
        }
    });
    
    // Initial setup
    await loadTags();
    setLoading(true);
    
    // Initialize infinite scroll
    initInfiniteScroll();
    
    // Load initial data
    await updateNews();
    setLoading(false);
});