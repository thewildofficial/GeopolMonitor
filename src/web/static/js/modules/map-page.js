import { initTheme } from './theme.js';
import { initWebSocket } from './websocket.js';
import { normalizeCountryName, getCountryFlag, getCountryCode } from './countries.js';
import { initHeatmap, updateHeatmap, updateTheme as updateHeatmapTheme } from './heatmap.js';
import { loadCountryData } from './countries.js';
import { mapDataCache } from './map-data-cache.js';

// Global variables and utility functions
let map;
let activeCountryLayer = null;
let activeRegionsCount = 0;
let todayEventsCount = 0;
let allNews = [];
let countryStats = null;

const formatDate = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
};

async function initMap() {
    console.log('Initializing map...');
    await loadCountryData();
    setupMap();
    await initWebSocket();
}

function setupMap() {
    // Set maximum bounds to prevent infinite scrolling
    const maxBounds = L.latLngBounds(
        L.latLng(-85, -180),  // Southwest corner
        L.latLng(85, 180)     // Northeast corner
    );
    
    map = L.map('worldMap', {
        zoomControl: true,
        attributionControl: false,
        minZoom: 2,
        maxZoom: 6,
        maxBounds: maxBounds,
        maxBoundsViscosity: 1.0,  // Makes the bounds completely solid
        zoomSnap: 0.25,           // Smoother zoom with smaller increments
        zoomDelta: 0.5,           // Smoother mouse wheel zooming
        wheelPxPerZoomLevel: 120  // Slower mouse wheel zoom for more control
    }).setView([30, 0], 2);
    
    // Add tile layers
    const lightTiles = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors, © CARTO'
    });
    
    const darkTiles = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors, © CARTO'
    });
    
    const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
    (isDarkMode ? darkTiles : lightTiles).addTo(map);
    
    // First initialize heatmap layer, then fetch data
    initHeatmap(map).then(() => {
        // Immediately fetch news stats after heatmap is initialized
        fetchNewsStats().then(() => {
            console.log('Map data loaded successfully');
        }).catch(err => {
            console.error('Error loading map data:', err);
            // If stats fail, try regular news
            fetchNews();
        });
        
        // Listen for country clicks
        map.on('countryclick', (e) => {
            highlightCountry(e.feature, e.countryName);
        });
    }).catch(error => {
        console.error('Failed to initialize heatmap:', error);
    });
    
    // Listen for theme changes
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.attributeName === 'data-theme') {
                const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
                map.removeLayer(isDark ? lightTiles : darkTiles);
                map.addLayer(isDark ? darkTiles : lightTiles);
                updateHeatmapTheme(isDark ? 'dark' : 'light');
            }
        });
    });
    
    observer.observe(document.documentElement, { attributes: true });
    
    // Add legend
    const mapControls = L.control({ position: 'bottomright' });
    mapControls.onAdd = () => {
        const div = L.DomUtil.create('div', 'heatmap-legend');
        div.innerHTML = `
            <h4>News Activity</h4>
            <div class="intensity-scale"></div>
            <div class="scale-labels">
                <span>No Activity</span>
                <span>High Activity</span>
            </div>
        `;
        return div;
    };
    mapControls.addTo(map);
    
    initTimelineSlider();
    // Note: We now call fetchNewsStats() inside the initHeatmap().then() callback

    // Initialize close button
    initializeCloseButton();
    
    // Improve map interaction settings
    map.options.wheelPxPerZoomLevel = 120; // Slower mouse wheel zoom
    map.options.zoomSnap = 0.1; // Smoother zoom levels
    map.options.zoomDelta = 0.5; // Smaller zoom steps
    map.options.wheelDebounceTime = 40; // Debounce wheel events
    
    // Enable smooth wheel zoom
    map.scrollWheelZoom.disable();
    map.on('focus', () => { map.scrollWheelZoom.enable(); });
    map.on('blur', () => { map.scrollWheelZoom.disable(); });
}

/**
 * Calculate optimal zoom level and padding based on country size
 * @param {Object} bounds - The L.LatLngBounds object of the country
 * @returns {Object} - Zoom parameters
 */
function calculateZoomParameters(bounds) {
    const area = Math.abs(
        (bounds.getNorth() - bounds.getSouth()) * 
        (bounds.getEast() - bounds.getWest())
    );
    
    // Get screen dimensions to calculate appropriate padding
    const mapContainer = map.getContainer();
    const screenWidth = mapContainer.clientWidth;
    const screenHeight = mapContainer.clientHeight;
    
    // Base padding that works well for average-sized countries
    let padding = [Math.min(50, screenHeight * 0.1), Math.min(50, screenWidth * 0.1)];
    let maxZoom = 6; // Default max zoom
    
    // Adjust padding for very large countries
    if (area > 1000) {
        // For very large countries (like Russia, USA, China)
        padding = [Math.min(10, screenHeight * 0.05), Math.min(10, screenWidth * 0.05)];
        maxZoom = 4;
    } else if (area > 100) {
        // For medium-sized countries
        padding = [Math.min(30, screenHeight * 0.08), Math.min(30, screenWidth * 0.08)];
        maxZoom = 5;
    } else if (area < 5) {
        // For very small countries
        padding = [Math.min(100, screenHeight * 0.2), Math.min(100, screenWidth * 0.2)];
    }
    
    return { padding, maxZoom };
}

/**
 * Highlight a country and smoothly zoom to its bounds
 * @param {Object} feature - GeoJSON feature of the country
 * @param {string} countryName - Name of the country
 */
function highlightCountry(feature, countryName) {
    if (!feature || !countryName) {
        console.error('Invalid feature or country name:', feature, countryName);
        return;
    }

    // Clean up existing active country layer before proceeding
    if (activeCountryLayer) {
        map.removeLayer(activeCountryLayer);
        activeCountryLayer = null;
    }
    
    // Get country bounds directly from the feature
    const bounds = L.geoJSON(feature).getBounds();
    
    // Calculate optimal zoom parameters
    const { padding, maxZoom } = calculateZoomParameters(bounds);
    
    // Create the highlight with a fade-in effect
    activeCountryLayer = L.geoJSON(feature, {
        style: {
            fillColor: '#3388ff',
            weight: 2,
            opacity: 0,
            color: '#3388ff',
            fillOpacity: 0,
            className: 'country-highlight'
        }
    }).addTo(map);
    
    // Animate highlight opacity
    requestAnimationFrame(() => {
        activeCountryLayer.setStyle({
            opacity: 0.8,
            fillOpacity: 0.3
        });
    });
    
    // Calculate the center point and optimal zoom level
    const center = bounds.getCenter();
    const zoom = map.getBoundsZoom(bounds, false, padding);
    
    // First pan to the center, then zoom
    map.once('moveend', () => {
        map.setZoom(Math.min(zoom, maxZoom), {
            animate: true,
            duration: 0.7
        });
    });
    
    map.panTo(center, {
        animate: true,
        duration: 0.7
    });
    
    // Show news panel with animation
    const newsPanel = document.querySelector('.country-news-panel');
    if (newsPanel) {
        newsPanel.style.display = 'flex';
        requestAnimationFrame(() => {
            newsPanel.classList.add('visible');
        });
    }
    
    // Show country news
    showCountryNews(countryName);
}

function showCountryNews(countryName) {
    console.log(`Showing news for country: ${countryName}`);
    
    const newsPanel = document.querySelector('.country-news-panel');
    const countryTitle = document.getElementById('selectedCountry');
    const newsList = document.getElementById('countryNewsList');
    const countryFlag = document.querySelector('.country-flag');
    
    if (!newsPanel || !countryTitle || !newsList || !countryFlag) {
        console.error('Missing DOM elements for news panel');
        return;
    }
    
    const normalizedName = normalizeCountryName(countryName);
    countryTitle.textContent = normalizedName;
    
    // Get and set the country flag for the panel header
    const countryCode = getCountryCode(normalizedName);
    countryFlag.textContent = countryCode ? getCountryFlag(countryCode) : '';
    newsList.innerHTML = '<p class="loading">Loading news for ' + normalizedName + '...</p>';
    
    // Display the news panel with a smooth fade-in animation
    newsPanel.style.opacity = '0';
    newsPanel.style.display = 'flex';
    
    // Use the new country-specific API endpoint
    fetchCountryNews(normalizedName, newsList, newsPanel);
}

/**
 * Fetch news specifically for a country using the dedicated endpoint
 * @param {string} countryName - The country name to fetch news for
 * @param {HTMLElement} newsList - The DOM element to display news in
 * @param {HTMLElement} newsPanel - The news panel container
 */
async function fetchCountryNews(countryName, newsList, newsPanel) {
    try {
        console.log(`Fetching news for country: ${countryName}`);
        
        // Encode the country name for URL safety
        const encodedCountryName = encodeURIComponent(countryName);
        const response = await fetch(`/api/news/country/${encodedCountryName}`);
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const data = await response.json();
        
        console.log(`Received ${data.news?.length || 0} news items for ${countryName}`);
        displayCountryNews(countryName, data.news || [], newsList, newsPanel);
        
        // Show the total count in the panel title
        const totalCount = data.pagination?.total_count || 0;
        const countryTitle = document.getElementById('selectedCountry');
        if (countryTitle) {
            countryTitle.textContent = `${countryName} (${totalCount} articles)`;
        }
        
        // Fade in the panel now that we have content
        setTimeout(() => {
            newsPanel.style.opacity = '1';
        }, 50);
        
    } catch (error) {
        console.error('Error fetching country news:', error);
        newsList.innerHTML = '<p class="error">Failed to load news. Please try again later.</p>';
        
        // Still show the panel even if there's an error
        setTimeout(() => {
            newsPanel.style.opacity = '1';
        }, 50);
    }
}

/**
 * Display news items for a selected country
 * @param {string} countryName - The country name
 * @param {Array} newsItems - Array of news items to display
 * @param {HTMLElement} newsList - DOM element to display news in
 * @param {HTMLElement} newsPanel - The news panel container
 */
function displayCountryNews(countryName, newsItems, newsList, newsPanel) {
    console.log(`Displaying ${newsItems.length} news items for ${countryName}`);
    
    if (newsItems.length === 0) {
        newsList.innerHTML = '<p class="no-news">No news available for this country.</p>';
        return;
    }
    
    // Clear the list and add news items
    newsList.innerHTML = '';
    
    newsItems.forEach(news => {
        const newsItem = document.createElement('div');
        newsItem.className = 'country-news-item';
        
        // Get geography tags and their flags
        const geoTags = (news.tags && Array.isArray(news.tags))
            ? news.tags.filter(tag => tag.category === 'geography' && tag.name)
            : [];
        let flagsHTML = '';
        
        // Get up to two flags for related countries
        if (geoTags.length >= 2) {
            flagsHTML = geoTags.slice(0, 2).map(tag => {
                const normalizedGeo = normalizeCountryName(tag.name);
                const flagCountryCode = getCountryCode(normalizedGeo);
                return flagCountryCode ? getCountryFlag(flagCountryCode) : '';
            }).join(' ');
        } else if (geoTags.length === 1) {
            const normalizedGeo = normalizeCountryName(geoTags[0].name);
            const flagCountryCode = getCountryCode(normalizedGeo);
            flagsHTML = flagCountryCode ? getCountryFlag(flagCountryCode) : '';
        } else {
            // Get the country flag from our current selection
            flagsHTML = document.querySelector('.country-flag')?.textContent || '';
        }
        
        // Get the source tag
        const sourceTag = news.tags.find(tag => tag.category === 'source');
        const sourceHTML = sourceTag ? `<span class="source">${sourceTag.name}</span>` : '';
        
        // Build the news item content with the source in the meta section
        newsItem.innerHTML = `
            <h3>${flagsHTML} ${news.title}</h3>
            <p>${news.description || news.content?.substring(0, 150) || ''}</p>
            <div class="meta">
                <span>${formatDate(news.timestamp)}</span>
                ${sourceHTML}
            </div>
        `;
        
        // Add click event to open news link in a new window
        newsItem.addEventListener('click', () => {
            window.open(news.link, '_blank', 'noopener');
        });
        
        newsList.appendChild(newsItem);
    });
}

function initTimelineSlider() {
    const slider = document.getElementById('timelineSlider');
    const daysValue = document.getElementById('daysValue');
    
    if (!slider || !daysValue) return;
    
    slider.addEventListener('input', (e) => {
        const days = parseInt(e.target.value);
        daysValue.textContent = days;
        updateTimeFilter(days);
    });
}

/**
 * Fetch news statistics for the heatmap
 * @param {Object} options - Optional filter parameters
 * @returns {Promise<Object>} - Statistics data
 */
async function fetchNewsStats(options = {}) {
    try {
        console.log('Fetching news stats...');
        
        // Try to get data from cache first
        const data = await mapDataCache.getCountryStats(options, async (opts) => {
            // Build query string from options
            const params = new URLSearchParams();
            if (opts.tags) params.append('tags', opts.tags);
            if (opts.start_date) params.append('start_date', opts.start_date);
            if (opts.end_date) params.append('end_date', opts.end_date);
            
            const queryString = params.toString();
            const url = `/api/news/stats${queryString ? '?' + queryString : ''}`;
            
            console.log('Fetching news stats from API:', url);
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Received stats data:', data);
            
            if (!data || !data.countries || !Array.isArray(data.countries)) {
                throw new Error('Invalid data format from API');
            }
            
            return data;
        });
        
        // Store for later use
        countryStats = data;
        
        // Update the map with country statistics
        updateMap(data);
        
        // Also fetch detailed news for the news panel
        fetchNews();
        
        return data;
    } catch (error) {
        console.error('Error fetching news stats:', error);
        // If stats fetch fails, try to fall back to normal news fetch
        await fetchNews();
        return null;
    }
}

async function fetchNews() {
    console.log('Fetching news items...');
    
    try {
        const response = await fetch('/api/news');
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Ensure we have an array of news items
        if (data && Array.isArray(data.news)) {
            console.log(`Fetched ${data.news.length} news items`);
            allNews = data.news;
        } else if (Array.isArray(data)) {
            console.log(`Fetched ${data.length} news items (array format)`);
            allNews = data;
        } else {
            console.error('Invalid news data format:', data);
            allNews = [];
        }
        
        // If we don't have country stats yet, use the full news data to update the map
        if (!countryStats) {
            updateMap({ news: allNews });
        }
        
        return allNews;
    } catch (error) {
        console.error('Error fetching news:', error);
        allNews = [];
        if (!countryStats) {
            updateMap({ news: [] });
        }
        throw error;
    }
}

function updateMap(data) {
    // Debug the data structure
    console.log('Update map called with data:', data);
    
    // Handle both formats: country stats or full news data
    if (data && data.countries && Array.isArray(data.countries)) {
        // For new aggregated stats format
        console.log('Updating map with aggregated stats:', data.countries.length, 'countries');
        
        // Debug data sample
        if (data.countries.length > 0) {
            console.log('Sample country data:', data.countries[0]);
        }
        
        // Update the heatmap with country statistics
        updateHeatmap(data.countries, true);
        
        // Update metadata stats
        activeRegionsCount = data.metadata?.total_countries || 0;
        todayEventsCount = data.metadata?.total_articles || 0;
    } else {
        // For legacy full news format
        const news = Array.isArray(data.news) ? data.news : (Array.isArray(data) ? data : []);
        console.log('Updating map with', news.length, 'news items');
        
        updateHeatmap(news, false);
        
        // Calculate stats
        const regions = new Set();
        const today = new Date().toDateString();
        let todayEvents = 0;
        
        news.forEach(item => {
            if (item && item.tags && Array.isArray(item.tags)) {
                const geoTags = item.tags.filter(tag => tag && tag.category === 'geography');
                geoTags.forEach(tag => {
                    regions.add(tag.name);
                    if (new Date(item.timestamp).toDateString() === today) {
                        todayEvents++;
                    }
                });
            }
        });
        
        // Update stats
        activeRegionsCount = regions.size;
        todayEventsCount = todayEvents;
    }
    
    updateStatsDisplay();
}

function updateStatsDisplay() {
    document.getElementById('activeRegions').textContent = activeRegionsCount;
    document.getElementById('todayEvents').textContent = todayEventsCount;
}

function updateTimeFilter(days) {
    const now = new Date();
    const cutoff = new Date(now - days * 24 * 60 * 60 * 1000);
    
    // Use the new stats endpoint with date filtering
    const startDateStr = cutoff.toISOString().split('T')[0]; // YYYY-MM-DD format
    
    fetchNewsStats({
        start_date: startDateStr
    }).catch(err => {
        console.error('Error updating time filter:', err);
        
        // Fallback to client-side filtering if API filtering fails
        const filteredNews = allNews.filter(item => new Date(item.timestamp) >= cutoff);
        updateMap({ news: filteredNews });
    });
}

// Initialize close button functionality
function initializeCloseButton() {
    const closeBtn = document.querySelector('.close-btn');
    const newsPanel = document.querySelector('.country-news-panel');
    
    if (closeBtn && newsPanel) {
        closeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            
            // Remove the visible class to trigger transition
            newsPanel.classList.remove('visible');
            
            // Hide panel after transition
            setTimeout(() => {
                newsPanel.style.display = 'none';
            }, 300);
            
            // Reset country highlight
            if (activeCountryLayer) {
                map.removeLayer(activeCountryLayer);
                activeCountryLayer = null;
            }
            
            // Reset map view smoothly
            map.flyTo([30, 0], 2, {
                duration: 1.2,
                easeLinearity: 0.1
            });
        });
    }
}

// Initialize everything when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initWebSocket();
    initMap();
});