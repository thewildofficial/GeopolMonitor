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
                            map.fireEvent('countryclick', { countryName, feature });
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
 * @param {Array} newsData - Array of news items
 */
export function updateHeatmap(newsData, retryCount = 0, maxRetries = 5) {
    // Add debug counters
    let totalPosts = 0;
    let totalGeoTags = 0;
    let processedTags = 0;
    let matchedTags = 0;

    console.log('[Heatmap] Starting update with', newsData?.length || 0, 'news items');
    console.log('[Heatmap] Current country layer status:', countryLayer ? 'active' : 'not initialized');
    try {
        if (!Array.isArray(newsData)) {
            console.error('Invalid news data format:', newsData);
            return;
        }
        
        // Reset country data
        countryData.clear();
        
        // Count posts per country using normalized country names
        const countryFrequencies = new Map();
        const unmatchedTags = new Set();
        const tagCounts = new Map();
        
        // First pass: count all geographic tags
        newsData.forEach(item => {
            if (!item?.tags?.length) return;
            totalPosts++;
            
            const geoTags = item.tags.filter(tag => tag?.category === 'geography' && tag.name);
            totalGeoTags += geoTags.length;
            
            geoTags.forEach(tag => {
                const originalName = tag.name;
                const normalizedCountry = normalizeCountry(originalName);
                
                // Check if this country exists in our GeoJSON data
                let matched = false;
                if (countryLayer) {
                    countryLayer.eachLayer(layer => {
                        const feature = layer.feature;
                        if (!feature?.properties) return;
                        
                        if (matchCountryName(originalName, feature)) {
                            matched = true;
                            matchedTags++;
                            const featureName = normalizeCountryName(feature.properties.ADMIN || feature.properties.name);
                            countryFrequencies.set(featureName, (countryFrequencies.get(featureName) || 0) + 1);
                        }
                    });
                }
                
                if (!matched) {
                    unmatchedTags.add(`${originalName} (${tagCounts.get(originalName) || 0}) → ${normalizedCountry.name}`);
                }
                
                tagCounts.set(tag.name, (tagCounts.get(tag.name) || 0) + 1);
            });
        });

        // Update country data using normalized names
        if (countryLayer) {
            countryLayer.eachLayer(layer => {
                const feature = layer.feature;
                if (!feature || !feature.properties) return;
                
                const featureName = normalizeCountryName(feature.properties.ADMIN || feature.properties.name);
                const count = countryFrequencies.get(featureName) || 0;
                if (count > 0) {
                    countryData.set(featureName, count);
                }
            });
        }
        
        // Get the maximum count for normalization
        const values = Array.from(countryData.values());
        const maxCount = values.length > 0 ? Math.max(...values) : 1;
        const uniqueCountries = new Set(values.filter(v => v > 0)).size;

        console.log('[Heatmap] Unique countries with data:', uniqueCountries);
        console.log('[Heatmap] Max count:', maxCount);

        // If we don't have enough country data and haven't exceeded max retries,
        // schedule another update
        if (uniqueCountries <= 1 && retryCount < maxRetries) {
            console.log(`[Heatmap] Not enough country data (${uniqueCountries}), retrying... (${retryCount + 1}/${maxRetries})`);
            setTimeout(() => updateHeatmap(newsData, retryCount + 1, maxRetries), 1000);
            return;
        }
        
        // Update country styles
        if (countryLayer) {
            countryLayer.eachLayer(layer => {
                const feature = layer.feature;
                if (!feature || !feature.properties) return;
                
                const countryName = feature.properties.ADMIN || feature.properties.name;
                const normalizedName = normalizeCountryName(countryName);
                const count = countryData.get(normalizedName) || 0;
                const style = mapStyles.getCountryStyle({ count }, maxCount);
                layer.setStyle(style);
                
                // Update tooltip
                if (count > 0) {
                    const country = getCountryData(normalizedName);
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

        // Log final stats if this is the last attempt
        if (retryCount === maxRetries || uniqueCountries > 1) {
            console.log('Final heatmap update stats:', {
                totalPosts,
                totalGeoTags,
                uniqueTags: tagCounts.size,
                matchedTags,
                unmatchedCount: unmatchedTags.size,
                matchRate: `${((matchedTags / totalGeoTags) * 100).toFixed(1)}%`,
                uniqueCountries,
                maxCount
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