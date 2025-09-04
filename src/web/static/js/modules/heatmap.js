import { normalizeCountryName, initializeISOMapping, matchCountryName, getCountryData, normalizeCountry } from './countries.js';
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
    console.log('[Heatmap] Starting initialization...');
    console.log('[Heatmap] Map instance:', map ? 'provided' : 'missing');
    
    try {
        // First fetch countries-lite.json for ISO mapping
        const liteResponse = await fetch('/static/assets/countries-lite.json');
        if (!liteResponse.ok) {
            throw new Error(`Failed to fetch lite GeoJSON: ${liteResponse.statusText}`);
        }
        
        const liteData = await liteResponse.json();
        if (!liteData || !liteData.features) {
            throw new Error('Invalid lite GeoJSON data format');
        }
        
        // Initialize ISO mapping with the lite data
        console.log('[Heatmap] Initializing ISO mapping with', liteData.features.length, 'features');
        initializeISOMapping(liteData);
        
        // Then fetch full countries.json for map rendering
        const response = await fetch('/static/assets/countries.json');
        if (!response.ok) {
            throw new Error(`Failed to fetch full GeoJSON: ${response.statusText}`);
        }
        
        const data = await response.json();
        if (!data || !data.features) {
            throw new Error('Invalid full GeoJSON data format');
        }
        
        // Pre-initialize the countryData map
        console.log('[Heatmap] Pre-initializing country data with', data.features.length, 'features');
        countryData = new Map();
        data.features.forEach(feature => {
            if (feature?.properties) {
                const countryName = normalizeCountryName(feature.properties.ADMIN || feature.properties.name);
                countryData.set(countryName, 0);
            }
        });
        
        console.log('[Heatmap] Creating GeoJSON layer...');
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
                            map.fireEvent('countryclick', { 
                                countryName, 
                                feature 
                            });
                        }
                    }
                });
            }
        }).addTo(map);
        
        console.log('[Heatmap] Initialization complete - Layer added to map');
        return countryLayer;
    } catch (error) {
        console.error('Error initializing heatmap:', error);
        throw error;
    }
}

/**
 * Update country colors based on news data
 * @param {Array} data - Array of news items or country statistics
 * @param {boolean} isStatsFormat - Whether data is in the new stats format
 * @param {number} retryCount - Internal retry counter
 * @param {number} maxRetries - Maximum number of retries
 */
export function updateHeatmap(data, isStatsFormat = false, retryCount = 0, maxRetries = 5) {
    console.log(`[Heatmap] Starting update with data format:`, isStatsFormat ? 'stats' : 'news');
    console.log('[Heatmap] Data length:', data?.length || 0);
    
    try {
        if (!Array.isArray(data) || data.length === 0) {
            console.error('[Heatmap] Invalid or empty data provided:', data);
            return;
        }
        
        // Reset country data before processing
        // Clear the data but keep the keys to ensure we have all countries
        if (countryLayer) {
            countryLayer.eachLayer(layer => {
                const feature = layer.feature;
                if (feature?.properties) {
                    const countryName = normalizeCountryName(feature.properties.ADMIN || feature.properties.name);
                    countryData.set(countryName, 0);
                }
            });
        }
        
        // Debug sample of the data
        console.log('[Heatmap] Sample data item:', data[0]);
        
        if (isStatsFormat) {
            // Process the new stats format
            console.log('[Heatmap] Processing country statistics format');
            
            // Each item has {name, code, flag, count}
            data.forEach(item => {
                if (item && item.name && item.count !== undefined) {
                    const normalizedName = normalizeCountryName(item.name);
                    console.log(`[Heatmap] Adding country stat: ${normalizedName} = ${item.count}`);
                    countryData.set(normalizedName, parseInt(item.count) || 0);
                }
            });
        } else {
            // Process the original news data format with tags
            console.log('[Heatmap] Processing news items format');
            console.log('[Heatmap] Sample news item tags:', data[0]?.tags);
            
            let totalGeoTags = 0;
            let matchedTags = 0;
            
            data.forEach(item => {
                if (!item?.tags) return;
                
                // Extract geography tags
                const geoTags = item.tags.filter(tag => 
                    tag && tag.category === 'geography' && tag.name
                );
                
                if (geoTags.length === 0) {
                    return;
                }
                
                totalGeoTags += geoTags.length;
                
                geoTags.forEach(tag => {
                    const normalizedName = normalizeCountryName(tag.name);
                    
                    // Increment the count directly without checking GeoJSON match first
                    if (normalizedName) {
                        console.log(`[Heatmap] Found geo tag: ${tag.name} → ${normalizedName}`);
                        countryData.set(normalizedName, (countryData.get(normalizedName) || 0) + 1);
                        matchedTags++;
                    }
                });
            });
            
            console.log(`[Heatmap] Matched ${matchedTags}/${totalGeoTags} geographic tags`);
        }
        
        // Count countries with data
        let countriesWithData = 0;
        countryData.forEach(count => {
            if (count > 0) countriesWithData++;
        });
        
        console.log('[Heatmap] Countries with data:', countriesWithData);
        
        // Get the maximum count for normalization
        const values = Array.from(countryData.values());
        const maxCount = values.length > 0 ? Math.max(...values) : 1;
        
        console.log('[Heatmap] Max count:', maxCount);
        
        // If we don't have enough country data and haven't exceeded max retries,
        // schedule another update, but only for the news format where we expect
        // to be able to extract additional information
        if (countriesWithData <= 1 && retryCount < maxRetries && !isStatsFormat) {
            console.log(`[Heatmap] Not enough country data (${countriesWithData}), retrying... (${retryCount + 1}/${maxRetries})`);
            setTimeout(() => updateHeatmap(data, isStatsFormat, retryCount + 1, maxRetries), 500);
            return;
        }
        
        // Update country styles
        if (countryLayer) {
            countryLayer.eachLayer(layer => {
                const feature = layer.feature;
                if (!feature || !feature.properties) return;
                
                const countryName = normalizeCountryName(feature.properties.ADMIN || feature.properties.name);
                const count = countryData.get(countryName) || 0;
                
                if (count > 0) {
                    console.log(`[Heatmap] Updating country style: ${countryName} = ${count}`);
                }
                
                const style = mapStyles.getCountryStyle({ count }, maxCount);
                layer.setStyle(style);
                
                // Update tooltip
                if (count > 0) {
                    const country = getCountryData(countryName);
                    const tooltipContent = `${country?.flag || ''} ${countryName}: ${count} news items`;
                    
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
        
        console.log('[Heatmap] Update complete');
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