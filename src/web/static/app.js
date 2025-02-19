import { initWebSocket } from './js/modules/websocket.js';
import { createNewsElement, formatTimeAgo } from './js/modules/news.js';
import { initTheme } from './js/modules/theme.js';
import { loadTags, toggleTagFilters, getActiveTags } from './js/modules/tags.js';
import { createScrollToTopButton, updateScrollToTopButtonVisibility, setView, setLoading, addLoadingItem } from './js/modules/ui-utils.js';
import { loadCountryData } from './js/modules/countries.js';

let lastUpdate = new Date();
const updateInterval = 30000; // 30 seconds


// Make functions globally available for WebSocket handler
window.handleNewsUpdate = handleNewsUpdate;
window.updateNews = updateNews;

async function handleNewsUpdate(newItem) {
 
    const container = document.getElementById('newsContainer');
    
    const currentElements = Array.from(container.children);
    const currentNews = currentElements.map(el => ({
        timestamp: el.querySelector('.time').getAttribute('data-timestamp'),
        element: el
    }));
    
    currentNews.push({
        timestamp: newItem.timestamp,
        element: createNewsElement(newItem)
    });
    
    currentNews.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    container.innerHTML = '';
    currentNews.forEach(item => {
        if (item.element === currentNews[0].element) {
            item.element.classList.add('news-item-new');
            item.element.style.opacity = '0';
            item.element.style.transform = 'translateY(-20px)';
        }
        container.appendChild(item.element);
    });
    
    if (currentNews[0].timestamp === newItem.timestamp) {
        await new Promise(resolve => requestAnimationFrame(resolve));
        const newestElement = container.firstElementChild;
        newestElement.style.transition = 'all 0.5s cubic-bezier(0.4, 0.0, 0.2, 1)';
        newestElement.style.opacity = '1';
        newestElement.style.transform = 'translateY(0)';
        
        setTimeout(() => {
            newestElement.classList.remove('news-item-new');
            newestElement.style.transition = '';
        }, 500);
    }
}

async function fetchNews() {
    try {
        addLoadingItem('Fetching latest news articles...');
        const activeTags = getActiveTags();
        const tagParam = activeTags.length > 0 ? `?tags=${activeTags.join(',')}` : '';
        const response = await fetch(`/api/news${tagParam}`);
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();
        addLoadingItem('Processing news data...');
        return data.news || [];
    } catch (error) {
        console.error('Error fetching news:', error);
        return [];
    }
}

async function filterNews(news) {
    const searchTerm = searchInput.value.toLowerCase();
    const timeValue = timeFilter.value;
    const activeTags = getActiveTags();
    
    let filtered = news;

    if (searchTerm) {
        filtered = filtered.filter(item => 
            item.title.toLowerCase().includes(searchTerm) ||
            item.description.toLowerCase().includes(searchTerm)
        );
    }

    if (timeValue !== 'all') {
        const now = new Date();
        const cutoff = new Date();
        switch (timeValue) {
            case '1h':
                cutoff.setHours(now.getHours() - 1);
                break;
            case '24h':
                cutoff.setDate(now.getDate() - 1);
                break;
            case '7d':
                cutoff.setDate(now.getDate() - 7);
                break;
        }
        filtered = filtered.filter(item => new Date(item.timestamp) > cutoff);
    }

    // Filter by active tags
    if (activeTags.length > 0) {
        filtered = filtered.filter(item => {
            if (!item.tags) return false;
            return activeTags.some(activeTag => 
                item.tags.some(itemTag => 
                    itemTag.name === activeTag || 
                    (itemTag.category === 'geography' && 
                     itemTag.name.toLowerCase().split(' ').map(word => 
                         word.charAt(0).toUpperCase() + word.slice(1)
                     ).join(' ') === activeTag)
                )
            );
        });
    }

    return filtered;
}

async function updateNewsList(news) {
    const container = document.getElementById('newsContainer');
    if (!container) return;
    
    addLoadingItem('Creating news elements...');
    const fragment = document.createDocumentFragment();
    news.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    let loadedImages = 0;
    const totalImages = news.length;
    const IMAGE_LOAD_TIMEOUT = 3000; // 3 seconds timeout for each image
    
    const imageLoadPromises = news.map((item, index) => {
        return new Promise((resolve) => {
            if (!item.image_url) {
                resolve();
                return;
            }

            const img = new Image();
            let timeoutId;

            const cleanup = () => {
                clearTimeout(timeoutId);
                img.onload = null;
                img.onerror = null;
            };

            const handleLoad = () => {
                loadedImages++;
                addLoadingItem(`Loading images (${loadedImages}/${totalImages})...`);
                cleanup();
                resolve();
            };

            const handleError = () => {
                console.warn('Failed to load image:', item.image_url);
                cleanup();
                resolve();
            };

            timeoutId = setTimeout(() => {
                console.warn('Image load timeout:', item.image_url);
                handleError();
            }, IMAGE_LOAD_TIMEOUT);

            img.onload = handleLoad;
            img.onerror = handleError;
            img.src = item.image_url;
        });
    });

    // Wait for all images to either load or timeout
    await Promise.all(imageLoadPromises);
    addLoadingItem('Rendering news feed...');
    
    news.forEach((item, index) => {
        try {
            // Ensure sentiment and bias data is properly formatted
            if (item.sentiment) {
                item.sentiment = parseFloat(item.sentiment);
            }
            if (item.bias) {
                item.bias = parseFloat(item.bias);
            }
            
            const element = createNewsElement(item);
            if (element && element.firstElementChild) {
                element.firstElementChild.classList.add('news-item-initial');
                element.firstElementChild.style.animationDelay = `${index * 0.1}s`;
                fragment.appendChild(element);
            }
        } catch (error) {
            console.error('Error creating news element:', error);
        }
    });

    container.innerHTML = '';
    container.appendChild(fragment);
    
    // Show "no results" message if no valid news items
    if (!fragment.children.length) {
        const noResults = document.createElement('div');
        noResults.className = 'no-results';
        noResults.innerHTML = `
            <i class="fas fa-newspaper"></i>
            <p>No news articles available</p>
        `;
        container.appendChild(noResults);
    }
}

async function updateNews() {
    try {
        const news = await fetchNews();
        if (!news || news.length === 0) return;
        
        const filtered = await filterNews(news);
        filtered.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        
        await updateNewsList(filtered);
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

    let searchTimeout;
    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            setLoading(true);
            updateNews().finally(() => setLoading(false));
        }, 300);
    });

    timeFilter.addEventListener('change', () => {
        setLoading(true);
        updateNews().finally(() => setLoading(false));
    });

    const filterToggle = document.getElementById('filterToggle');
    filterToggle.addEventListener('click', toggleTagFilters);
    
    document.addEventListener('click', (e) => {
        const tagFilters = document.querySelector('.tag-filters');
        const filterToggle = document.getElementById('filterToggle');
        
        if (!tagFilters.contains(e.target) && !filterToggle.contains(e.target)) {
            tagFilters.classList.add('collapsed');
        }
    });

    // Initial setup
    await loadTags();
    setLoading(true);
    await updateNews();
    setLoading(false);
    
    // Set up periodic updates
    setInterval(() => updateNews(), updateInterval);
});