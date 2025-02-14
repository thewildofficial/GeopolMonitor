import { initTheme } from './modules/theme.js';
import { initWebSocket } from './modules/websocket.js';
import { getCountryCoordinates, normalizeCountryName, getCountryFlag, getCountryCode, normalizeCountry, isCountryMatch } from './modules/countries.js';

// Global variables and utility functions
let map;
let heatLayer;
let newsMarkers = new Map();
let activeCountryLayer = null;
const newsPoints = [];
let activeRegionsCount = 0;
let todayEventsCount = 0;
let allNews = [];

const formatDate = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
};

// Load Leaflet.heat plugin
const loadHeatPlugin = () => {
    return new Promise((resolve) => {
        const script = document.createElement('script');
        script.src = 'https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js';
        script.onload = resolve;
        document.head.appendChild(script);
    });
};

async function initMap() {
    // Wait for the heatmap plugin to load
    await loadHeatPlugin();
    setupMap();
}

function setupMap() {
    map = L.map('worldMap', {
        zoomControl: true,
        attributionControl: false,  // Remove attribution
        minZoom: 2,
        maxZoom: 6
    }).setView([30, 0], 2);
    
    // Add minimalistic tile layer with country borders only
    const lightTiles = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors, © CARTO'
    });
    
    const darkTiles = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors, © CARTO'
    });
    
    // Load GeoJSON data for countries
    fetch('https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson')
        .then(response => response.json())
        .then(data => {
            L.geoJSON(data, {
                style: {
                    weight: 1,
                    color: 'var(--border-color)',
                    fillOpacity: 0
                },
                onEachFeature: function(feature, layer) {
                    layer.on('click', function() {
                        let countryName = feature.properties.ADMIN || feature.properties.name;
                        highlightCountry(feature);
                        showCountryNews(countryName);
                    });
                }
            }).addTo(map);
        });
    
    // Set initial tile layer based on theme
    const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
    (isDarkMode ? darkTiles : lightTiles).addTo(map);
    
    // Listen for theme changes
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.attributeName === 'data-theme') {
                const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
                map.removeLayer(isDark ? lightTiles : darkTiles);
                map.addLayer(isDark ? darkTiles : lightTiles);
            }
        });
    });
    
    observer.observe(document.documentElement, { attributes: true });
    
    // Initialize heatmap with proper configuration
    if (typeof L.heatLayer === 'function') {
        heatLayer = L.heatLayer([], {
            radius: 30,
            blur: 20,
            maxZoom: 6,
            max: 1.0,
            minOpacity: 0.3,
            gradient: {
                0.1: 'rgba(52, 152, 219, 0.5)',  // Light blue
                0.3: 'rgba(46, 204, 113, 0.6)',  // Green
                0.5: 'rgba(241, 196, 15, 0.7)',  // Yellow
                0.7: 'rgba(230, 126, 34, 0.8)',  // Orange
                0.9: 'rgba(231, 76, 60, 0.9)'    // Red
            }
        }).addTo(map);
    } else {
        console.error('Leaflet.heat plugin not loaded properly');
    }
    
    // Add custom map controls with improved legend
    const mapControls = L.control({ position: 'bottomright' });
    mapControls.onAdd = function() {
        const div = L.DomUtil.create('div', 'heat-map-legend');
        div.innerHTML = `
            <strong>News Intensity</strong>
            <div class="intensity-scale"></div>
            <div class="scale-labels">
                <span>Low</span>
                <span>High</span>
            </div>
        `;
        return div;
    };
    mapControls.addTo(map);
    
    // Disable map zoom when scrolling
    map.scrollWheelZoom.disable();
    map.on('focus', () => { map.scrollWheelZoom.enable(); });
    map.on('blur', () => { map.scrollWheelZoom.disable(); });
    
    initTimelineSlider();
    fetchNews();
}

function highlightCountry(feature) {
    // Remove previous highlight if it exists
    if (activeCountryLayer) {
        map.removeLayer(activeCountryLayer);
    }
    
    // Create new highlight layer
    activeCountryLayer = L.geoJSON(feature, {
        style: {
            className: 'country-highlight'
        }
    }).addTo(map);
    
    // Fit map to country bounds with padding
    map.fitBounds(activeCountryLayer.getBounds(), {
        padding: [50, 50],
        maxZoom: 6
    });
}

function showCountryNews(countryName) {
    const newsPanel = document.querySelector('.country-news-panel');
    const newsList = document.getElementById('countryNewsList');
    const normalizedCountry = normalizeCountry(countryName);
    
    // Ensure panel is visible and interactive
    newsPanel.style.display = 'flex';
    newsPanel.style.pointerEvents = 'auto';
    
    // Set country name and flag
    document.getElementById('selectedCountry').innerHTML = `${normalizedCountry.flag} ${normalizedCountry.name}`;
    
    // Clear existing news
    newsList.innerHTML = '';
    
    // Filter news for this country
    const countryNews = allNews.filter(item => 
        item.tags.some(tag => 
            tag.category === 'geography' && 
            isCountryMatch(tag.name, countryName)
        )
    );
    
    if (countryNews.length === 0) {
        newsList.innerHTML = '<div class="no-news">No news available for this country</div>';
    } else {
        countryNews.forEach(news => {
            const newsItem = document.createElement('div');
            newsItem.className = 'country-news-item';
            newsItem.innerHTML = `
                <h3>${news.title}</h3>
                <p>${news.description || 'No description available'}</p>
                <div class="meta">
                    <span>${formatDate(news.timestamp)}</span>
                    <span>${news.tags.find(t => t.category === 'source')?.name || 'Unknown Source'}</span>
                </div>
            `;
            newsItem.addEventListener('click', (e) => {
                e.stopPropagation();
                window.open(news.link, '_blank', 'noopener');
            });
            newsList.appendChild(newsItem);
        });
    }
    
    // Add visible class after a short delay for animation
    requestAnimationFrame(() => {
        newsPanel.classList.add('visible');
    });
    
    // Handle close button click with proper event handling
    const closeBtn = document.getElementById('closeCountryNews');
    if (closeBtn) {
        const newCloseBtn = closeBtn.cloneNode(true);
        closeBtn.parentNode.replaceChild(newCloseBtn, closeBtn);
        
        newCloseBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            closePanel();
        });
    }
    
    // Handle clicking outside with proper event handling
    const handleOutsideClick = (e) => {
        if (!newsPanel.contains(e.target) && 
            !e.target.closest('.leaflet-container') &&
            newsPanel.classList.contains('visible')) {
            closePanel();
        }
    };
    
    // Clean up old event listener and add new one
    document.removeEventListener('click', handleOutsideClick);
    document.addEventListener('click', handleOutsideClick);
    
    // Function to handle panel closing
    function closePanel() {
        newsPanel.classList.remove('visible');
        newsPanel.style.pointerEvents = 'none';
        
        setTimeout(() => {
            newsPanel.style.display = 'none';
            if (activeCountryLayer) {
                map.removeLayer(activeCountryLayer);
                activeCountryLayer = null;
            }
            map.setView([30, 0], 2);
        }, 300);
    }
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

async function fetchNews() {
    try {
        const response = await fetch('/api/news');
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();
        if (data.news) {
            allNews = data.news; // Store all news
            updateMap(data.news);
        }
    } catch (error) {
        console.error('Error fetching news:', error);
    }
}

function updateMap(news) {
    clearMap();
    
    const regions = new Set();
    const today = new Date();
    let todayEvents = 0;
    
    // Group news by country to avoid overlapping points
    const countryIntensities = new Map();
    
    news.forEach(item => {
        if (item.tags) {
            const geoTags = item.tags.filter(tag => tag.category === 'geography');
            geoTags.forEach(tag => {
                const coords = getCountryCoordinates(tag.name);
                if (coords) {
                    const key = coords.join(',');
                    const age = (new Date() - new Date(item.timestamp)) / (1000 * 60 * 60); // hours
                    const intensity = Math.max(0.3, 1 - (age / 72)); // Decrease intensity over 72 hours
                    
                    if (!countryIntensities.has(key)) {
                        countryIntensities.set(key, { coords, intensity, count: 0 });
                    }
                    
                    const country = countryIntensities.get(key);
                    country.intensity = Math.max(country.intensity, intensity);
                    country.count++;
                    
                    regions.add(tag.name);
                    
                    if (new Date(item.timestamp).toDateString() === today.toDateString()) {
                        todayEvents++;
                    }
                }
            });
        }
    });
    
    // Add points to heatmap with weighted intensities
    countryIntensities.forEach(({ coords, intensity, count }) => {
        // Adjust intensity based on news count
        const adjustedIntensity = Math.min(1, intensity * (1 + Math.log(count) / 2));
        newsPoints.push([coords[0], coords[1], adjustedIntensity]);
    });
    
    // Update stats
    activeRegionsCount = regions.size;
    todayEventsCount = todayEvents;
    updateStatsDisplay();
    
    // Update heatmap with accumulated points
    if (heatLayer) {
        heatLayer.setLatLngs(newsPoints);
    }
}

function updateStatsDisplay() {
    document.getElementById('activeRegions').textContent = activeRegionsCount;
    document.getElementById('todayEvents').textContent = todayEventsCount;
}

function clearMap() {
    newsMarkers.forEach(marker => marker.remove());
    newsMarkers.clear();
    newsPoints.length = 0;
    heatLayer.setLatLngs([]);
}

function createPopupContent(newsItem) {
    const div = document.createElement('div');
    div.className = 'news-preview';
    div.innerHTML = `
        <h4>${newsItem.title}</h4>
        <p>${newsItem.description?.substring(0, 100) || ''}...</p>
    `;
    div.addEventListener('click', () => {
        window.open(newsItem.link, '_blank', 'noopener');
    });
    return div;
}

// ... [existing coordinate extraction functions from map.js] ...

function updateTimeFilter(days) {
    const now = new Date();
    const cutoff = new Date(now - days * 24 * 60 * 60 * 1000);
    
    let visibleRegions = 0;
    let visibleTodayEvents = 0;
    
    newsMarkers.forEach((marker, link) => {
        const newsItem = Array.from(newsMarkers.keys()).find(item => item.link === link);
        if (newsItem) {
            const itemDate = new Date(newsItem.timestamp);
            const isVisible = itemDate >= cutoff;
            marker.setOpacity(isVisible ? 1 : 0.2);
            
            if (isVisible) {
                visibleRegions++;
                if (itemDate.toDateString() === now.toDateString()) {
                    visibleTodayEvents++;
                }
            }
        }
    });
    
    // Update stats for visible items
    document.getElementById('activeRegions').textContent = visibleRegions;
    document.getElementById('todayEvents').textContent = visibleTodayEvents;
}

// Update marker and popup styles
function addNewsMarker(newsItem, coords) {
    const markerOptions = {
        radius: 8,
        fillColor: getMarkerColor(newsItem),
        color: 'var(--border-color)',
        weight: 1,
        opacity: 1,
        fillOpacity: 0.6
    };
    
    const marker = L.circleMarker(coords, markerOptions)
        .bindPopup(createPopupContent(newsItem))
        .addTo(map);
    
    newsMarkers.set(newsItem.link, marker);
}

function getMarkerColor(newsItem) {
    // Color based on news category or age
    const hours = (new Date() - new Date(newsItem.timestamp)) / (1000 * 60 * 60);
    if (hours < 6) return '#e74c3c';  // Very recent - red
    if (hours < 24) return '#f1c40f'; // Last 24h - yellow
    return '#3498db';                 // Older - blue
}

// Initialize everything when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initWebSocket();
    initMap();
});