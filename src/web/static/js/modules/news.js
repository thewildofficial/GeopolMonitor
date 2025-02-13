export function createNewsElement(newsItem) {
    const template = document.getElementById('newsItemTemplate');
    const element = template.content.cloneNode(true);
    const article = element.querySelector('article');
    const imageContainer = article.querySelector('.news-image-container');
    const image = article.querySelector('.news-image');

    // Format title with emojis
    const titleText = newsItem.title || "Untitled";
    const emojis = (newsItem.emoji1 || '') + (newsItem.emoji2 || '');
    const titleWithEmojis = emojis ? `${emojis} ${titleText}` : titleText;
    
    // Get a clean description
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
    
    // Make article clickable
    article.style.cursor = 'pointer';
    article.addEventListener('click', (e) => {
        e.preventDefault();
        window.open(newsItem.link, '_blank', 'noopener');
    });

    // Handle image errors
    image.onerror = () => {
        imageContainer.style.display = 'none';
    };

    // Add tags
    if (newsItem.tags && newsItem.tags.length > 0) {
        const tagsContainer = article.querySelector('.tags');
        newsItem.tags.forEach(tag => {
            const tagEl = document.createElement('span');
            tagEl.className = 'tag';
            tagEl.textContent = tag.name;
            tagEl.dataset.category = tag.category;
            
            // Add click handler for tag filtering
            tagEl.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent article click
                const tagName = tag.name;
                if (window.toggleTag) {
                    window.toggleTag(tagName);
                }
            });
            
            tagsContainer.appendChild(tagEl);
        });
    }

    return element;
}

export function formatTimeAgo(timestamp) {
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