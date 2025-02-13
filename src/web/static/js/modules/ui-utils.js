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

export function setLoading(loading) {
    document.body.classList.toggle('loading', loading);
}