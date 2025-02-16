import { initTheme } from './modules/theme.js';
import { initWebSocket } from './modules/websocket.js';

let map;
let heatLayer;
let newsMarkers = new Map();
let activeCountryLayer = null;
const newsPoints = [];
let activeRegionsCount = 0;
let todayEventsCount = 0;
let allNews = []; // Store all news for filtering

function initMap() {
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
    
    // Initialize heatmap with more subtle colors
    heatLayer = L.heatLayer([], {
        radius: 25,
        blur: 15,
        maxZoom: 6,
        gradient: {
            0.2: 'rgba(52, 152, 219, 0.3)',  // Blue, more transparent
            0.4: 'rgba(46, 204, 113, 0.4)',  // Green
            0.6: 'rgba(241, 196, 15, 0.5)',  // Yellow
            0.8: 'rgba(231, 76, 60, 0.6)'    // Red
        }
    }).addTo(map);
    
    // Add custom map controls
    const mapControls = L.control({ position: 'bottomright' });
    mapControls.onAdd = function() {
        const div = L.DomUtil.create('div', 'heat-map-legend');
        div.innerHTML = `
            <strong>News Intensity</strong><br>
            <span style="color: rgba(231, 76, 60, 0.8)">■</span> High<br>
            <span style="color: rgba(241, 196, 15, 0.7)">■</span> Medium<br>
            <span style="color: rgba(46, 204, 113, 0.6)">■</span> Low
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
    const countryTitle = document.getElementById('selectedCountry');
    const newsList = document.getElementById('countryNewsList');
    
    countryTitle.textContent = countryName;
    newsList.innerHTML = '';
    
    // Normalize country names for comparison
    const normalizeCountry = (name) => {
        const specialCases = {
            'United States of America': 'United States',
            'USA': 'United States',
            'United Kingdom': 'United Kingdom',
            'UK': 'United Kingdom',
            'Russian Federation': 'Russia',
        };
        
        return specialCases[name] || name;
    };

    const normalizedCountryName = normalizeCountry(countryName);
    
    // Filter news items for the selected country with more flexible matching
    const countryNews = allNews.filter(item => 
        item.tags.some(tag => 
            tag.category === 'geography' && 
            normalizeCountry(tag.name).toLowerCase() === normalizedCountryName.toLowerCase()
        )
    );
    
    if (countryNews.length === 0) {
        newsList.innerHTML = '<p class="no-news">No news available for this country.</p>';
    } else {
        countryNews.forEach(news => {
            const newsItem = document.createElement('div');
            newsItem.className = 'country-news-item';
            newsItem.innerHTML = `
                <h3>${news.title}</h3>
                <p>${news.description}</p>
                <div class="meta">
                    <span>${formatDate(news.timestamp)}</span>
                </div>
            `;
            newsItem.addEventListener('click', () => {
                window.open(news.link, '_blank', 'noopener');
            });
            newsList.appendChild(newsItem);
        });
    }
    
    newsPanel.style.display = 'flex';
}

function formatDate(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
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

async function fetchNews() {
    try {
        const response = await fetch('/api/news');
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();
        if (data.news) {
            allNews = data.news; // Store all news
            updateMap(data.news);
            updateStats(data.news);
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
    
    news.forEach(item => {
        const coords = extractCoordinates(item);
        if (coords) {
            addNewsMarker(item, coords);
            newsPoints.push([coords[0], coords[1], 1]);
            regions.add(coords.join(','));
            
            const itemDate = new Date(item.timestamp);
            if (itemDate.toDateString() === today.toDateString()) {
                todayEvents++;
            }
        }
    });
    
    // Update stats
    activeRegionsCount = regions.size;
    todayEventsCount = todayEvents;
    updateStatsDisplay();
    
    // Update heatmap
    heatLayer.setLatLngs(newsPoints);
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