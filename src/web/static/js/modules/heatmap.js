import { normalizeCountryName, initializeISOMapping, matchCountryName, getCountryData } from './countries.js';
import { mapStyles } from './map-styles.js';

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

        // Initialize ISO mapping with the GeoJSON data
        initializeISOMapping(data);
        
        countryLayer = L.geoJSON(data, {
            style: (feature) => mapStyles.getCountryStyle({ count: 0 }, 1),
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
    console.log('Updating heatmap with new data...', newsData?.length || 0, 'items');
    try {
        if (!Array.isArray(newsData)) {
            console.error('Invalid news data format:', newsData);
            return;
        }
        
        // Reset country data
        countryData.clear();
        
        // Count posts per country and log for debugging
        const countryFrequencies = new Map();
        
        newsData.forEach(item => {
            if (!item || !item.tags || !Array.isArray(item.tags)) return;
            
            const geoTags = item.tags.filter(tag => tag && tag.category === 'geography' && tag.name);
            geoTags.forEach(tag => {
                const countryName = tag.name;
                if (countryName) {
                    countryFrequencies.set(countryName, (countryFrequencies.get(countryName) || 0) + 1);
                }
            });
        });

        // Log top countries for debugging
        const sortedCountries = Array.from(countryFrequencies.entries())
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5);
        console.log('Top 5 countries by news count:', sortedCountries);
        
        // Update country data using GeoJSON feature matching
        if (countryLayer) {
            countryLayer.eachLayer(layer => {
                const feature = layer.feature;
                if (!feature || !feature.properties) return;
                
                let totalCount = 0;
                countryFrequencies.forEach((count, tagCountry) => {
                    if (matchCountryName(tagCountry, feature)) {
                        totalCount += count;
                    }
                });
                
                if (totalCount > 0) {
                    const countryName = feature.properties.ADMIN || feature.properties.name;
                    countryData.set(countryName, totalCount);
                }
            });
        }
        
        // Get the maximum count for normalization
        const values = Array.from(countryData.values());
        const maxCount = values.length > 0 ? Math.max(...values) : 1;
        console.log('Max count across countries:', maxCount);
        
        // Update country styles
        if (countryLayer) {
            countryLayer.eachLayer(layer => {
                const feature = layer.feature;
                if (!feature || !feature.properties) return;
                
                const countryName = feature.properties.ADMIN || feature.properties.name;
                const count = countryData.get(countryName) || 0;
                const style = mapStyles.getCountryStyle({ count }, maxCount);
                layer.setStyle(style);
                
                // Update tooltip
                if (count > 0) {
                    const country = getCountryData(countryName);
                    const tooltipContent = `${count} posts ${country.flag}`;
                    
                    if (layer.getTooltip()) {
                        layer.setTooltipContent(tooltipContent);
                    } else {
                        layer.bindTooltip(tooltipContent, {
                            permanent: false,
                            direction: 'center',
                            className: 'country-tooltip apple-tooltip'
                        });
                    }
                } else if (layer.getTooltip()) {
                    layer.unbindTooltip();
                }
            });
        }
    } catch (error) {
        console.error('Error updating heatmap:', error);
    }
}

/**
 * Highlight a country on mouseover
 * @param {L.Event} e - Leaflet event
 */
function highlightFeature(e) {
    const layer = e.target;
    const currentStyle = layer.options;
    
    layer.setStyle(mapStyles.getHoverStyle(currentStyle));
    layer.bringToFront();
}

/**
 * Reset country highlight on mouseout
 * @param {L.Event} e - Leaflet event
 */
function resetHighlight(e) {
    const layer = e.target;
    const feature = layer.feature;
    if (!feature || !feature.properties) return;
    
    const countryName = normalizeCountryName(feature.properties.ADMIN || feature.properties.name);
    const count = countryData.get(countryName) || 0;
    const maxCount = Math.max(...Array.from(countryData.values()), 1);
    
    layer.setStyle(mapStyles.getCountryStyle({ count }, maxCount));
}

/**
 * Update theme-related styles
 * @param {string} theme - 'light' or 'dark'
 */
export function updateTheme(theme) {
    currentTheme = theme;
    if (countryLayer) {
        const maxCount = Math.max(...Array.from(countryData.values()), 1);
        countryLayer.eachLayer(layer => {
            const feature = layer.feature;
            if (!feature || !feature.properties) return;
            
            const countryName = normalizeCountryName(feature.properties.ADMIN || feature.properties.name);
            const count = countryData.get(countryName) || 0;
            
            layer.setStyle(mapStyles.getCountryStyle({ count }, maxCount));
        });
    }
}