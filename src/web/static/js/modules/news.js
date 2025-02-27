import { normalizeCountry, isCountryMatch } from './countries.js';
import { SentimentPanel } from './sentiment-panel.js';
import { setLoading } from './ui-utils.js';

// Add this function at the beginning of news.js
function updateDebugInfo(message, data = null) {
  const debugContent = document.getElementById('debugContent');
  if (!debugContent) return;
  
  const messageElement = document.createElement('div');
  messageElement.style.marginBottom = '10px';
  messageElement.style.borderBottom = '1px solid #555';
  messageElement.style.paddingBottom = '5px';
  
  let content = `<strong>${new Date().toLocaleTimeString()}</strong>: ${message}`;
  
  if (data) {
    try {
      // For objects, add a formatted display
      if (typeof data === 'object') {
        content += `<pre style="overflow: auto; max-height: 200px;">${JSON.stringify(data, null, 2)}</pre>`;
      } else {
        content += `<div>${data}</div>`;
      }
    } catch (e) {
      content += `<div>Error displaying data: ${e.message}</div>`;
    }
  }
  
  messageElement.innerHTML = content;
  debugContent.appendChild(messageElement);
  
  // Keep only the latest 10 messages
  while (debugContent.children.length > 10) {
    debugContent.removeChild(debugContent.firstChild);
  }
}

// Move getSentimentLabel out of createNewsElement to make it accessible globally
function getSentimentLabel(score) {
    if (score >= 0.6) return 'Positive';
    if (score <= -0.6) return 'Negative';
    if (score >= 0.2) return 'Somewhat Positive';
    if (score <= -0.2) return 'Somewhat Negative';
    return 'Neutral';
}

// Move getBiasIcon out of createNewsElement to make it accessible globally
function getBiasIcon(score) {
    if (score >= 0.7) return '⚠️';
    if (score >= 0.4) return '⚡';
    return '✓';
}

// Create a class for the BiasContext tooltip
class BiasContextTooltip {
    constructor() {
        this.tooltips = new Map();
        this.init();
    }

    init() {
        // Clean up old tooltips on initialization
        document.querySelectorAll('.bias-context-tooltip').forEach(el => el.remove());
    }

    createTooltipElement(id) {
        const tooltip = document.createElement('div');
        tooltip.className = 'bias-context-tooltip';
        tooltip.id = `bias-tooltip-${id}`;
        tooltip.style.opacity = '0';
        tooltip.style.visibility = 'hidden';
        tooltip.style.pointerEvents = 'none';
        document.body.appendChild(tooltip);
        return tooltip;
    }

    show(biasData, targetRect, elementId) {
        let tooltip = this.tooltips.get(elementId);
        if (!tooltip) {
            tooltip = this.createTooltipElement(elementId);
            this.tooltips.set(elementId, tooltip);
        }
        
        // Update tooltip content
        tooltip.innerHTML = `
            <div class="bias-tooltip-header">
                <span>Additional Context</span>
                <div class="bias-tooltip-category">${biasData.category || 'neutral'}</div>
            </div>
            <div class="bias-tooltip-content">
                <div class="bias-tooltip-score">
                    <div class="bias-meter">
                        <div class="bias-meter-fill" style="width: ${Math.min(100, Math.max(0, biasData.score * 100))}%"></div>
                    </div>
                    <div class="bias-score-label">${getBiasLabel(biasData.score)}</div>
                </div>
                <div class="bias-tooltip-desc">
                    <p>This content may reflect a ${biasData.category || 'neutral'} perspective.</p>
                </div>
            </div>
            <div class="bias-tooltip-footer">
                <span>Hover over bias indicators to see context</span>
            </div>
        `;

        // Position tooltip near the bias indicator
        const tooltipRect = tooltip.getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        const viewportWidth = window.innerWidth;

        // Calculate initial position (center-aligned with target, below it)
        let top = targetRect.bottom + window.scrollY + 10;
        let left = targetRect.left + (targetRect.width / 2) - (tooltipRect.width / 2);

        // Check if tooltip would go off bottom of screen
        if (top + tooltipRect.height > viewportHeight + window.scrollY) {
            // Position above the target instead
            top = targetRect.top + window.scrollY - tooltipRect.height - 10;
        }

        // Check horizontal bounds
        if (left < 10) left = 10;
        if (left + tooltipRect.width > viewportWidth - 10) {
            left = viewportWidth - tooltipRect.width - 10;
        }

        // Apply position
        tooltip.style.top = `${top}px`;
        tooltip.style.left = `${left}px`;

        // Show with animation
        tooltip.style.opacity = '0';
        tooltip.style.transform = 'translateY(10px)';
        tooltip.style.visibility = 'visible';
        tooltip.style.pointerEvents = 'auto';
        
        // Trigger reflow
        tooltip.offsetHeight;
        
        // Apply transition
        tooltip.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
        tooltip.style.opacity = '1';
        tooltip.style.transform = 'translateY(0)';
    }

    hide(elementId) {
        const tooltip = this.tooltips.get(elementId);
        if (tooltip) {
            tooltip.style.opacity = '0';
            tooltip.style.transform = 'translateY(5px)';
            tooltip.style.pointerEvents = 'none';
            
            setTimeout(() => {
                tooltip.style.visibility = 'hidden';
            }, 200);
        }
    }

    cleanup() {
        this.tooltips.forEach(tooltip => tooltip.remove());
        this.tooltips.clear();
    }
}

// Create singleton instance
const biasTooltip = new BiasContextTooltip();

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
    // More detailed logging
    console.log('Creating news element for:', {
        title: newsItem.title,
        description: newsItem.description?.substring(0, 50) + '...',
        tags: newsItem.tags,
        template_exists: document.getElementById('newsItemTemplate') !== null
    });
    
    // Use content as fallback for missing description
    if (!newsItem.description && newsItem.content) {
        newsItem.description = newsItem.content.split('.')[0] + '.';
    }
    
    if (!newsItem.description) {
        console.warn('Skipping news item with no description or content:', newsItem.title);
        return null;
    }
    
    if (!newsItem.tags) {
        console.warn('News item missing tags property:', newsItem);
        newsItem.tags = [];
    }
    
    const template = document.getElementById('newsItemTemplate');
    if (!template) {
        console.error('News item template not found in the document!');
        return null;
    }
    
    // More detailed structure inspection
    const element = template.content.cloneNode(true);
    console.log('Template structure:', {
        article: element.querySelector('article') !== null,
        image_container: element.querySelector('.news-image-container') !== null,
        image: element.querySelector('.news-image') !== null,
        title_container: element.querySelector('h2') !== null,
        description: element.querySelector('.description') !== null,
        meta: element.querySelector('.meta') !== null,
        time: element.querySelector('.time') !== null,
        tags: element.querySelector('.tags') !== null
    });
    
    const article = element.querySelector('article');
    
    if (!article) {
        console.error('Article element not found in template!');
        return null;
    }
    
    const imageContainer = article.querySelector('.news-image-container');
    const image = article.querySelector('.news-image');
    
    // Format title with emojis
    const titleText = newsItem.title || "Untitled";
    const emoji1 = newsItem.emoji1 || "📰";
    const emoji2 = newsItem.emoji2 || "🌐";
    const titleWithEmojis = `${emoji1}${emoji2} ${titleText}`;
    
    let description = newsItem.description;
    if (description && description.length > 300) {
        const sentences = description.split('.');
        description = sentences.slice(0, 3)
            .map(s => s.trim())
            .filter(s => s.length > 0)
            .join('. ') + '.';
    }
    
    // Add sentiment indicator
    const titleContainer = article.querySelector('h2');
    if (!titleContainer) {
        console.error('Title container (h2) not found in template!');
        return null;
    }
    
    // Set the title text
    titleContainer.textContent = titleWithEmojis;
    
    // Add sentiment indicator if available
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
        
        // Generate unique ID
        const safeLink = newsItem.link ? encodeURIComponent(newsItem.link.replace(/[^a-zA-Z0-9]/g, '')) : '';
        const timestamp = Date.now();
        const uniqueId = `bias-${safeLink}-${timestamp}`;
        
        biasWrapper.className = 'bias-wrapper has-tooltip';
        biasWrapper.id = uniqueId;
        biasWrapper.setAttribute('data-bias-id', uniqueId);
        biasWrapper.setAttribute('aria-label', 'Show bias context');
        biasWrapper.setAttribute('tabindex', '0');
        
        const biasIcon = document.createElement('span');
        biasIcon.className = 'bias-icon';
        biasIcon.textContent = getBiasIcon(newsItem.bias_score);
        
        const biasLabel = document.createElement('span');
        biasLabel.className = 'bias-label';
        biasLabel.textContent = getBiasLabel(newsItem.bias_score);
        
        const biasScore = document.createElement('span');
        biasScore.className = 'bias-score';
        biasScore.textContent = `${Math.round(newsItem.bias_score * 100)}%`;
        
        biasWrapper.appendChild(biasIcon);
        biasWrapper.appendChild(biasLabel);
        biasWrapper.appendChild(biasScore);
        
        // Add hover effect for bias context tooltip
        biasWrapper.addEventListener('mouseenter', (e) => {
            const rect = biasWrapper.getBoundingClientRect();
            biasTooltip.show({
                score: newsItem.bias_score,
                category: newsItem.bias_category
            }, rect, uniqueId);
        });
        
        biasWrapper.addEventListener('mouseleave', () => {
            biasTooltip.hide(uniqueId);
        });
        
        // Add keyboard accessibility
        biasWrapper.addEventListener('focus', (e) => {
            const rect = biasWrapper.getBoundingClientRect();
            biasTooltip.show({
                score: newsItem.bias_score,
                category: newsItem.bias_category
            }, rect, uniqueId);
        });
        
        biasWrapper.addEventListener('blur', () => {
            biasTooltip.hide(uniqueId);
        });
        
        const meta = article.querySelector('.meta');
        if (meta) {
            meta.appendChild(biasWrapper);
        }
    }
    
    // Set description
    const descContainer = article.querySelector('.description');
    if (descContainer) {
        descContainer.textContent = description;
    }
    
    // Set time
    const timeElement = article.querySelector('.time');
    if (timeElement) {
        timeElement.textContent = formatTimeAgo(newsItem.timestamp);
        timeElement.setAttribute('data-timestamp', newsItem.timestamp);
    }
    
    // Handle image
    if (image && imageContainer) {
        const imageUrl = newsItem.image_url || null;
        if (imageUrl) {
            // Use data-src for lazy loading
            image.setAttribute('data-src', imageUrl);
            image.alt = titleText;
            
            // Create and use IntersectionObserver for lazy loading
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        // Only load the image when it comes into view
                        const lazyImage = entry.target;
                        lazyImage.src = lazyImage.dataset.src;
                        observer.unobserve(lazyImage);
                    }
                });
            }, { rootMargin: '200px' });
            
            observer.observe(image);
            imageContainer.style.display = 'block';
        } else {
            imageContainer.style.display = 'none';
        }
        
        // Handle image errors
        image.onerror = () => {
            imageContainer.style.display = 'none';
        };
    }
    
    // Add source to meta section
    const sourceTag = newsItem.tags.find(tag => tag.category === 'source');
    if (sourceTag) {
        const meta = article.querySelector('.meta');
        if (meta) {
            const sourceSpan = document.createElement('span');
            sourceSpan.className = 'source';
            sourceSpan.textContent = sourceTag.name;
            meta.appendChild(sourceSpan);
        }
    }
    
    // Make article clickable
    article.style.cursor = 'pointer';
    article.addEventListener('click', (e) => {
        e.preventDefault();
        window.open(newsItem.link, '_blank', 'noopener');
    });
    
    // Add tags
    const tagsContainer = article.querySelector('.tags');
    if (tagsContainer && newsItem.tags && newsItem.tags.length > 0) {
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

export function formatDate(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleDateString(undefined, {
        year: 'numeric', 
        month: 'short', 
        day: 'numeric'
    });
}

// Filter news by country with flexible matching
function filterNewsByCountry(countryData) {
    return allLoadedNews.filter(item => {
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

export async function fetchNews(tagParam = '', page = 1, pageSize = 20) {
    if (isLoading || (!hasMorePages && page > 1)) return null;
    
    isLoading = true;
    updateDebugInfo('Fetching news...', { tagParam, page, pageSize });
    
    try {
        // Build query params for pagination
        const params = new URLSearchParams();
        if (tagParam) {
            params.append('tags', tagParam.replace('?tags=', ''));
        }
        params.append('page', page);
        params.append('page_size', pageSize);
        
        const url = `/api/news?${params.toString()}`;
        console.log(`Fetching news from: ${url}`);
        
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        updateDebugInfo('API Response:', data);
        
        // Check if we got valid data
        if (!data.news || !Array.isArray(data.news)) {
            throw new Error('Invalid news data format received from API');
        }
        
        // Update pagination state
        hasMorePages = data.pagination?.has_next || false;
        
        isLoading = false;
        return data;
    } catch (error) {
        console.error('Error fetching news:', error);
        updateDebugInfo('Error fetching news:', error.message);
        isLoading = false;
        throw error; // Re-throw to handle in calling function
    }
}

export async function filterNews(news) {
    return news.filter(item => {
        // Only require title, use content as fallback for description
        if (!item.title) return false;
        if (!item.description && item.content) {
            item.description = item.content.split('.')[0] + '.'; // Use first sentence of content
        }
        return true;
    });
}

// Add this function to help with debugging news display issues
export async function updateNewsList(newsItems, append = false) {
    const container = document.getElementById('newsContainer');
    
    if (!container) {
        console.error('newsContainer element not found in DOM');
        return;
    }
    
    // Log the first item for debugging
    if (newsItems && newsItems.length > 0) {
        console.log('First news item:', {
            title: newsItems[0].title,
            description: newsItems[0].description?.substring(0, 100) + '...',
            timestamp: newsItems[0].timestamp,
            tags: newsItems[0].tags
        });
    } else {
        console.log('No news items to display');
        if (!append) {
            container.innerHTML = `
                <div class="no-results" style="text-align: center; padding: 2rem;">
                    <i class="fas fa-newspaper" style="font-size: 2rem; margin-bottom: 1rem;"></i>
                    <p>No news articles available</p>
                </div>
            `;
        }
        return;
    }
    
    // Only clear if not appending
    if (!append) {
        container.innerHTML = '';
        allLoadedNews = [];
    }
    
    // Add to global store
    allLoadedNews = [...allLoadedNews, ...newsItems];
    
    // Create document fragment for better performance
    const fragment = document.createDocumentFragment();
    
    newsItems.forEach((item, index) => {
        try {
            if (!item.title || !item.description) {
                console.warn('Skipping item - missing required fields:', item);
                return;
            }
            
            const newsItem = document.createElement('div');
            newsItem.className = 'news-item fade-in';
            newsItem.style.animationDelay = `${index * 0.1}s`; // Add staggered delay
            
            const article = document.createElement('article');
            article.style.backgroundColor = 'var(--card-background)';
            article.style.color = 'var(--text-color)';
            
            // Format title with emojis
            const emoji1 = item.emoji1 || '📰';
            const emoji2 = item.emoji2 || '🌐';
            
            article.innerHTML = `
                <div class="news-content">
                    ${item.image_url ? `
                        <div class="news-image-container">
                            <img class="news-image" src="${item.image_url}" alt="${item.title}" loading="lazy">
                        </div>
                    ` : ''}
                    <div class="news-text">
                        <div class="news-header">
                            <h2>
                                ${emoji1}${emoji2} ${item.title}
                                ${item.sentiment_score !== undefined ? `
                                    <span class="sentiment-wrapper" 
                                          title="Sentiment score: ${Math.round(item.sentiment_score * 100)}%">
                                        <span class="sentiment-indicator" 
                                              style="background-color: ${getSentimentColor(item.sentiment_score)}">
                                        </span>
                                        <span class="sentiment-label">${getSentimentLabel(item.sentiment_score)}</span>
                                    </span>
                                ` : ''}
                            </h2>
                            <div class="tags">
                                ${item.tags?.filter(tag => tag.category !== 'source')
                                    .map(tag => `
                                        <span class="tag-in-article" 
                                              data-category="${tag.category}"
                                              data-tag="${tag.name}">
                                            ${tag.category === 'geography' 
                                                ? `${normalizeCountry(tag.name).flag || ''} ${tag.name}`
                                                : tag.name}
                                        </span>
                                    `).join('') || ''}
                            </div>
                        </div>
                        <p class="description">${item.description}</p>
                        <div class="meta">
                            <span class="time" data-timestamp="${item.timestamp}">
                                ${formatTimeAgo(item.timestamp)}
                            </span>
                            ${item.tags?.find(t => t.category === 'source')?.name 
                                ? `<span class="source">${item.tags.find(t => t.category === 'source').name}</span>` 
                                : ''}
                            
                            ${item.bias_score !== undefined ? `
                                <span class="bias-wrapper" title="Bias score: ${Math.round(item.bias_score * 100)}%">
                                    <span class="bias-icon">${getBiasIcon(item.bias_score)}</span>
                                    <span class="bias-label">${getBiasLabel(item.bias_score)}</span>
                                </span>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
            
            // Add click handlers
            article.style.cursor = 'pointer';
            article.addEventListener('click', () => {
                window.open(item.link, '_blank', 'noopener');
            });
            
            // Add tag click handlers
            article.querySelectorAll('.tag-in-article').forEach(tagEl => {
                tagEl.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (window.toggleTag) {
                        window.toggleTag(tagEl.dataset.tag);
                    }
                });
            });
            
            newsItem.appendChild(article);
            fragment.appendChild(newsItem);
            
        } catch (err) {
            console.error('Error rendering news item:', err, item);
        }
    });
    
    container.appendChild(fragment);
    
    // Let the browser render the items before removing the loading state
    requestAnimationFrame(() => {
        document.body.classList.remove('loading');
        setLoading(false);
    });
    
    // Add scroll sentinel for infinite scroll if this is the first load
    if (!append) {
        const sentinel = document.createElement('div');
        sentinel.id = 'scroll-sentinel';
        container.appendChild(sentinel);
    }
}

let currentPage = 1;
let isLoading = false;
let hasMorePages = true;
let allLoadedNews = [];
let activeTagFilter = '';

export function setActiveTagFilter(tagParam) {
    activeTagFilter = tagParam;
    loadInitialNews(tagParam);
}

export async function initInfiniteScroll() {
    const sentinel = document.createElement('div');
    sentinel.id = 'scroll-sentinel';
    document.getElementById('newsContainer').appendChild(sentinel);

    const observer = new IntersectionObserver(async (entries) => {
        entries.forEach(async (entry) => {
            if (entry.isIntersecting && !isLoading && hasMorePages) {
                currentPage++;
                const activeTags = window.getActiveTags?.() || [];
                const tagParam = activeTags.length > 0 ? `?tags=${activeTags.join(',')}` : '';
                
                try {
                    const data = await fetchNews(tagParam, currentPage);
                    if (data && data.news) {
                        const filteredNews = await filterNews(data.news);
                        await updateNewsList(filteredNews, true); // true for append mode
                    }
                } catch (error) {
                    console.error('Error loading more news:', error);
                }
            }
        });
    }, {
        root: null,
        rootMargin: '100px',
        threshold: 0.1
    });

    observer.observe(sentinel);
}

export async function loadInitialNews(tagParam = '') {
    currentPage = 1;
    hasMorePages = true;
    
    try {
        const data = await fetchNews(tagParam, currentPage);
        if (data && data.news) {
            const filteredNews = await filterNews(data.news);
            await updateNewsList(filteredNews, false); // false for replace mode
        }
    } catch (error) {
        console.error('Error loading initial news:', error);
    }
}

// Add cleanup on page unload
window.addEventListener('unload', () => {
    biasTooltip.cleanup();
});