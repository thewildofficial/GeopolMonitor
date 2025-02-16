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