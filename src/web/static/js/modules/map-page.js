import { initTheme } from './theme.js';
import { initWebSocket } from './websocket.js';
import { normalizeCountryName, getCountryFlag, getCountryCode } from './countries.js';
import { initHeatmap, updateHeatmap, updateTheme as updateHeatmapTheme } from './heatmap.js';
import {loadCountryData} from './countries.js';

// Global variables and utility functions
let map;
let activeCountryLayer = null;
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

async function initMap() {
    setupMap();
    await initWebSocket();
    await loadCountryData()
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
        maxBoundsViscosity: 1.0  // Makes the bounds completely solid
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
    
    // Initialize the heatmap
    initHeatmap(map).then(() => {
        // Listen for country clicks
        map.on('countryclick', (e) => {
            highlightCountry(e.feature);
            showCountryNews(e.countryName);
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
    fetchNews();
}

function highlightCountry(feature) {
    if (activeCountryLayer) {
        map.removeLayer(activeCountryLayer);
    }
    
    activeCountryLayer = L.geoJSON(feature, {
        style: {
            className: 'country-highlight'
        }
    }).addTo(map);
    
    map.fitBounds(activeCountryLayer.getBounds(), {
        padding: [50, 50],
        maxZoom: 6
    });
}

function showCountryNews(countryName) {
    const newsPanel = document.querySelector('.country-news-panel');
    const countryTitle = document.getElementById('selectedCountry');
    const newsList = document.getElementById('countryNewsList');
    const countryFlag = document.querySelector('.country-flag');

    const normalizedName = normalizeCountryName(countryName);
    countryTitle.textContent = normalizedName;

    // Get and set the country flag for the panel header
    const countryCode = getCountryCode(normalizedName);
    countryFlag.textContent = countryCode ? getCountryFlag(countryCode) : '';

    newsList.innerHTML = '';

    // Filter news items for the selected country
    const countryNews = allNews.filter(item =>
        item.tags.some(tag =>
            tag.category === 'geography' &&
            normalizeCountryName(tag.name).toLowerCase() === normalizedName.toLowerCase()
        )
    );

    if (countryNews.length === 0) {
        newsList.innerHTML = '<p class="no-news">No news available for this country.</p>';
    } else {
        countryNews.forEach(news => {
            const newsItem = document.createElement('div');
            newsItem.className = 'country-news-item';
            
            // Determine geography tags from the news post
            const geoTags = (news.tags && Array.isArray(news.tags))
                ? news.tags.filter(tag => tag.category === 'geography' && tag.name)
                : [];
            let flagsHTML = '';
            
            // If two or more geography tags are detected, convert first two to flags.
            if (geoTags.length >= 2) {
                flagsHTML = geoTags.slice(0, 2).map(tag => {
                    // Normalize country name from the tag name
                    const normalizedGeo = normalizeCountryName(tag.name);
                    // Retrieve the country code
                    const flagCountryCode = getCountryCode(normalizedGeo);
                    // If a valid code is found, convert it to a flag; otherwise return empty string
                    return flagCountryCode ? getCountryFlag(flagCountryCode) : '';
                }).join(' ');
            } else {
                // If no or only one geography tag is present, use the default panel flag
                const defaultFlagElem = document.querySelector('.country-flag');
                flagsHTML = defaultFlagElem ? defaultFlagElem.textContent : '';
            }
            
            // Build the news item content, appending the flags before the title
            newsItem.innerHTML = `
                <h3>${flagsHTML} ${news.title}</h3>
                <p>${news.description}</p>
                <div class="meta">
                    <span>${formatDate(news.timestamp)}</span>
                </div>
            `;
            
            // Add click event to open news link in a new window
            newsItem.addEventListener('click', () => {
                window.open(news.link, '_blank', 'noopener');
            });
            newsList.appendChild(newsItem);
        });
    }
    
    // Display the news panel
    newsPanel.style.display = 'flex';
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
        const data = await response.json();
        
        // Ensure we have an array of news items
        if (data && Array.isArray(data.news)) {
            allNews = data.news;
        } else if (Array.isArray(data)) {
            allNews = data;
        } else {
            console.error('Invalid news data format:', data);
            allNews = [];
        }
        updateMap(allNews);
    } catch (error) {
        console.error('Error fetching news:', error);
        allNews = [];
        updateMap([]);
    }
}

function updateMap(news) {
    if (!Array.isArray(news)) {
        console.error('Invalid news data format in updateMap:', news);
        news = [];
    }
    
    console.log('Updating map with', news.length, 'news items');
    
    // Update heatmap with new data
    updateHeatmap(news);
    
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
    updateStatsDisplay();
}

function updateStatsDisplay() {
    document.getElementById('activeRegions').textContent = activeRegionsCount;
    document.getElementById('todayEvents').textContent = todayEventsCount;
}

function updateTimeFilter(days) {
    const now = new Date();
    const cutoff = new Date(now - days * 24 * 60 * 60 * 1000);
    
    // Filter news by date
    const filteredNews = allNews.filter(item => new Date(item.timestamp) >= cutoff);
    updateMap(filteredNews);
}

// Initialize everything when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initWebSocket();
    initMap();

});