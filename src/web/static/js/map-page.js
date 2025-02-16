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
let countryLayer = null; // Add this to track the country boundaries layer

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
            countryLayer = L.geoJSON(data, {
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

                    // Add mouseover tooltip
                    layer.on('mouseover', function(e) {
                        const countryName = feature.properties.ADMIN || feature.properties.name;
                        const normalizedCountryName = normalizeCountry(countryName);
                        const countryNews = allNews.filter(item => 
                            item.tags.some(tag => 
                                tag.category === 'geography' && 
                                normalizeCountry(tag.name).toLowerCase() === normalizedCountryName.toLowerCase()
                            )
                        );

                        const tooltipContent = `
                            <div class="country-tooltip">
                                <strong>${countryName}</strong>
                                <div>${countryNews.length} news items</div>
                            </div>
                        `;

                        layer.bindTooltip(tooltipContent, {
                            className: `custom-tooltip ${document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light'}`,
                            direction: 'top',
                            permanent: false,
                            sticky: true,
                            opacity: 0.9
                        }).openTooltip(e.latlng);
                    });

                    // Remove tooltip on mouseout
                    layer.on('mouseout', function() {
                        layer.closeTooltip();
                    });
                }
            }).addTo(map);

            // Update tooltips when theme changes
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.attributeName === 'data-theme') {
                        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
                        countryLayer.eachLayer((layer) => {
                            if (layer.getTooltip()) {
                                layer.getTooltip().setClassName(`custom-tooltip ${isDark ? 'dark' : 'light'}`);
                            }
                        });
                    }
                });
            });
            observer.observe(document.documentElement, { attributes: true });
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
    
    fetchNews();

    // Update the close button handler to properly reset the map state
    const closeButton = document.getElementById('closeCountryNews');
    const newsPanel = document.querySelector('.country-news-panel');
    
    closeButton.addEventListener('click', (e) => {
        // Prevent event from bubbling to map
        e.stopPropagation();
        
        // Hide the panel with animation
        newsPanel.style.opacity = '0';
        newsPanel.style.transform = 'translateX(20px)';
        newsPanel.style.pointerEvents = 'none';
        
        // Wait for animation to complete before hiding
        setTimeout(() => {
            newsPanel.style.display = 'none';
            newsPanel.style.zIndex = '-1';
            // Reset transform and opacity for next open
            newsPanel.style.opacity = '';
            newsPanel.style.transform = '';
        }, 300);

        // Reset the active country highlighting
        if (activeCountryLayer) {
            map.removeLayer(activeCountryLayer);
            activeCountryLayer = null;
        }

        // Reset all country styles
        if (countryLayer) {
            countryLayer.eachLayer((layer) => {
                layer.setStyle({
                    weight: 1,
                    color: 'var(--border-color)',
                    fillOpacity: 0
                });
            });
        }
    });
}

function highlightCountry(feature) {
    // Reset previous highlight
    if (activeCountryLayer) {
        map.removeLayer(activeCountryLayer);
        activeCountryLayer = null;
    }
    
    // Reset all country styles first
    if (countryLayer) {
        countryLayer.eachLayer((layer) => {
            layer.setStyle({
                weight: 1,
                color: 'var(--border-color)',
                fillOpacity: 0
            });
        });
    }
    
    // Create new highlight layer
    activeCountryLayer = L.geoJSON(feature, {
        style: {
            weight: 2,
            color: 'var(--accent-color)',
            fillOpacity: 0.2,
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
    
    // Reset panel state before showing
    newsPanel.style.zIndex = '1000';
    newsPanel.style.pointerEvents = 'all';
    
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

async function fetchNews() {
    try {
        const response = await fetch('/api/news');
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();
        if (data.news) {
            allNews = data.news; // Store all news
            updateMap(allNews); // Pass all news directly
            updateStats(allNews);
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
    
    // Process all news items without time filtering
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
    
    // Update stats with all data
    activeRegionsCount = regions.size;
    todayEventsCount = todayEvents;
    updateStatsDisplay();
    
    // Update heatmap with all points
    if (heatLayer && newsPoints.length > 0) {
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