"""Script to split GeoJSON map data into smaller chunks based on zoom levels and regions."""
import json
import os
import math
from pathlib import Path
from typing import Dict, List, Tuple

def simplify_coordinates(coords: List[float], tolerance: float) -> List[float]:
    """Simplify coordinate arrays using Douglas-Peucker algorithm."""
    if len(coords) <= 2:
        return coords
    
    # Find the point with the maximum distance
    max_dist = 0
    max_idx = 0
    first = coords[0]
    last = coords[-1]
    
    for i in range(1, len(coords) - 1):
        dist = point_line_distance(coords[i], first, last)
        if dist > max_dist:
            max_dist = dist
            max_idx = i
    
    # If max distance is greater than tolerance, recursively simplify
    if max_dist > tolerance:
        left = simplify_coordinates(coords[:max_idx + 1], tolerance)
        right = simplify_coordinates(coords[max_idx:], tolerance)
        return left[:-1] + right
    
    return [first, last]

def point_line_distance(point: List[float], line_start: List[float], line_end: List[float]) -> float:
    """Calculate the distance between a point and a line segment."""
    if line_start == line_end:
        return math.sqrt(sum((point[i] - line_start[i]) ** 2 for i in range(2)))
    
    # Calculate the normalized dot product
    line_length = math.sqrt(sum((line_end[i] - line_start[i]) ** 2 for i in range(2)))
    dot_product = sum((point[i] - line_start[i]) * (line_end[i] - line_start[i]) for i in range(2))
    t = max(0, min(1, dot_product / (line_length ** 2)))
    
    # Find the closest point on the line
    closest = [line_start[i] + t * (line_end[i] - line_start[i]) for i in range(2)]
    
    # Return the distance to the closest point
    return math.sqrt(sum((point[i] - closest[i]) ** 2 for i in range(2)))

def get_region(lat: float, lng: float) -> str:
    """Get region identifier for coordinates."""
    lat_region = math.floor((lat + 90) / 45)
    lng_region = math.floor((lng + 180) / 45)
    return f"r{lat_region}-{lng_region}"

def get_feature_region(feature: Dict) -> str:
    """Get region for a GeoJSON feature based on its centroid."""
    coords = feature['geometry']['coordinates']
    if feature['geometry']['type'] == 'Polygon':
        # Calculate centroid of first polygon ring
        lats = [p[1] for p in coords[0]]
        lngs = [p[0] for p in coords[0]]
        center_lat = sum(lats) / len(lats)
        center_lng = sum(lngs) / len(lngs)
    elif feature['geometry']['type'] == 'MultiPolygon':
        # Use first polygon's centroid
        lats = [p[1] for p in coords[0][0]]
        lngs = [p[0] for p in coords[0][0]]
        center_lat = sum(lats) / len(lats)
        center_lng = sum(lngs) / len(lngs)
    else:
        raise ValueError(f"Unsupported geometry type: {feature['geometry']['type']}")
    
    return get_region(center_lat, center_lng)

def simplify_feature(feature: Dict, tolerance: float) -> Dict:
    """Simplify a GeoJSON feature's geometry."""
    geom_type = feature['geometry']['type']
    coords = feature['geometry']['coordinates']
    
    if geom_type == 'Polygon':
        new_coords = []
        for ring in coords:
            new_ring = []
            for i in range(0, len(ring), 2):  # Take every other point
                new_ring.append(ring[i])
            if len(new_ring) < 4:  # Ensure minimum points for a valid polygon
                new_ring = ring
            new_coords.append(new_ring)
        feature['geometry']['coordinates'] = new_coords
    
    elif geom_type == 'MultiPolygon':
        new_coords = []
        for polygon in coords:
            new_polygon = []
            for ring in polygon:
                new_ring = []
                for i in range(0, len(ring), 2):  # Take every other point
                    new_ring.append(ring[i])
                if len(new_ring) < 4:  # Ensure minimum points for a valid polygon
                    new_ring = ring
                new_polygon.append(new_ring)
            new_coords.append(new_polygon)
        feature['geometry']['coordinates'] = new_coords
    
    return feature

def split_geojson(input_file: str, output_dir: str):
    """Split GeoJSON file into chunks based on zoom levels and regions."""
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Load GeoJSON file
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    # Zoom level tolerances
    zoom_levels = {
        'high': 0.01,    # Highest detail
        'medium': 0.05,  # Medium detail
        'low': 0.1       # Lowest detail
    }
    
    # Group features by region
    regions: Dict[str, List] = {}
    for feature in data['features']:
        region = get_feature_region(feature)
        if region not in regions:
            regions[region] = []
        regions[region].append(feature)
    
    # Create chunks for each zoom level and region
    for zoom, tolerance in zoom_levels.items():
        zoom_dir = os.path.join(output_dir, zoom)
        os.makedirs(zoom_dir, exist_ok=True)
        
        for region, features in regions.items():
            # Simplify features based on zoom level
            simplified_features = [simplify_feature(feature.copy(), tolerance) for feature in features]
            
            # Create chunk file
            chunk_data = {
                'type': 'FeatureCollection',
                'features': simplified_features
            }
            
            chunk_file = os.path.join(zoom_dir, f"{region}.json")
            with open(chunk_file, 'w') as f:
                json.dump(chunk_data, f)

def main():
    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent
    
    # Input and output paths
    input_file = project_root / 'src/web/static/assets/countries-lite.json'
    output_dir = project_root / 'src/web/static/assets/map-chunks'
    
    # Split the GeoJSON file
    split_geojson(str(input_file), str(output_dir))
    print(f"Successfully split GeoJSON into chunks at {output_dir}")

if __name__ == '__main__':
    main()