import { normalizeCountry, isCountryMatch } from './countries.js';

export function createNewsElement(newsItem) {
    // Skip articles with no description
    if (!newsItem.description) {
        return null;
    }

    const template = document.getElementById('newsItemTemplate');
    const element = template.content.cloneNode(true);
    const article = element.querySelector('article');
    const imageContainer = article.querySelector('.news-image-container');
    const image = article.querySelector('.news-image');

    // Format title with emojis
    const titleText = newsItem.title || "Untitled";
    const emoji1 = newsItem.emoji1 || '';
    const emoji2 = newsItem.emoji2 || '';
    const emojis = emoji1 + emoji2;
    const titleWithEmojis = emojis ? `${emoji1}${emoji2} ${titleText}` : titleText;
    
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
    article.querySelector('.description').textContent = description;
    
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

    // Add tags with proper formatting for geography tags
    if (newsItem.tags && newsItem.tags.length > 0) {
        const tagsContainer = article.querySelector('.tags');
        newsItem.tags.forEach(tag => {
            const tagEl = document.createElement('span');
            tagEl.className = 'tag';
            
            // Format geography tags with proper capitalization and add flag
            if (tag.category === 'geography') {
                const countryData = normalizeCountry(tag.name);
                const formattedName = countryData.name;
                const flag = countryData.flag;
                tagEl.textContent = flag ? `${flag} ${formattedName}` : formattedName;
                tagEl.dataset.tagName = formattedName;
            } else {
                tagEl.textContent = tag.name;
                tagEl.dataset.tagName = tag.name;
            }
            
            tagEl.dataset.category = tag.category;
            
            // Add click handler for tag filtering
            tagEl.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent article click
                if (window.toggleTag) {
                    window.toggleTag(tagEl.dataset.tagName);
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

// Handle country flags and news display
function showCountryNews(countryName) {
    console.log('Showing news for country:', countryName);
    const newsPanel = document.querySelector('.country-news-panel');
    const countryTitle = document.getElementById('selectedCountry');
    const newsList = document.getElementById('countryNewsList');
    
    const countryData = normalizeCountry(countryName);
    countryTitle.textContent = countryData.name;
    if (countryData.flag) {
        countryTitle.textContent = `${countryData.flag} ${countryData.name}`;
    }
    
    // Reset news list
    newsList.innerHTML = '';
    
    // Filter news items for the selected country
    const countryNews = filterNewsByCountry(countryData);
    console.log(`Found ${countryNews.length} news items for ${countryData.name}`);
    
    if (countryNews.length === 0) {
        newsList.innerHTML = '<p class="no-news">No news available for this country.</p>';
    } else {
        displayFilteredNews(countryNews, newsList);
    }
    
    newsPanel.style.display = 'flex';
    
    // Handle close button click with smooth transition
    const closeBtn = document.getElementById('closeCountryNews');
    closeBtn.onclick = (e) => {
        e.stopPropagation();
        newsPanel.classList.remove('visible');
        
        // Wait for transition to complete before hiding
        setTimeout(() => {
            newsPanel.style.display = 'none';
            if (activeCountryLayer) {
                map.removeLayer(activeCountryLayer);
                activeCountryLayer = null;
            }
            map.setView([30, 0], 2);
        }, 300); // Match the CSS transition duration
    };
    
    // Handle clicking outside the panel
    document.addEventListener('click', (e) => {
        if (!newsPanel.contains(e.target) && 
            !e.target.closest('.leaflet-container') &&
            newsPanel.classList.contains('visible')) {
            closeBtn.click();
        }
    });
}

// Filter news by country with flexible matching
function filterNewsByCountry(countryData) {
    return allNews.filter(item => {
        const geoTags = item.tags.filter(tag => tag.category === 'geography');
        return geoTags.some(tag => {
            const tagCountryData = normalizeCountry(tag.name);
            return isCountryMatch(countryData, tagCountryData);
        });
    });
}

// Display filtered news with deduplicated flags
function displayFilteredNews(newsItems, container) {
    newsItems.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    newsItems.forEach(news => {
        // Get geography tags and normalize them
        const geoTags = news.tags
            .filter(tag => tag.category === 'geography')
            .map(tag => normalizeCountry(tag.name))
            .filter(countryData => countryData.flag);

        // Get unique flags (limit to 2) and sort by importance
        const uniqueFlags = Array.from(new Set(
            geoTags.map(country => ({
                flag: country.flag,
                code: country.code,
                // Prioritize certain countries
                priority: ['US', 'RU', 'CN', 'GB', 'UA'].includes(country.code) ? 1 : 0
            }))
        ))
        .sort((a, b) => b.priority - a.priority)
        .slice(0, 2)
        .map(country => country.flag);
        
        const newsItem = document.createElement('div');
        newsItem.className = 'country-news-item';
        newsItem.innerHTML = `
            <h3>${uniqueFlags.join(' ')} ${news.title}</h3>
            <p>${news.description}</p>
            <div class="meta">
                <span>${formatDate(news.timestamp)}</span>
                ${news.tags.find(t => t.category === 'source')?.name ? 
                  `<span class="source">${news.tags.find(t => t.category === 'source').name}</span>` : ''}
            </div>
        `;
        newsItem.addEventListener('click', () => {
            window.open(news.link, '_blank', 'noopener');
        });
        container.appendChild(newsItem);
    });
}