// Country data management
const countryData = {
    'United States': { coords: [39.8283, -98.5795], code: 'US' },
    'USA': { coords: [39.8283, -98.5795], code: 'US' },
    'Russia': { coords: [61.5240, 105.3188], code: 'RU' },
    'Russian Federation': { coords: [61.5240, 105.3188], code: 'RU' },
    'China': { coords: [35.8617, 104.1954], code: 'CN' },
    'United Kingdom': { coords: [55.3781, -3.4360], code: 'GB' },
    'UK': { coords: [55.3781, -3.4360], code: 'GB' },
    'France': { coords: [46.2276, 2.2137], code: 'FR' },
    'Germany': { coords: [51.1657, 10.4515], code: 'DE' },
    'Japan': { coords: [36.2048, 138.2529], code: 'JP' },
    'India': { coords: [20.5937, 78.9629], code: 'IN' },
    'Brazil': { coords: [-14.2350, -51.9253], code: 'BR' },
    'Canada': { coords: [56.1304, -106.3468], code: 'CA' },
    'Australia': { coords: [-25.2744, 133.7751], code: 'AU' },
    'Italy': { coords: [41.8719, 12.5674], code: 'IT' },
    'Spain': { coords: [40.4637, -3.7492], code: 'ES' },
    'Ukraine': { coords: [48.3794, 31.1656], code: 'UA' },
    'Israel': { coords: [31.0461, 34.8516], code: 'IL' },
    'Iran': { coords: [32.4279, 53.6880], code: 'IR' },
    'South Korea': { coords: [35.9078, 127.7669], code: 'KR' },
    'North Korea': { coords: [40.3399, 127.5101], code: 'KP' },
    'Mexico': { coords: [23.6345, -102.5528], code: 'MX' },
    'Egypt': { coords: [26.8206, 30.8025], code: 'EG' },
    'Saudi Arabia': { coords: [23.8859, 45.0792], code: 'SA' },
    'Turkey': { coords: [38.9637, 35.2433], code: 'TR' },
    'Türkiye': { coords: [38.9637, 35.2433], code: 'TR' },
    'Pakistan': { coords: [30.3753, 69.3451], code: 'PK' },
    'Afghanistan': { coords: [33.9391, 67.7100], code: 'AF' },
    'Syria': { coords: [34.8021, 38.9968], code: 'SY' },
    'Iraq': { coords: [33.2232, 43.6793], code: 'IQ' },
    'Poland': { coords: [51.9194, 19.1451], code: 'PL' },
    'Netherlands': { coords: [52.1326, 5.2913], code: 'NL' },
    'Belgium': { coords: [50.5039, 4.4699], code: 'BE' },
    'Sweden': { coords: [60.1282, 18.6435], code: 'SE' },
    'Norway': { coords: [60.4720, 8.4689], code: 'NO' },
    'Finland': { coords: [61.9241, 25.7482], code: 'FI' },
    'Denmark': { coords: [56.2639, 9.5018], code: 'DK' },
    'Greece': { coords: [39.0742, 21.8243], code: 'GR' },
    'Romania': { coords: [45.9432, 24.9668], code: 'RO' },
    'Belarus': { coords: [53.7098, 27.9534], code: 'BY' },
    'Kazakhstan': { coords: [48.0196, 66.9237], code: 'KZ' },
    'Azerbaijan': { coords: [40.1431, 47.5769], code: 'AZ' },
    'Armenia': { coords: [40.0691, 45.0382], code: 'AM' },
    'Georgia': { coords: [42.3154, 43.3569], code: 'GE' },
    'Moldova': { coords: [47.4116, 28.3699], code: 'MD' },
    'Vietnam': { coords: [14.0583, 108.2772], code: 'VN' },
    'Thailand': { coords: [15.8700, 100.9925], code: 'TH' },
    'Malaysia': { coords: [4.2105, 101.9758], code: 'MY' },
    'Indonesia': { coords: [-0.7893, 113.9213], code: 'ID' },
    'Philippines': { coords: [12.8797, 121.7740], code: 'PH' },
    'New Zealand': { coords: [-40.9006, 174.8860], code: 'NZ' },
    'South Africa': { coords: [-30.5595, 22.9375], code: 'ZA' },
    'Nigeria': { coords: [9.0820, 8.6753], code: 'NG' },
    'Kenya': { coords: [-0.0236, 37.9062], code: 'KE' },
    'Ethiopia': { coords: [9.1450, 40.4897], code: 'ET' },
    'Sudan': { coords: [12.8628, 30.2176], code: 'SD' },
    'Argentina': { coords: [-38.4161, -63.6167], code: 'AR' },
    'Chile': { coords: [-35.6751, -71.5430], code: 'CL' },
    'Peru': { coords: [-9.1900, -75.0152], code: 'PE' },
    'Colombia': { coords: [4.5709, -74.2973], code: 'CO' },
    'Venezuela': { coords: [6.4238, -66.5897], code: 'VE' },
    'Taiwan': { coords: [23.5937, 121.0254], code: 'TW' }
};

export function getCountryCoordinates(countryName) {
    // Normalize the country name
    const normalizedName = normalizeCountryName(countryName);
    return countryData[normalizedName]?.coords;
}

export function normalizeCountryName(name) {
    // Special cases and common variations
    const aliases = {
        'United States of America': 'United States',
        'USA': 'United States',
        'UK': 'United Kingdom',
        'Great Britain': 'United Kingdom',
        'Russian Federation': 'Russia',
        "People's Republic of China": 'China',
        'South Korea': 'South Korea',
        'Republic of Korea': 'South Korea',
        'DPRK': 'North Korea',
        "Democratic People's Republic of Korea": 'North Korea',
        'UAE': 'United Arab Emirates',
        'KSA': 'Saudi Arabia',
        'ROK': 'South Korea',
        'RoC': 'Taiwan',
        'Republic of China': 'Taiwan',
        'Chinese Taipei': 'Taiwan',
        'Taipei': 'Taiwan',
        'Islamic Republic of Iran': 'Iran',
        'Republic of Türkiye': 'Turkey',
        'Republic of Turkiye': 'Turkey',
        'Republic of Turkey': 'Turkey',
        'Kingdom of Saudi Arabia': 'Saudi Arabia',
        'Mainland China': 'China',
        'PRC': 'China',
        'Republic of India': 'India',
        'Estado Unidos': 'United States',
        'América': 'United States',
        'Estados Unidos': 'United States',
        'Republic of South Africa': 'South Africa',
        'RSA': 'South Africa',
        'UAE': 'United Arab Emirates',
        'The Netherlands': 'Netherlands',
        'Holland': 'Netherlands',
        'Reino Unido': 'United Kingdom'
    };

    // First check aliases
    if (aliases[name]) {
        return aliases[name];
    }

    // Return original name if no alias found
    return name;
}

export function getCountryCode(countryName) {
    const normalizedName = normalizeCountryName(countryName);
    return countryData[normalizedName]?.code;
}

export function getCountryFlag(countryCode) {
    if (!countryCode) return '';
    return countryCode
        .toUpperCase()
        .replace(/./g, char => 
            String.fromCodePoint(char.charCodeAt(0) + 127397)
        );
}

export function normalizeCountry(input) {
    const name = normalizeCountryName(input);
    const code = getCountryCode(name);
    const flag = getCountryFlag(code);
    return { name, code, flag };
}

export function isCountryMatch(country1, country2) {
    const name1 = normalizeCountryName(country1.name || country1);
    const name2 = normalizeCountryName(country2.name || country2);
    return name1.toLowerCase() === name2.toLowerCase();
}