import { normalizeCountryName } from './countries.js';

let countryLayer;
let currentTheme = 'light';
let countryData = new Map(); // Store country data for intensity calculations

/**
 * Initialize the heatmap functionality
 * @param {L.Map} map - The Leaflet map instance
 * @returns {Promise} - Resolves when the heatmap is initialized
 */
export async function initHeatmap(map) {
    console.log('Initializing country heatmap...');
    try {
        const response = await fetch('https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson');
        if (!response.ok) {
            throw new Error(`Failed to fetch GeoJSON: ${response.statusText}`);
        }
        
        const data = await response.json();
        if (!data || !data.features) {
            throw new Error('Invalid GeoJSON data format');
        }
        
        countryLayer = L.geoJSON(data, {
            style: getCountryStyle,
            onEachFeature: function(feature, layer) {
                if (!feature || !feature.properties) return;
                
                layer.on({
                    mouseover: highlightFeature,
                    mouseout: resetHighlight,
                    click: (e) => {
                        const countryName = feature.properties.ADMIN || feature.properties.name;
                        if (countryName) {
                            map.fireEvent('countryclick', { countryName, feature });
                        }
                    }
                });

                // Add tooltip with post count
                const countryName = normalizeCountryName(feature.properties.ADMIN || feature.properties.name);
                if (!countryName) return;
                
                const count = countryData.get(countryName) || 0;
                if (count > 0) {
                    layer.bindTooltip(`${count} posts`, {
                        permanent: false,
                        direction: 'center',
                        className: 'country-tooltip'
                    });
                }
            }
        }).addTo(map);
        
        console.log('Country heatmap initialized successfully');
        return countryLayer;
    } catch (error) {
        console.error('Error initializing heatmap:', error);
        throw error;
    }
}

/**
 * Update country colors based on news data
 * @param {Array} newsData - Array of news items
 */
export function updateHeatmap(newsData) {
    console.log('Updating heatmap with new data...');
    try {
        if (!Array.isArray(newsData)) {
            console.error('Invalid news data format:', newsData);
            return;
        }
        
        // Reset country data
        countryData.clear();
        
        // Count posts per country
        newsData.forEach(item => {
            if (!item || !item.tags || !Array.isArray(item.tags)) return;
            
            const geoTags = item.tags.filter(tag => tag && tag.category === 'geography' && tag.name);
            geoTags.forEach(tag => {
                const countryName = normalizeCountryName(tag.name);
                if (countryName) {
                    countryData.set(countryName, (countryData.get(countryName) || 0) + 1);
                }
            });
        });
        
        // Get the maximum count for normalization
        const values = Array.from(countryData.values());
        const maxCount = values.length > 0 ? Math.max(...values) : 1;
        
        // Update country styles
        if (countryLayer) {
            countryLayer.setStyle(feature => {
                if (!feature || !feature.properties) return getCountryStyle(null, 0, maxCount);
                
                const countryName = normalizeCountryName(feature.properties.ADMIN || feature.properties.name);
                const count = countryName ? (countryData.get(countryName) || 0) : 0;
                return getCountryStyle(feature, count, maxCount);
            });
            
            // Update tooltips
            countryLayer.eachLayer(layer => {
                if (!layer.feature || !layer.feature.properties) return;
                
                const countryName = normalizeCountryName(layer.feature.properties.ADMIN || layer.feature.properties.name);
                if (!countryName) return;
                
                const count = countryData.get(countryName) || 0;
                if (count > 0) {
                    if (layer.getTooltip()) {
                        layer.setTooltipContent(`${count} posts`);
                    } else {
                        layer.bindTooltip(`${count} posts`, {
                            permanent: false,
                            direction: 'center',
                            className: 'country-tooltip'
                        });
                    }
                } else {
                    if (layer.getTooltip()) {
                        layer.unbindTooltip();
                    }
                }
            });
        }
    } catch (error) {
        console.error('Error updating heatmap:', error);
    }
}

/**
 * Get style configuration for a country
 * @param {Object} feature - GeoJSON feature
 * @param {number} count - Number of posts for the country
 * @param {number} maxCount - Maximum post count across all countries
 * @returns {Object} - Leaflet path style options
 */
function getCountryStyle(feature, count = 0, maxCount = 1) {
    // Normalize count to get intensity level (0-5)
    const normalized = count / maxCount;
    const intensityLevel = Math.ceil(normalized * 5);
    
    return {
        fillColor: `var(--country-intensity-${intensityLevel || 'default'})`,
        weight: 1,
        opacity: 1,
        color: 'var(--border-color)',
        fillOpacity: count > 0 ? 0.7 : 0.3,
        className: count > 0 ? 'country-active' : 'country-inactive'
    };
}

/**
 * Highlight a country on mouseover
 * @param {L.Event} e - Leaflet event
 */
function highlightFeature(e) {
    const layer = e.target;
    const currentStyle = layer.options;
    
    layer.setStyle({
        weight: 2,
        opacity: 1,
        fillOpacity: currentStyle.fillOpacity + 0.2
    });
    
    layer.bringToFront();
}

/**
 * Reset country highlight on mouseout
 * @param {L.Event} e - Leaflet event
 */
function resetHighlight(e) {
    countryLayer.resetStyle(e.target);
}

/**
 * Update theme-related styles
 * @param {string} theme - 'light' or 'dark'
 */
export function updateTheme(theme) {
    currentTheme = theme;
    if (countryLayer) {
        countryLayer.setStyle(feature => {
            const countryName = normalizeCountryName(feature.properties.ADMIN || feature.properties.name);
            const count = countryData.get(countryName) || 0;
            const maxCount = Math.max(...Array.from(countryData.values()), 1);
            return getCountryStyle(feature, count, maxCount);
        });
    }
}