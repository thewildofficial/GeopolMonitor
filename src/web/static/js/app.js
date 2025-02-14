async function updateNewsList(news) {
    const container = document.getElementById('newsContainer');
    if (!container) return;
    
    const fragment = document.createDocumentFragment();
    news.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
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