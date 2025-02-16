// Country data management
let geoJsonCountryData = new Map();

// ISO code mapping for additional country matching
const isoCodeMapping = new Map();

// Save GeoJSON features for reverse lookup
let geoJsonFeatures = [];

function getCountryCoordinates(countryName) {
    const normalizedName = normalizeCountryName(countryName);
    const countryData = geoJsonCountryData.get(normalizedName);
    return countryData ? countryData.coords : null;
}

function normalizeCountryName(name) {
    if (!name) return '';
    
    // Handle kebab-case first
    const preFormatted = name.replace(/-/g, ' ').trim();
    
    // Convert to title case
    const formattedName = preFormatted
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ');

    // Special cases and common variations
    const aliases = {
        'United States Of America': 'United States',
        'United Kingdom Of Great Britain And Northern Ireland': 'United Kingdom',
        'Democratic Republic Of The Congo': 'DR Congo',
        'Dr Congo': 'DR Congo',
        'Drc': 'DR Congo',
        'Congo Democratic Republic': 'DR Congo',
        'Congo Dr': 'DR Congo',
        'Republic Of The Congo': 'Congo',
        'Congo Republic': 'Congo',
        'Peoples Republic Of China': 'China',
        "People's Republic Of China": 'China',
        'Republic Of China': 'Taiwan',
        'Chinese Republic': 'Taiwan',
        'Russian Federation': 'Russia',
        'United States': 'United States',
        'United States Of America': 'United States',
        'Usa': 'United States',
        'Unidos': 'United States',
        'Estados Unidos': 'United States',
        'Us': 'United States',
        'America': 'United States',
        'América': 'United States',
        'Democratic Peoples Republic Of Korea': 'North Korea',
        'Republic Of Korea': 'South Korea',
        'Korea South': 'South Korea',
        'Korea North': 'North Korea',
        'Deutschland': 'Germany',
        'Federal Republic Of Germany': 'Germany',
        'Burma': 'Myanmar',
        'Czech Republic': 'Czechia',
        'Uk': 'United Kingdom',
        'Great Britain': 'United Kingdom',
        'Britain': 'United Kingdom'
    };

    return aliases[formattedName] || formattedName;
}

// Initialize ISO code mapping and country data from GeoJSON
function initializeISOMapping(geojsonData) {
    if (!geojsonData || !geojsonData.features) {
        console.error('Invalid GeoJSON data provided');
        return;
    }
    
    geoJsonFeatures = geojsonData.features; // store for reverse lookup
    console.log(`Initializing data with ${geojsonData.features.length} features`);
    
    geojsonData.features.forEach(feature => {
        if (feature.properties) {
            const props = feature.properties;
            const name = props.ADMIN || props.name;
            if (!name) {
                console.warn('Feature missing name:', feature);
                return;
            }

            const normalizedName = normalizeCountryName(name);
            
            // Store coordinates and ISO code
            const bounds = L.geoJSON(feature).getBounds();
            const center = bounds.getCenter();
            const countryData = {
                coords: [center.lat, center.lng],
                code: props.ISO_A2
            };
            
            geoJsonCountryData.set(normalizedName, countryData);

            // Store ISO codes for lookup
            if (props.ISO_A2) {
                isoCodeMapping.set(props.ISO_A2.toLowerCase(), normalizedName);
            }
            if (props.ISO_A3) {
                isoCodeMapping.set(props.ISO_A3.toLowerCase(), normalizedName);
            }
            isoCodeMapping.set(normalizedName.toLowerCase(), normalizedName);
        }
    });
    
    console.log(`Initialized ${geoJsonCountryData.size} countries and ${isoCodeMapping.size} ISO codes`);
}

function matchCountryName(name, geojsonFeature) {
    const normalizedInput = normalizeCountryName(name).toLowerCase();
    const featureProps = geojsonFeature.properties;
    const featureName = normalizeCountryName(featureProps.ADMIN || featureProps.name).toLowerCase();
    
    if (normalizedInput === featureName) return true;
    if (featureProps.ISO_A2 && normalizedInput === featureProps.ISO_A2.toLowerCase()) return true;
    if (featureProps.ISO_A3 && normalizedInput === featureProps.ISO_A3.toLowerCase()) return true;
    
    const mappedName = isoCodeMapping.get(normalizedInput);
    if (mappedName && normalizeCountryName(mappedName).toLowerCase() === featureName) return true;
    
    return false;
}

function getCountryCode(countryName) {
    if (geoJsonCountryData.size === 0) {
        console.warn('Country data not loaded. Call loadCountryData() first.');
        return null;
    }
    const normalizedName = normalizeCountryName(countryName);
    let countryData = geoJsonCountryData.get(normalizedName);
    if (!countryData) {
        // Reverse lookup by iterating over stored features
        for (const feature of geoJsonFeatures) {
            if (feature.properties) {
                const props = feature.properties;
                const featureName = normalizeCountryName(props.ADMIN || props.name);
                // Compare lowercased names to avoid minor differences
                if (featureName.toLowerCase() === normalizedName.toLowerCase()) {
                    const isoCode = props.ISO_A2;
                    countryData = { code: isoCode };
                    // Optionally, update the Map for future fast lookup
                    geoJsonCountryData.set(normalizedName, countryData);
                    console.debug(`Reverse lookup successful for ${normalizedName}:`, countryData);
                    break;
                }
            }
        }
    }
    if (!countryData) {
        return null;
    }
    if (!countryData.code) {
        console.warn(`No ISO code found for: ${normalizedName}`);
        return null;
    }
    return countryData.code;
}

function getCountryFlag(countryCode) {
    if (!countryCode) return '';
    return countryCode
        .toUpperCase()
        .replace(/./g, char => 
            String.fromCodePoint(char.charCodeAt(0) + 127397)
        );
}

/**
 * Get country's flag emoji based on ISO code
 * @param {string} countryCode - The ISO 3166-1 alpha-2 country code
 * @returns {string} The flag emoji for the country or 🌐 as fallback
 */
export function getCountryEmoji(countryCode) {
    if (!countryCode) return '🌐';
    
    try {
        // Convert country code to regional indicator symbols
        return countryCode
            .toUpperCase()
            .replace(/./g, char => 
                String.fromCodePoint(char.charCodeAt(0) + 127397)
            );
    } catch (error) {
        console.warn(`Failed to get emoji for country code: ${countryCode}`, error);
        return '🌐';
    }
}

/**
 * Get country data including name, code, and flag emoji
 * @param {string} countryName - The country name to normalize
 * @returns {Object} Object containing normalized name, code and flag emoji
 */
export function getCountryData(countryName) {
    const normalized = normalizeCountryName(countryName);
    const code = getCountryCode(normalized);
    const flag = getCountryEmoji(code);
    
    return {
        name: normalized,
        code: code,
        flag: flag
    };
}

function normalizeCountry(input) {
    const name = normalizeCountryName(input);
    const code = getCountryCode(name);
    const flag = getCountryFlag(code);
    return { name, code, flag };
}

function isCountryMatch(country1, country2) {
    const name1 = normalizeCountryName(country1.name || country1);
    const name2 = normalizeCountryName(country2.name || country2);
    return name1.toLowerCase() === name2.toLowerCase();
}

/**
 * Load and initialize country data from GeoJSON
 * @returns {Promise<void>}
 */
async function loadCountryData() {
    try {
        const response = await fetch('/static/assets/countries.json');
        if (!response.ok) {
            throw new Error(`Failed to fetch GeoJSON: ${response.statusText}`);
        }
        const geojsonData = await response.json();
        console.log('GeoJSON loaded:', geojsonData.features.length, 'features');
        
        initializeISOMapping(geojsonData);
        
        // Verify data was loaded
        console.log('Country data loaded:', {
            countries: geoJsonCountryData.size,
            isoCodes: isoCodeMapping.size,
            features: geoJsonFeatures.length
        });
 
    } catch (error) {
        console.error('Failed to load country data:', error);
        throw error;
    }
}

export {
    getCountryCoordinates,
    normalizeCountryName,
    initializeISOMapping,
    matchCountryName,
    getCountryCode,
    getCountryFlag,
    normalizeCountry,
    isCountryMatch,
    loadCountryData
};