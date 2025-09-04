export function createScrollToTopButton() {
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

export function updateScrollToTopButtonVisibility() {
    const button = document.getElementById('scrollToTopBtn');
    if (!button) return;
    
    if (window.scrollY > 500) {
        button.classList.remove('hidden');
    } else {
        button.classList.add('hidden');
    }
}

export function setView(viewType) {
    const newsContainer = document.getElementById('newsContainer');
    const currentView = newsContainer.className;
    
    if (currentView !== viewType) {
        newsContainer.classList.add('view-transitioning');
        
        const items = Array.from(newsContainer.children);
        const oldPositions = items.map(item => item.getBoundingClientRect());
        
        newsContainer.className = viewType;
        newsContainer.offsetHeight; // Force reflow
        
        items.forEach((item, i) => {
            const oldPos = oldPositions[i];
            const newPos = item.getBoundingClientRect();
            
            const dx = oldPos.left - newPos.left;
            const dy = oldPos.top - newPos.top;
            
            item.style.transform = `translate(${dx}px, ${dy}px)`;
            item.style.transition = 'none';
            
            item.offsetHeight; // Force reflow
            
            item.style.transform = '';
            item.style.transition = 'transform 0.5s cubic-bezier(0.4, 0.0, 0.2, 1)';
        });
        
        setTimeout(() => {
            items.forEach(item => {
                item.style.transform = '';
                item.style.transition = '';
            });
            newsContainer.classList.remove('view-transitioning');
        }, 500);
    }
}

let loadingItems = [];
let loadingTimeout;
let progressTimeout;

export function setLoading(loading) {
    document.body.classList.toggle('loading', loading);
    const loadingItemsEl = document.querySelector('.loading-items');
    
    if (loading) {
        // Reset loading items
        loadingItems = [];
        updateLoadingItems();
        loadingItemsEl.classList.remove('show');
        
        // Show loading items after a delay
        clearTimeout(progressTimeout);
        progressTimeout = setTimeout(() => {
            loadingItemsEl.classList.add('show');
        }, 800); // Increased delay for more Apple-like feel
    } else {
        clearTimeout(progressTimeout);
        // Fade out gracefully
        loadingItemsEl.classList.remove('show');
        setTimeout(() => {
            loadingItems = [];
            updateLoadingItems();
        }, 300);
    }
}

export function addLoadingItem(item) {
    loadingItems.push(item);
    updateLoadingItems();
    
    // Animate the loading bar
    const progress = Math.min((loadingItems.length / 5) * 100, 90); // Cap at 90% until complete
    const loadingBar = document.querySelector('.loading-bar-progress');
    if (loadingBar) {
        loadingBar.style.width = `${progress}%`;
    }
}

function updateLoadingItems() {
    const loadingItemsEl = document.querySelector('.loading-items');
    const loadingTextEl = document.querySelector('.loading-text');
    
    if (loadingItems.length > 0) {
        const latestItem = loadingItems[loadingItems.length - 1];
        loadingItemsEl.textContent = latestItem;
        loadingTextEl.textContent = getLoadingPhrase(loadingItems.length);
    }
}

function getLoadingPhrase(step) {
    const phrases = [
        "Getting things ready...",
        "Loading latest updates...",
        "Almost there...",
        "Putting everything together...",
        "Just a moment..."
    ];
    return phrases[Math.min(step, phrases.length - 1)];
}

/**
 * Date formatting utilities to handle UTC dates consistently across the application
 */

/**
 * Format a UTC ISO date string to the user's local timezone
 * @param {string} isoDateString - ISO datetime string in UTC
 * @param {object} options - Formatting options
 * @returns {string} Formatted date string in local timezone
 */
export function formatDate(isoDateString, options = {}) {
    if (!isoDateString) return '';
    
    try {
        const date = new Date(isoDateString);
        
        // Check if date is valid
        if (isNaN(date.getTime())) {
            console.warn('Invalid date:', isoDateString);
            return '';
        }
        
        const defaultOptions = {
            dateStyle: 'medium',
            timeStyle: 'short'
        };
        
        const mergedOptions = { ...defaultOptions, ...options };
        return new Intl.DateTimeFormat(navigator.language, mergedOptions).format(date);
    } catch (error) {
        console.error('Error formatting date:', error);
        return isoDateString;
    }
}

/**
 * Format a UTC ISO date string as a relative time (e.g., "2 hours ago")
 * @param {string} isoDateString - ISO datetime string in UTC
 * @returns {string} Relative time string
 */
export function formatRelativeTime(isoDateString) {
    if (!isoDateString) return '';
    
    try {
        const date = new Date(isoDateString);
        const now = new Date();
        const diffMs = now - date;
        const diffSec = Math.floor(diffMs / 1000);
        const diffMin = Math.floor(diffSec / 60);
        const diffHour = Math.floor(diffMin / 60);
        const diffDay = Math.floor(diffHour / 24);
        const diffMonth = Math.floor(diffDay / 30);
        const diffYear = Math.floor(diffDay / 365);
        
        if (diffSec < 60) {
            return 'just now';
        } else if (diffMin < 60) {
            return `${diffMin} minute${diffMin > 1 ? 's' : ''} ago`;
        } else if (diffHour < 24) {
            return `${diffHour} hour${diffHour > 1 ? 's' : ''} ago`;
        } else if (diffDay < 30) {
            return `${diffDay} day${diffDay > 1 ? 's' : ''} ago`;
        } else if (diffMonth < 12) {
            return `${diffMonth} month${diffMonth > 1 ? 's' : ''} ago`;
        } else {
            return `${diffYear} year${diffYear > 1 ? 's' : ''} ago`;
        }
    } catch (error) {
        console.error('Error formatting relative time:', error);
        return '';
    }
}

/**
 * Add a clock element that updates with the current time
 * @param {string} elementId - ID of the element to insert the clock
 * @returns {function} Function to stop the clock
 */
export function startLiveClock(elementId) {
    const clockElement = document.getElementById(elementId);
    if (!clockElement) return () => {};
    
    const updateClock = () => {
        const now = new Date();
        const options = {
            hour: 'numeric',
            minute: 'numeric',
            second: 'numeric',
            hour12: true,
            timeZoneName: 'short'
        };
        clockElement.textContent = new Intl.DateTimeFormat(navigator.language, options).format(now);
    };
    
    // Update immediately and then every second
    updateClock();
    const interval = setInterval(updateClock, 1000);
    
    // Return a function to stop the clock
    return () => clearInterval(interval);
}

/**
 * Initialize all date elements in the document
 * Finds elements with data-utc-date attribute and formats them
 */
export function initializeDateElements() {
    const dateElements = document.querySelectorAll('[data-utc-date]');
    
    dateElements.forEach(element => {
        const isoDate = element.getAttribute('data-utc-date');
        const format = element.getAttribute('data-date-format') || 'full';
        const relative = element.hasAttribute('data-relative');
        
        if (relative) {
            element.textContent = formatRelativeTime(isoDate);
            // Update relative time periodically
            setInterval(() => {
                element.textContent = formatRelativeTime(isoDate);
            }, 60000); // Every minute
        } else {
            let options = {};
            
            // Handle different preset formats
            switch (format) {
                case 'date-only':
                    options = { dateStyle: 'medium', timeStyle: undefined };
                    break;
                case 'time-only':
                    options = { dateStyle: undefined, timeStyle: 'medium' };
                    break;
                case 'short':
                    options = { dateStyle: 'short', timeStyle: 'short' };
                    break;
                case 'full':
                default:
                    options = { dateStyle: 'full', timeStyle: 'medium' };
                    break;
            }
            
            element.textContent = formatDate(isoDate, options);
        }
        
        // Add title with both absolute and relative time for hover
        element.title = `${formatDate(isoDate, { dateStyle: 'full', timeStyle: 'long' })}
${formatRelativeTime(isoDate)}`;
    });
}