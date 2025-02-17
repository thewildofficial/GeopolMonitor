import pycountry
from typing import Dict, Optional
from difflib import get_close_matches
import json
import gzip
import os
from pathlib import Path

# Get the absolute path to the assets directory
ASSETS_DIR = Path(__file__).parent / 'static' / 'assets'

# UTIL SCRIPT TO HANDLE JSON FILE

def get_country_aliases() -> Dict[str, str]:
    """
    Returns a dictionary of common country name variations and their standard names.
    Generated systematically from pycountry data where possible.
    """
    aliases = {}
    
    # Add systematic aliases for all countries
    for country in pycountry.countries:
        if hasattr(country, 'alpha_2'):
            aliases[country.alpha_2] = country.name  # Add ISO alpha-2 codes
        if hasattr(country, 'alpha_3'):
            aliases[country.alpha_3] = country.name  # Add ISO alpha-3 codes
        if hasattr(country, 'official_name'):
            aliases[country.official_name] = country.name  # Add official names
            # Add hyphenated version of official name
            aliases[country.official_name.lower().replace(' ', '-')] = country.name
            
    # Add some very common variations that might not be covered
    additional_aliases = {
        "USA": "United States",
        "US": "United States",
        "America": "United States",
        "united-states": "United States",
        "united-states-of-america": "United States",
        "UK": "United Kingdom",
        "Britain": "United Kingdom",
        "Great Britain": "United Kingdom",
        "united-kingdom": "United Kingdom",
        "great-britain": "United Kingdom",
        "england": "United Kingdom",
        "UAE": "United Arab Emirates",
        "united-arab-emirates": "United Arab Emirates",
        "DPRK": "Korea, Democratic People's Republic of",
        "North Korea": "Korea, Democratic People's Republic of",
        "north-korea": "Korea, Democratic People's Republic of",
        "South Korea": "Korea, Republic of",
        "south-korea": "Korea, Republic of",
        "Russia": "Russian Federation",
        "european-union": "European Union",
        "EU": "European Union",
        "czech-republic": "Czechia",
        "saudi-arabia": "Saudi Arabia",
        "hong-kong": "Hong Kong",
        "new-zealand": "New Zealand",
        "south-africa": "South Africa",
        "myanmar": "Myanmar",
        "burma": "Myanmar"
    }
    aliases.update(additional_aliases)
    
    return aliases

# Initialize aliases once at module level
COUNTRY_ALIASES = get_country_aliases()

def normalize_country(country_name: str) -> Dict[str, Optional[str]]:
    """
    Normalize a country name to its standard form using pycountry.
    Returns a dictionary with normalized name, alpha-2 code, and flag emoji.
    """
    if not country_name:
        return {"name": "", "code": None, "flag": ""}
    
    # Clean the input and try both original and hyphen-converted versions
    clean_name = country_name.strip()
    hyphen_version = clean_name.lower().replace(' ', '-')
    space_version = clean_name.lower().replace('-', ' ')
    
    # Try all variants in aliases
    for name_variant in [clean_name, hyphen_version, space_version]:
        if name_variant.upper() in COUNTRY_ALIASES:
            clean_name = COUNTRY_ALIASES[name_variant.upper()]
            break
    
    try:
        # Step 1: Try exact match
        country = pycountry.countries.get(name=clean_name)
        
        # Step 2: Try searching by name
        if not country:
            countries = pycountry.countries.search(clean_name)
            if countries:
                country = countries[0]
                
        # Step 3: Try fuzzy matching as a last resort
        if not country:
            all_names = [c.name for c in pycountry.countries]
            matches = get_close_matches(clean_name, all_names, n=1, cutoff=0.85)
            if matches:
                country = pycountry.countries.get(name=matches[0])

        if country:
            # Convert country code to flag emoji
            flag = ""
            if hasattr(country, 'alpha_2'):
                flag = ''.join(chr(ord(c) + 127397) for c in country.alpha_2)

            return {
                "name": country.name,
                "code": country.alpha_2 if hasattr(country, 'alpha_2') else None,
                "flag": flag
            }
    except (AttributeError, LookupError):
        pass

    # Return original name if no match found
    return {
        "name": country_name,
        "code": None,
        "flag": ""
    }

def create_lite_countries_file():
    # Use absolute paths for file operations
    input_path = ASSETS_DIR / 'countries.json'
    output_path = ASSETS_DIR / 'countries-lite.json'
    gzip_path = ASSETS_DIR / 'countries.json.gz'
    
    # Ensure the assets directory exists
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(input_path, 'r') as f:
        data = json.load(f)
    
    # Create a new FeatureCollection with only properties
    lite_data = {
        "type": "FeatureCollection",
        "features": []
    }
    
    # Extract only the properties for each feature
    for feature in data['features']:
        lite_feature = {
            "type": "Feature",
            "properties": feature['properties']
        }
        lite_data['features'].append(lite_feature)
    
    # Write the simplified data to a new file
    with open(output_path, 'w') as f:
        json.dump(lite_data, f, indent=2)
    
    # Create gzipped version of the original file
    with open(input_path, 'rb') as f_in:
        with gzip.open(gzip_path, 'wb', compresslevel=9) as f_out:
            f_out.write(f_in.read())
    
    print(f"Created compressed file: {gzip_path}")
    print(f"Original size: {os.path.getsize(input_path):,} bytes")
    print(f"Compressed size: {os.path.getsize(gzip_path):,} bytes")

if __name__ == '__main__':
    create_lite_countries_file()