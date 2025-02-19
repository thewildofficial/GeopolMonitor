import { normalizeCountry, isCountryMatch } from './countries.js';
import { SentimentPanel } from './sentiment-panel.js';

function getSentimentColor(sentiment) {
    // Convert sentiment score (-1 to 1) to a color
    const normalizedScore = (sentiment + 1) / 2; // Convert to 0-1 range
    if (normalizedScore < 0.4) return 'var(--negative-sentiment)';
    if (normalizedScore > 0.6) return 'var(--positive-sentiment)';
    return 'var(--neutral-sentiment)';
}

function getBiasLabel(bias) {
    // Convert bias score to a human-readable label
    if (bias >= 0.7) return 'Strong bias';
    if (bias >= 0.4) return 'Moderate bias';
    return 'Low bias';
}

export function createNewsElement(newsItem) {
    console.log('News item data:', {
        title: newsItem.title,
        sentiment_score: newsItem.sentiment_score,
        bias_score: newsItem.bias_score,
        bias_category: newsItem.bias_category
    });

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
    const titleWithEmojis = `${newsItem.emoji1}${newsItem.emoji2} ${titleText}`;
    
    let description = newsItem.description;
    if (description && description.length > 300) {
        const sentences = description.split('.');
        description = sentences.slice(0, 3)
            .map(s => s.trim())
            .filter(s => s.length > 0)
            .join('. ') + '.';
    }
    
    function getSentimentLabel(score) {
        if (score >= 0.6) return 'Positive';
        if (score <= -0.6) return 'Negative';
        if (score >= 0.2) return 'Somewhat Positive';
        if (score <= -0.2) return 'Somewhat Negative';
        return 'Neutral';
    }
    
    function getBiasIcon(score) {
        if (score >= 0.7) return '⚠️';
        if (score >= 0.4) return '⚡';
        return '✓';
    }
    
    // Add sentiment indicator
    const titleContainer = article.querySelector('h2');
    titleContainer.textContent = titleWithEmojis;
    
    if (newsItem.sentiment_score !== undefined) {
        const sentimentWrapper = document.createElement('div');
        sentimentWrapper.className = 'sentiment-wrapper';
        
        const sentimentIndicator = document.createElement('span');
        sentimentIndicator.className = 'sentiment-indicator';
        sentimentIndicator.style.backgroundColor = getSentimentColor(newsItem.sentiment_score);
        
        const sentimentLabel = document.createElement('span');
        sentimentLabel.className = 'sentiment-label';
        sentimentLabel.textContent = getSentimentLabel(newsItem.sentiment_score);
        
        sentimentWrapper.appendChild(sentimentIndicator);
        sentimentWrapper.appendChild(sentimentLabel);
        titleContainer.appendChild(sentimentWrapper);
    }
    
    // Add bias indicator if available
    if (newsItem.bias_score !== undefined) {
        const biasWrapper = document.createElement('div');
        biasWrapper.className = 'bias-wrapper';
        
        const biasIcon = document.createElement('span');
        
        
        const biasLabel = document.createElement('span');
        
        
        const biasScore = document.createElement('span');
        biasScore.className = 'bias-score';        
        biasWrapper.appendChild(biasIcon);
        biasWrapper.appendChild(biasLabel);
        biasWrapper.appendChild(biasScore);
        
        const meta = article.querySelector('.meta');
        meta.appendChild(biasWrapper);
    }

    const descContainer = article.querySelector('.description');
    descContainer.textContent = description;

    

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

    // Add source to meta section
    const sourceTag = newsItem.tags.find(tag => tag.category === 'source');
    if (sourceTag) {
        const meta = article.querySelector('.meta');
        const sourceSpan = document.createElement('span');
        sourceSpan.className = 'source';
        sourceSpan.textContent = sourceTag.name;
        meta.appendChild(sourceSpan);
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
        tagsContainer.innerHTML = ''; // Clear existing tags
        
        // Sort tags by category for consistent display
        const sortedTags = [...newsItem.tags].sort((a, b) => {
            const categoryOrder = {
                'geography': 1,
                'events': 2,
                'topic': 3,
                'source': 4
            };
            return (categoryOrder[a.category] || 99) - (categoryOrder[b.category] || 99);
        });

        sortedTags.forEach(tag => {
            if (tag.category === 'source') return; // Skip source tags as they're shown in meta
            const tagEl = renderTag(tag.name, tag.category);
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

function renderTag(name, category) {
    const span = document.createElement('span');
    span.className = 'tag-in-article';
    span.dataset.category = category;
    
    if (category === 'geography') {
        const countryData = normalizeCountry(name);
        const normalizedName = countryData.name;
        const flag = countryData.flag || '';
        
        span.dataset.tag = normalizedName;
        span.innerHTML = `${flag} ${normalizedName}`;
    } else {
        span.dataset.tag = name;
        span.textContent = name;
    }
    
    span.addEventListener('click', (e) => {
        e.stopPropagation(); // Prevent the article click event
        window.toggleTag(span.dataset.tag);
    });
    
    return span;
}

export async function fetchNews(tagParam = '') {
    try {
        const response = await fetch(`/api/news${tagParam}`);
        const data = await response.json();
        return data.news;
    } catch (error) {
        console.error('Error fetching news:', error);
        return [];
    }
}

export async function filterNews(news) {
    return news.filter(item => item.title && item.description);
}

export async function updateNewsList(newsItems) {
    const container = document.getElementById('newsContainer');
    container.innerHTML = '';
    
    newsItems.forEach(item => {
        const element = createNewsElement(item);
        if (element) {
            const wrapper = document.createElement('div');
            wrapper.className = 'news-item';
            wrapper.appendChild(element);
            container.appendChild(wrapper);
        }
    });
}