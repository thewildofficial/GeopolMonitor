import { getActiveTags } from './tags.js';

let map;
let heatLayer;
let newsMarkers = new Map();
let currentTimeRange = 'all';
const newsPoints = [];

export function initMap() {
    map = L.map('worldMap').setView([20, 0], 2);
    
    // Add dark/light mode tile layers
    const lightTiles = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    });
    
    const darkTiles = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        className: 'dark-tiles'
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
    
    // Initialize heatmap layer
    heatLayer = L.heatLayer([], {
        radius: 25,
        blur: 15,
        maxZoom: 10,
        gradient: {
            0.4: '#3498db',
            0.6: '#2ecc71',
            0.8: '#f1c40f',
            1.0: '#e74c3c'
        }
    }).addTo(map);
    
    // Add legend
    const legend = L.control({ position: 'bottomright' });
    legend.onAdd = function () {
        const div = L.DomUtil.create('div', 'heat-map-legend');
        div.innerHTML = `
            <strong>News Density</strong><br>
            <span style="color: #e74c3c">■</span> High<br>
            <span style="color: #f1c40f">■</span> Medium<br>
            <span style="color: #2ecc71">■</span> Low
        `;
        return div;
    };
    legend.addTo(map);
    
    // Initialize timeline slider
    initTimelineSlider();
}

function initTimelineSlider() {
    const slider = document.getElementById('timelineSlider');
    if (!slider) return;
    
    slider.addEventListener('input', (e) => {
        const days = parseInt(e.target.value);
        updateTimeFilter(days);
    });
}

export async function updateMap(news) {
    clearMap();
    
    news.forEach(item => {
        const coords = extractCoordinates(item);
        if (coords) {
            addNewsMarker(item, coords);
            newsPoints.push([coords[0], coords[1], 1]); // weight of 1 for heatmap
        }
    });
    
    // Update heatmap
    heatLayer.setLatLngs(newsPoints);
}

function clearMap() {
    newsMarkers.forEach(marker => marker.remove());
    newsMarkers.clear();
    newsPoints.length = 0;
    heatLayer.setLatLngs([]);
}

function addNewsMarker(newsItem, coords) {
    const marker = L.marker(coords)
        .bindPopup(createPopupContent(newsItem))
        .addTo(map);
    
    newsMarkers.set(newsItem.link, marker);
}

function createPopupContent(newsItem) {
    const div = document.createElement('div');
    div.className = 'news-preview';
    div.innerHTML = `
        <h4>${newsItem.title}</h4>
        <p>${newsItem.description.substring(0, 100)}...</p>
    `;
    div.addEventListener('click', () => {
        window.open(newsItem.link, '_blank', 'noopener');
    });
    return div;
}

function extractCoordinates(newsItem) {
    // Extract coordinates from geography tags
    const geoTag = newsItem.tags.find(tag => tag.category === 'geography');
    if (geoTag) {
        const coords = getCoordinatesForLocation(geoTag.name);
        if (coords) return coords;
    }
    
    // Fallback: Try to extract from content
    return extractCoordinatesFromText(newsItem.content);
}

function getCoordinatesForLocation(location) {
    // Simple mapping of common locations to coordinates
    // This should be expanded with a proper geocoding service
    const coordinates = {
        'USA': [37.0902, -95.7129],
        'RUSSIA': [61.5240, 105.3188],
        'CHINA': [35.8617, 104.1954],
        'UK': [55.3781, -3.4360],
        'EUROPE': [54.5260, 15.2551],
        // Add more mappings as needed
    };
    
    return coordinates[location.toUpperCase()];
}

function extractCoordinatesFromText(content) {
    // Implement more sophisticated coordinate extraction
    // This is a placeholder that could be improved with NLP
    return null;
}

function updateTimeFilter(days) {
    const now = new Date();
    const cutoff = new Date(now - days * 24 * 60 * 60 * 1000);
    
    newsMarkers.forEach((marker, link) => {
        const newsItem = Array.from(newsMarkers.keys()).find(item => item.link === link);
        if (newsItem) {
            const itemDate = new Date(newsItem.timestamp);
            marker.setOpacity(itemDate >= cutoff ? 1 : 0.3);
        }
    });
}

export function handleNewsUpdate(newItem) {
    const coords = extractCoordinates(newItem);
    if (coords) {
        addNewsMarker(newItem, coords);
        newsPoints.push([coords[0], coords[1], 1]);
        heatLayer.setLatLngs(newsPoints);
    }
}