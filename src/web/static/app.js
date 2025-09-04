// Import required modules
import { loadTags, toggleTagFilters, getActiveTags, toggleTag } from './js/modules/tags.js';
import { loadInitialNews, initInfiniteScroll, setActiveTagFilter } from './js/modules/news.js';
import { initWebSocket } from './js/modules/websocket.js';
import { initTheme } from './js/modules/theme.js';
import { createScrollToTopButton, updateScrollToTopButtonVisibility, setView, setLoading } from './js/modules/ui-utils.js';
import { loadCountryData } from './js/modules/countries.js';

// Debug flag
const DEBUG = true;

function debugLog(...args) {
    if (DEBUG) {
        console.log(...args);
    }
}

// Make functions globally available
window.toggleTag = toggleTag;
window.getActiveTags = getActiveTags;

// Initialize everything when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
    debugLog('DOM loaded, initializing app...');
    
    try {
        initWebSocket();
        initTheme();
        await loadCountryData();
        
        // Initialize tags first
        await loadTags();
        debugLog('Tags initialized');
        
        // Load initial news before setting up infinite scroll
        debugLog('Loading initial news...');
        setLoading(true);
        await loadInitialNews();
        setLoading(false);
        debugLog('Initial news loaded successfully');

        // Initialize infinite scroll after initial news load
        debugLog('Initializing infinite scroll...');
        await initInfiniteScroll();
        debugLog('Infinite scroll initialized');
        
        // Set up UI controls
        const scrollToTopBtn = createScrollToTopButton();
        window.addEventListener('scroll', updateScrollToTopButtonVisibility);
        
        const newsContainer = document.getElementById('newsContainer');
        const listViewBtn = document.getElementById('listViewBtn');
        const gridViewBtn = document.getElementById('gridViewBtn');
        const filterToggle = document.getElementById('filterToggle');
        
        if (!newsContainer) {
            throw new Error('News container element not found!');
        }
        
        // View switching logic
        if (listViewBtn && gridViewBtn) {
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
            
            // Set initial view
            const preferredView = localStorage.getItem('preferredView') || 'list';
            if (preferredView === 'grid') {
                gridViewBtn.click();
            }
        }
        
        // Initialize theme toggle
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                const currentTheme = document.documentElement.getAttribute('data-theme');
                const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
                document.documentElement.setAttribute('data-theme', newTheme);
                localStorage.setItem('theme', newTheme);
            });
        }
        
        // Tag filter toggle
        if (filterToggle) {
            filterToggle.addEventListener('click', toggleTagFilters);
            
            // Close tag filters when clicking outside
            document.addEventListener('click', (e) => {
                const tagFilters = document.querySelector('.tag-filters');
                if (tagFilters && !tagFilters.contains(e.target) && !filterToggle.contains(e.target)) {
                    tagFilters.classList.add('collapsed');
                }
            });
        }
        
        // Remove loading screen
        const loadingScreen = document.querySelector('.loading-screen');
        if (loadingScreen) {
            loadingScreen.style.opacity = '0';
            setTimeout(() => {
                loadingScreen.style.display = 'none';
            }, 500);
        }
        
    } catch (error) {
        console.error('Error during app initialization:', error);
        setLoading(false);
        
        // Show error in console only
        console.error('Initialization error:', error);
    }
});