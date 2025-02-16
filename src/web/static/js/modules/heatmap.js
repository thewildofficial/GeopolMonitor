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
    // Add debug counters
    let totalPosts = 0;
    let totalGeoTags = 0;
    let processedTags = 0;
    let matchedTags = 0;

    console.log('Updating heatmap with new data...', newsData?.length || 0, 'items');
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
                tagCounts.set(tag.name, (tagCounts.get(tag.name) || 0) + 1);
            });
        });

        // Log initial stats
        console.log('Initial counts:', {
            totalPosts,
            totalGeoTags,
            uniqueTags: tagCounts.size
        });

        // Second pass: process with normalized names
        newsData.forEach(item => {
            if (!item?.tags?.length) return;
            
            const geoTags = item.tags.filter(tag => tag?.category === 'geography' && tag.name);
            geoTags.forEach(tag => {
                processedTags++;
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
            });
        });

        // Log comprehensive stats
        console.log('Tag processing stats:', {
            totalPosts,
            totalGeoTags,
            processedTags,
            matchedTags,
            unmatchedCount: unmatchedTags.size,
            matchRate: `${((matchedTags / totalGeoTags) * 100).toFixed(1)}%`
        });

        // Log unmapped tags by frequency
        const unmappedByFrequency = Array.from(tagCounts.entries())
            .filter(([tag]) => !Array.from(countryFrequencies.keys())
                .some(country => normalizeCountryName(tag).toLowerCase() === country.toLowerCase()))
            .sort((a, b) => b[1] - a[1]);
            
        if (unmappedByFrequency.length > 0) {
            console.warn('Most frequent unmapped tags:', 
                unmappedByFrequency.slice(0, 10)
                    .map(([tag, count]) => `${tag}: ${count}`)
            );
        }

        // Log comparison between original counts and matched counts
        console.log('Original tag counts vs Matched counts:');
        for (const [tag, count] of tagCounts.entries()) {
            const normalized = normalizeCountry(tag).name;
            const matched = Array.from(countryFrequencies.entries())
                .find(([country]) => country.toLowerCase() === normalized.toLowerCase());
            if (matched) {
                console.log(`${tag}: ${count} → ${matched[0]}: ${matched[1]}`);
            } else {
                console.log(`${tag}: ${count} → UNMATCHED`);
            }
        }

        // Log unmatched tags
        if (unmatchedTags.size > 0) {
            console.warn('Unmatched geographic tags:', 
                Array.from(unmatchedTags).sort(),
                `(${unmatchedTags.size} total unmatched)`
            );
        }

        // Log matched countries
        console.log('Matched countries:', 
            Array.from(countryFrequencies.entries())
                .sort((a, b) => b[1] - a[1])
                .map(([country, count]) => `${country}: ${count}`)
        );

        // Log top countries for debugging
        const sortedCountries = Array.from(countryFrequencies.entries())
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5);
        console.log('Top 5 countries by news count:', sortedCountries);
        
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