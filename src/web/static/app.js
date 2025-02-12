let lastUpdate = new Date();
const updateInterval = 30000; // 30 seconds
let ws;

function initWebSocket() {
    // Use wss:// for HTTPS, ws:// for HTTP
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('WebSocket connection established');
    };
    
    ws.onmessage = async (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'news_update') {
            await handleNewsUpdate(data.data);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
        console.log('WebSocket connection closed, attempting to reconnect...');
        // Reconnect after 1 second
        setTimeout(initWebSocket, 1000);
    };
}

async function handleNewsUpdate(newItem) {
    const container = document.getElementById('newsContainer');
    
    // Get current news items
    const currentElements = Array.from(container.children);
    const currentNews = currentElements.map(el => ({
        timestamp: el.querySelector('.time').getAttribute('data-timestamp'),
        element: el
    }));
    
    // Add new item to the array and sort
    currentNews.push({
        timestamp: newItem.timestamp,
        element: createNewsElement(newItem)
    });
    
    currentNews.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    // Clear container and append in new order
    container.innerHTML = '';
    currentNews.forEach(item => {
        if (item.element === currentNews[0].element) {
            // Add animation only for the newest item
            item.element.classList.add('news-item-new');
            item.element.style.opacity = '0';
            item.element.style.transform = 'translateY(-20px)';
        }
        container.appendChild(item.element);
    });
    
    // Animate the new item if it's at the top
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
        const response = await fetch('/api/news');
        const data = await response.json();
        return data.news;
    } catch (error) {
        console.error('Error fetching news:', error);
        return [];
    }
}

function extractImageFromContent(content) {
    if (!content) return null;
    const parser = new DOMParser();
    const doc = parser.parseFromString(content, 'text/html');
    const img = doc.querySelector('img');
    return img ? img.src : null;
}

function formatTimeAgo(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    const intervals = {
        year: 31536000,
        month: 2592000,
        week: 604800,
        day: 86400,
        hour: 3600,
        minute: 60
    };

    for (const [unit, secondsInUnit] of Object.entries(intervals)) {
        const interval = Math.floor(seconds / secondsInUnit);
        if (interval >= 1) {
            return `${interval} ${unit}${interval === 1 ? '' : 's'} ago`;
        }
    }
    return 'Just now';
}

function createNewsElement(newsItem) {
    const template = document.getElementById('newsItemTemplate');
    const element = template.content.cloneNode(true);
    const article = element.querySelector('article');
    const imageContainer = article.querySelector('.news-image-container');
    const image = article.querySelector('.news-image');

    // Format title with emojis, handle missing title
    const titleText = newsItem.title || "Untitled";
    const emojis = (newsItem.emoji1 || '') + (newsItem.emoji2 || '');
    const titleWithEmojis = emojis ? `${emojis} ${titleText}` : titleText;
    
    // Get a clean description (use first 2-3 sentences if full description provided)
    let description = newsItem.description;
    if (description && description.length > 300) {
        const sentences = description.split('.');
        description = sentences.slice(0, 3)
            .map(s => s.trim())
            .filter(s => s.length > 0)
            .join('. ') + '.';
    }
    
    article.querySelector('h2').textContent = titleWithEmojis;
    article.querySelector('.description').textContent = description || 'No description available';
    
    // Store timestamp as data attribute for sorting
    const timeElement = article.querySelector('.time');
    timeElement.textContent = formatTimeAgo(newsItem.timestamp);
    timeElement.setAttribute('data-timestamp', newsItem.timestamp);

    // Handle image
    const imageUrl = newsItem.image_url || null;
    if (imageUrl) {
        image.src = imageUrl;
        image.alt = titleText;
        imageContainer.style.display = 'block';
    } else {
        imageContainer.style.display = 'none';
    }
    
    // Make the entire article clickable
    article.style.cursor = 'pointer';
    article.addEventListener('click', (e) => {
        e.preventDefault();
        window.open(newsItem.link, '_blank', 'noopener');
    });

    // Handle image loading errors
    image.onerror = () => {
        imageContainer.style.display = 'none';
    };

    return element;
}

function createScrollToTopButton() {
    const button = document.createElement('button');
    button.id = 'scrollToTopBtn';
    button.innerHTML = '↑';
    button.className = 'scroll-to-top-btn hidden';
    button.title = 'Scroll to top';
    
    button.addEventListener('click', () => {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
    
    document.body.appendChild(button);
    return button;
}

function updateScrollToTopButtonVisibility() {
    const button = document.getElementById('scrollToTopBtn');
    if (!button) return;
    
    if (window.scrollY > 500) {
        button.classList.remove('hidden');
    } else {
        button.classList.add('hidden');
    }
}

function updateNewsList(news) {
    const container = document.getElementById('newsContainer');
    if (!container) return;
    
    const fragment = document.createDocumentFragment();
    
    // Sort news by timestamp, newest first
    news.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    // Create elements with staggered animations
    news.forEach((item, index) => {
        try {
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

    // Clear and update the container
    container.innerHTML = '';
    container.appendChild(fragment);
}

async function filterNews(news) {
    const searchTerm = searchInput.value.toLowerCase();
    const timeValue = timeFilter.value;
    
    let filtered = news;

    // Apply search filter
    if (searchTerm) {
        filtered = filtered.filter(item => 
            item.title.toLowerCase().includes(searchTerm) ||
            item.description.toLowerCase().includes(searchTerm)
        );
    }

    // Apply time filter
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

    return filtered;
}

async function updateNews() {
    try {
        const news = await fetchNews();
        if (!news || news.length === 0) return;
        
        const container = document.getElementById('newsContainer');
        if (!container) return;
        
        const filtered = await filterNews(news);
        
        // Sort news by timestamp before processing
        filtered.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        
        // Get current items
        const currentItems = Array.from(container.children);
        const currentIds = new Set(currentItems.map(item => item.dataset.id));
        
        // Create new items
        const fragment = document.createDocumentFragment();
        filtered.forEach(item => {
            try {
                const element = createNewsElement(item);
                if (!element || !element.firstElementChild) return;
                
                const id = item.link || item.title; // Use link or title as unique ID
                element.firstElementChild.dataset.id = id;
                
                if (!currentIds.has(id)) {
                    // New item animation
                    element.firstElementChild.classList.add('news-item-new');
                }
                fragment.appendChild(element);
            } catch (error) {
                console.error('Error creating news element:', error);
            }
        });
        
        // Animate out items that will be removed
        const newIds = new Set(filtered.map(item => item.link || item.title));
        const removePromises = currentItems
            .filter(item => !newIds.has(item.dataset.id))
            .map(item => {
                return new Promise(resolve => {
                    if (item) {
                        item.style.transition = 'all 0.5s cubic-bezier(0.4, 0.0, 0.2, 1)';
                        item.style.opacity = '0';
                        item.style.transform = 'scale(0.9)';
                    }
                    setTimeout(resolve, 500);
                });
            });
        
        await Promise.all(removePromises);
        
        // Update container
        container.innerHTML = '';
        container.appendChild(fragment);
        
        // Trigger new item animations
        requestAnimationFrame(() => {
            const newItems = container.querySelectorAll('.news-item-new');
            newItems.forEach(item => {
                if (item) {
                    item.classList.add('news-item-visible');
                    setTimeout(() => {
                        item.classList.remove('news-item-new', 'news-item-visible');
                    }, 500);
                }
            });
        });
        
        lastUpdate = new Date();
    } catch (error) {
        console.error('Error updating news:', error);
    }
}

// Theme management
function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    
    const themeToggle = document.getElementById('themeToggle');
    const icon = themeToggle.querySelector('i');
    
    if (theme === 'dark') {
        icon.classList.remove('fa-sun');
        icon.classList.add('fa-moon');
    } else {
        icon.classList.remove('fa-moon');
        icon.classList.add('fa-sun');
    }
}

// Enhance view toggle transitions
function setView(viewType) {
    const newsContainer = document.getElementById('newsContainer');
    const currentView = newsContainer.className;
    
    if (currentView !== viewType) {
        // Add transition class
        newsContainer.classList.add('view-transitioning');
        
        // Get current positions of all items
        const items = Array.from(newsContainer.children);
        const oldPositions = items.map(item => item.getBoundingClientRect());
        
        // Change view
        newsContainer.className = viewType;
        
        // Force reflow
        newsContainer.offsetHeight;
        
        // Get new positions and apply FLIP animations
        items.forEach((item, i) => {
            const oldPos = oldPositions[i];
            const newPos = item.getBoundingClientRect();
            
            // Calculate transforms
            const dx = oldPos.left - newPos.left;
            const dy = oldPos.top - newPos.top;
            
            // Apply initial position
            item.style.transform = `translate(${dx}px, ${dy}px)`;
            item.style.transition = 'none';
            
            // Force reflow
            item.offsetHeight;
            
            // Animate to new position
            item.style.transform = '';
            item.style.transition = 'transform 0.5s cubic-bezier(0.4, 0.0, 0.2, 1)';
        });
        
        // Clean up after animation
        setTimeout(() => {
            items.forEach(item => {
                item.style.transform = '';
                item.style.transition = '';
            });
            newsContainer.classList.remove('view-transitioning');
        }, 500);
    }
}

// Initial load and periodic updates
document.addEventListener('DOMContentLoaded', async () => {
    // Initialize WebSocket connection
    initWebSocket();
    
    // Create scroll to top button
    const scrollToTopBtn = createScrollToTopButton();
    
    // Add scroll listener for button visibility
    window.addEventListener('scroll', updateScrollToTopButtonVisibility);
    
    // Theme initialization
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);
    
    const themeToggle = document.getElementById('themeToggle');
    themeToggle.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        setTheme(currentTheme === 'dark' ? 'light' : 'dark');
    });

    const newsContainer = document.getElementById('newsContainer');
    const listViewBtn = document.getElementById('listViewBtn');
    const gridViewBtn = document.getElementById('gridViewBtn');
    const searchInput = document.getElementById('searchInput');
    const timeFilter = document.getElementById('timeFilter');

    // View Toggle Functionality
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

    // Restore user's preferred view
    const preferredView = localStorage.getItem('preferredView') || 'list';
    if (preferredView === 'grid') {
        gridViewBtn.click();
    }

    // Add debounced search handler
    let searchTimeout;
    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            setLoading(true);
            updateNews().finally(() => setLoading(false));
        }, 300);
    });

    // Add time filter handler
    timeFilter.addEventListener('change', () => {
        setLoading(true);
        updateNews().finally(() => setLoading(false));
    });

    // Add loading state
    const setLoading = (loading) => {
        document.body.classList.toggle('loading', loading);
    };

    // Update news with loading state
    const updateNewsWithLoading = async () => {
        setLoading(true);
        await updateNews();
        setLoading(false);
    };

    // Initial fetch with loading indicator
    const initialLoad = async () => {
        setLoading(true);
        const news = await fetchNews();
        if (news && news.length > 0) {
            const filtered = await filterNews(news);
            updateNewsList(filtered);
        }
        setLoading(false);
    };

    await initialLoad();

    // Set up periodic updates with error handling
    setInterval(updateNewsWithLoading, updateInterval);

    // Add error handling for image loads
    document.addEventListener('error', (e) => {
        if (e.target.tagName === 'IMG') {
            const container = e.target.closest('.news-image-container');
            if (container) {
                container.style.display = 'none';
            }
        }
    }, true);
});

// Add CSS styles for the scroll to top button
const style = document.createElement('style');
style.textContent = `
.scroll-to-top-btn {
    position: fixed;
    bottom: 30px;
    right: 30px;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: var(--primary-color, #007AFF);
    color: white;
    border: none;
    font-size: 20px;
    cursor: pointer;
    opacity: 1;
    transition: all 0.3s ease;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
    z-index: 1000;
}

.scroll-to-top-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.scroll-to-top-btn.hidden {
    opacity: 0;
    pointer-events: none;
    transform: translateY(20px);
}

.news-item-new {
    will-change: transform, opacity;
}

[data-theme="dark"] .scroll-to-top-btn {
    background: var(--card-background, #2c2c2c);
    color: white;
    border: 2px solid var(--border-color, #404040);
}
`;
document.head.appendChild(style);