import { getActiveTags } from './tags.js';
import { mapStyles } from './map-styles.js';
import { normalizeCountry } from './countries.js';

let map;
let heatLayer;
let newsMarkers = new Map();
let currentTimeRange = 'all';
const newsPoints = [];

export class NewsMap {
    constructor() {
        this.map = null;
        this.countryLayer = null;
        this.activeCountryLayer = null;
        this.countryHeatData = new Map();
        this.regions = new Set();
        this.todayEvents = 0;
        this.onCountrySelected = null;
        this.geoJsonData = null;
    }

    async init() {
        this.map = L.map('worldMap', {
            zoomControl: true,
            attributionControl: false,
            minZoom: 2,
            maxZoom: 6,
            zoomSnap: 0.5,
            zoomDelta: 0.5,
            wheelPxPerZoomLevel: 120
        }).setView([30, 0], 2);

        await this.initTileLayers();
        await this.loadCountryBoundaries();
        this.addLegend();
        this.setupThemeObserver();
    }

    async loadCountryBoundaries() {
        try {
            const response = await fetch('https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson');
            this.geoJsonData = await response.json();
            
            // Transform GeoJSON to include normalized country data
            this.geoJsonData.features = this.geoJsonData.features.map(feature => {
                const countryName = feature.properties.ADMIN || feature.properties.name;
                const countryData = normalizeCountry(countryName);
                feature.properties.normalizedData = countryData;
                return feature;
            });
            
            this.updateCountryLayer();
        } catch (error) {
            console.error('Failed to load country boundaries:', error);
        }
    }

    updateCountryLayer() {
        if (!this.geoJsonData) return;

        if (this.countryLayer) {
            this.map.removeLayer(this.countryLayer);
        }

        this.countryLayer = L.geoJSON(this.geoJsonData, {
            style: (feature) => this.getCountryStyle(feature),
            onEachFeature: (feature, layer) => {
                const countryData = feature.properties.normalizedData;
                const heatData = this.countryHeatData.get(countryData.code);

                // Add interactivity
                layer.on({
                    mouseover: (e) => this.highlightCountry(e.target),
                    mouseout: (e) => this.resetHighlight(e.target),
                    click: (e) => this.handleCountryClick(feature, e.target)
                });

                // Add tooltip with news count if available
                if (heatData) {
                    const tooltipContent = `${countryData.flag} ${countryData.name}: ${heatData.count} news items`;
                    layer.bindTooltip(tooltipContent, {
                        permanent: false,
                        direction: 'center',
                        className: 'country-tooltip'
                    });
                }
            }
        }).addTo(this.map);

        // Apply theme-specific styles
        this.updateMapTheme();
    }

    updateMapTheme() {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        
        // Update map container background
        const mapContainer = document.getElementById('worldMap');
        if (mapContainer) {
            mapContainer.style.background = isDark ? '#111' : '#f5f5f5';
        }

        // Update legend gradient
        const legendGradient = document.querySelector('.legend-gradient');
        if (legendGradient) {
            legendGradient.style.background = mapStyles.getLegendGradient();
        }

        // Refresh country styles
        if (this.countryLayer) {
            this.countryLayer.eachLayer(layer => {
                const feature = layer.feature;
                const style = this.getCountryStyle(feature);
                layer.setStyle(style);
            });
        }
    }

    getCountryStyle(feature) {
        const countryData = feature.properties.normalizedData;
        const heatData = this.countryHeatData.get(countryData.code);
        const maxCount = this.getMaxCount();
        
        return mapStyles.getCountryStyle(heatData, maxCount);
    }

    highlightCountry(layer) {
        if (layer === this.activeCountryLayer) return;
        
        layer.setStyle(mapStyles.getHoverStyle());
        layer.bringToFront();
    }

    resetHighlight(layer) {
        if (layer === this.activeCountryLayer) return;
        
        this.countryLayer.resetStyle(layer);
    }

    handleCountryClick(feature, layer) {
        const countryName = feature.properties.ADMIN || feature.properties.name;
        
        // Reset previous active country
        if (this.activeCountryLayer) {
            this.countryLayer.resetStyle(this.activeCountryLayer);
        }
        
        // Set new active country
        this.activeCountryLayer = layer;
        layer.setStyle(mapStyles.getActiveCountryStyle());
        layer.bringToFront();

        // Trigger callback
        if (this.onCountrySelected) {
            this.onCountrySelected(countryName);
        }
    }

    initTileLayers() {
        this.lightTiles = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors, © CARTO'
        });
        
        this.darkTiles = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors, © CARTO'
        });

        const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
        (isDarkMode ? this.darkTiles : this.lightTiles).addTo(this.map);
    }

    addLegend() {
        const mapControls = L.control({ position: 'bottomright' });
        mapControls.onAdd = () => {
            const div = L.DomUtil.create('div', 'heat-map-legend');
            div.innerHTML = `
                <div class="legend-container">
                    <div class="legend-gradient" style="background: ${mapStyles.getLegendGradient()}"></div>
                    <div class="legend-labels">
                        <span>Less active</span>
                        <span>More active</span>
                    </div>
                </div>
            `;
            return div;
        };
        mapControls.addTo(this.map);
    }

    setupThemeObserver() {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'data-theme') {
                    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
                    this.map.removeLayer(isDark ? this.lightTiles : this.darkTiles);
                    this.map.addLayer(isDark ? this.darkTiles : this.lightTiles);
                    
                    // Update legend gradient
                    const legendGradient = document.querySelector('.legend-gradient');
                    if (legendGradient) {
                        legendGradient.style.background = mapStyles.getLegendGradient();
                    }
                    
                    // Update country styles
                    this.updateCountryLayer();
                }
            });
        });
        
        observer.observe(document.documentElement, { attributes: true });
    }

    getMaxCount() {
        return Math.max(...Array.from(this.countryHeatData.values()).map(data => data.count));
    }

    updateHeatData(newsItems) {
        this.countryHeatData.clear();
        this.regions.clear();
        this.todayEvents = 0;
        
        const today = new Date().toDateString();
        
        // Group news items by country
        newsItems.forEach(item => {
            const geoTags = item.tags.filter(tag => tag.category === 'geography');
            geoTags.forEach(tag => {
                const countryData = normalizeCountry(tag.name);
                if (!countryData.code) return;

                if (!this.countryHeatData.has(countryData.code)) {
                    this.countryHeatData.set(countryData.code, {
                        name: countryData.name,
                        flag: countryData.flag,
                        count: 0,
                        items: [],
                        newestTimestamp: null
                    });
                }
                
                const data = this.countryHeatData.get(countryData.code);
                data.count++;
                data.items.push(item);
                
                // Track newest timestamp for this country
                const timestamp = new Date(item.timestamp);
                if (!data.newestTimestamp || timestamp > data.newestTimestamp) {
                    data.newestTimestamp = timestamp;
                }
                
                // Count today's events
                if (timestamp.toDateString() === today) {
                    this.todayEvents++;
                }
                
                this.regions.add(countryData.code);
            });
        });
        
        // Update the map visualization
        this.updateCountryLayer();
        
        return {
            activeRegions: this.regions.size,
            todayEvents: this.todayEvents
        };
    }
}

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



function normalizeCountryName(name) {
    const countryMappings = {
        'United States of America': { name: 'United States', code: 'US' },
        'USA': { name: 'United States', code: 'US' },
        'United Kingdom': { name: 'United Kingdom', code: 'GB' },
        'UK': { name: 'United Kingdom', code: 'GB' },
        'Russian Federation': { name: 'Russia', code: 'RU' },
        'People\'s Republic of China': { name: 'China', code: 'CN' }
        // Add more mappings as needed
    };

    // Function to convert country code to flag emoji
    const getCountryFlag = (code) => {
        if (!code) return '';
        return code.toUpperCase().replace(/./g, char => 
            String.fromCodePoint(char.charCodeAt(0) + 127397)
        );
    };

    const normalized = countryMappings[name] || { name: name, code: null };
    return {
        name: normalized.name,
        flag: getCountryFlag(normalized.code)
    };
}