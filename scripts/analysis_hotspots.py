"""SPECTER Multi-Layer Hotspot Detection"""
import numpy as np
import pandas as pd
from scipy import ndimage
import json
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from config import OUTPUT_DIR, PORTLAND_BBOX
from db_utils import query_table, insert_records

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in meters"""
    R = 6371000
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda/2)**2
    return 2 * R * np.arcsin(np.sqrt(a))

def fetch_all_data():
    """Fetch all relevant data for hotspot analysis"""
    data = {}

    # Paranormal reports
    reports = query_table(
        'specter_paranormal_reports',
        select='latitude,longitude,phenomenon_type',
        filters='latitude=not.is.null&longitude=not.is.null',
        limit=5000
    )
    data['reports'] = pd.DataFrame(reports)
    print(f"Reports: {len(data['reports'])}")

    # Infrastructure by type
    for infra_type in ['cemetery', 'church', 'hospital', 'substation', 'cell_tower']:
        infra = query_table(
            'specter_infrastructure',
            select='geom',
            filters=f'infrastructure_type=eq.{infra_type}',
            limit=5000
        )
        data[f'infra_{infra_type}'] = infra
        print(f"{infra_type}: {len(infra)}")

    # Historical events
    events = query_table(
        'specter_historical_events',
        select='latitude,longitude,event_type,death_count',
        filters='latitude=not.is.null&longitude=not.is.null',
        limit=5000
    )
    data['historical'] = pd.DataFrame(events)
    print(f"Historical events: {len(data['historical'])}")

    return data

def parse_wkt_point(geom_str):
    """Parse WKT point to (lat, lon)"""
    if not geom_str or not isinstance(geom_str, str):
        return None, None
    try:
        if 'POINT' in geom_str:
            coords = geom_str.split('POINT')[1].replace('(', '').replace(')', '').strip()
            lon, lat = coords.split()
            return float(lat), float(lon)
    except:
        pass
    return None, None

def create_grid(bbox, resolution=0.01):
    """Create analysis grid"""
    lats = np.arange(bbox['min_lat'], bbox['max_lat'], resolution)
    lons = np.arange(bbox['min_lon'], bbox['max_lon'], resolution)
    return lats, lons

def calculate_point_density(points, grid_lats, grid_lons, radius_m=1000):
    """Calculate point density at each grid cell"""
    density = np.zeros((len(grid_lats), len(grid_lons)))

    for i, lat in enumerate(grid_lats):
        for j, lon in enumerate(grid_lons):
            count = 0
            for _, row in points.iterrows():
                p_lat, p_lon = row.get('latitude'), row.get('longitude')
                if p_lat and p_lon:
                    dist = haversine_distance(lat, lon, p_lat, p_lon)
                    if dist < radius_m:
                        count += 1
            density[i, j] = count

    return density

def calculate_proximity_score(coords_list, grid_lats, grid_lons, max_dist_m=2000):
    """Calculate inverse distance score to features"""
    score = np.zeros((len(grid_lats), len(grid_lons)))

    if not coords_list:
        return score

    for i, lat in enumerate(grid_lats):
        for j, lon in enumerate(grid_lons):
            min_dist = np.inf
            for f_lat, f_lon in coords_list:
                dist = haversine_distance(lat, lon, f_lat, f_lon)
                if dist < min_dist:
                    min_dist = dist

            # Inverse distance score (capped)
            if min_dist < max_dist_m:
                score[i, j] = 1 - (min_dist / max_dist_m)
            else:
                score[i, j] = 0

    return score

def normalize_layer(layer):
    """Normalize layer to 0-1 range"""
    if layer.max() == layer.min():
        return np.zeros_like(layer)
    return (layer - layer.min()) / (layer.max() - layer.min())

def find_hotspot_peaks(combined_score, grid_lats, grid_lons, threshold_percentile=90):
    """Find local maxima in combined score"""
    # Find local maxima
    local_max = combined_score == ndimage.maximum_filter(combined_score, size=3)

    # Apply threshold
    threshold = np.percentile(combined_score, threshold_percentile)
    significant = local_max & (combined_score > threshold)

    # Extract hotspot locations
    hotspots = []
    y_indices, x_indices = np.where(significant)

    for y, x in zip(y_indices, x_indices):
        hotspots.append({
            'latitude': grid_lats[y],
            'longitude': grid_lons[x],
            'combined_score': combined_score[y, x]
        })

    return sorted(hotspots, key=lambda h: h['combined_score'], reverse=True)

def main():
    print("=" * 60)
    print("SPECTER Multi-Layer Hotspot Detection")
    print("=" * 60)

    # Fetch all data
    print("\nFetching data...")
    data = fetch_all_data()

    # Create analysis grid (coarser for speed)
    print("\nCreating analysis grid...")
    grid_lats, grid_lons = create_grid(PORTLAND_BBOX, resolution=0.02)
    print(f"Grid size: {len(grid_lats)} x {len(grid_lons)} = {len(grid_lats) * len(grid_lons)} cells")

    layers = {}

    # Layer 1: Report density
    print("\nCalculating report density...")
    if len(data['reports']) > 0:
        layers['report_density'] = calculate_point_density(
            data['reports'], grid_lats, grid_lons, radius_m=1500
        )
        print(f"  Max density: {layers['report_density'].max()}")

    # Layer 2: Cemetery proximity
    print("Calculating cemetery proximity...")
    cemetery_coords = []
    for item in data.get('infra_cemetery', []):
        lat, lon = parse_wkt_point(item.get('geom'))
        if lat and lon:
            cemetery_coords.append((lat, lon))
    if cemetery_coords:
        layers['cemetery_proximity'] = calculate_proximity_score(
            cemetery_coords, grid_lats, grid_lons
        )
        print(f"  Cemeteries found: {len(cemetery_coords)}")

    # Layer 3: Historical death proximity
    print("Calculating historical event proximity...")
    if len(data['historical']) > 0:
        hist_coords = list(zip(
            data['historical']['latitude'].dropna().values,
            data['historical']['longitude'].dropna().values
        ))
        layers['historical_proximity'] = calculate_proximity_score(
            hist_coords, grid_lats, grid_lons
        )
        print(f"  Historical events: {len(hist_coords)}")

    # Layer 4: Power infrastructure proximity (as potential EMF source)
    print("Calculating power infrastructure proximity...")
    power_coords = []
    for item in data.get('infra_substation', []):
        lat, lon = parse_wkt_point(item.get('geom'))
        if lat and lon:
            power_coords.append((lat, lon))
    if power_coords:
        layers['power_proximity'] = calculate_proximity_score(
            power_coords, grid_lats, grid_lons
        )
        print(f"  Power infrastructure: {len(power_coords)}")

    # Layer 5: Church proximity
    print("Calculating church proximity...")
    church_coords = []
    for item in data.get('infra_church', []):
        lat, lon = parse_wkt_point(item.get('geom'))
        if lat and lon:
            church_coords.append((lat, lon))
    if church_coords:
        layers['church_proximity'] = calculate_proximity_score(
            church_coords, grid_lats, grid_lons
        )
        print(f"  Churches: {len(church_coords)}")

    # Normalize all layers
    print("\nNormalizing layers...")
    normalized = {}
    for name, layer in layers.items():
        normalized[name] = normalize_layer(layer)
        print(f"  {name}: mean={normalized[name].mean():.3f}")

    # Combined score (weighted sum)
    print("\nCalculating combined hotspot score...")
    weights = {
        'report_density': 2.0,       # Primary signal
        'cemetery_proximity': 1.0,
        'historical_proximity': 1.5,
        'power_proximity': 0.5,
        'church_proximity': 0.5
    }

    combined = np.zeros((len(grid_lats), len(grid_lons)))
    for name, layer in normalized.items():
        weight = weights.get(name, 1.0)
        combined += layer * weight

    # Normalize combined score
    combined = normalize_layer(combined)

    # Find hotspot peaks
    print("\nIdentifying hotspot peaks...")
    hotspots = find_hotspot_peaks(combined, grid_lats, grid_lons, threshold_percentile=85)
    print(f"Found {len(hotspots)} hotspot locations")

    # Add layer scores to hotspots
    for hotspot in hotspots:
        lat_idx = np.argmin(np.abs(grid_lats - hotspot['latitude']))
        lon_idx = np.argmin(np.abs(grid_lons - hotspot['longitude']))

        for name, layer in normalized.items():
            hotspot[f'{name}_score'] = layer[lat_idx, lon_idx]

    # Report top hotspots
    print("\n" + "=" * 60)
    print("TOP CONVERGENCE HOTSPOTS")
    print("=" * 60)

    for i, hs in enumerate(hotspots[:15]):
        print(f"\n#{i+1} - Score: {hs['combined_score']:.3f}")
        print(f"   Location: ({hs['latitude']:.4f}, {hs['longitude']:.4f})")
        print(f"   Layer scores:")
        for key, val in hs.items():
            if key.endswith('_score') and key != 'combined_score':
                print(f"     {key}: {val:.3f}")

    # Identify convergence patterns
    print("\n" + "=" * 60)
    print("CONVERGENCE ANALYSIS")
    print("=" * 60)

    high_convergence = [h for h in hotspots if h['combined_score'] > 0.6]
    print(f"\nHigh convergence hotspots (score > 0.6): {len(high_convergence)}")

    multi_factor = []
    for h in hotspots:
        factors = sum(1 for k, v in h.items()
                     if k.endswith('_score') and k != 'combined_score' and v > 0.3)
        if factors >= 3:
            multi_factor.append(h)

    print(f"Multi-factor hotspots (3+ factors > 0.3): {len(multi_factor)}")

    # Save results
    results = {
        'total_hotspots': len(hotspots),
        'high_convergence_count': len(high_convergence),
        'multi_factor_count': len(multi_factor),
        'hotspots': hotspots[:50],  # Top 50
        'layer_weights': weights,
        'grid_resolution_degrees': 0.02
    }

    output_file = os.path.join(OUTPUT_DIR, 'reports', 'hotspot_results.json')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nResults saved to {output_file}")

    # Store in database
    db_records = []
    for h in hotspots[:30]:
        db_records.append({
            'location': f"SRID=4326;POINT({h['longitude']} {h['latitude']})",
            'latitude': h['latitude'],
            'longitude': h['longitude'],
            'combined_score': h['combined_score'],
            'report_density_score': h.get('report_density_score', 0),
            'cemetery_proximity_score': h.get('cemetery_proximity_score', 0),
            'historical_death_score': h.get('historical_proximity_score', 0),
            'power_line_score': h.get('power_proximity_score', 0)
        })

    inserted, errors = insert_records('specter_hotspots', db_records)
    print(f"Stored {inserted} hotspot records in database")

    return results

if __name__ == "__main__":
    main()
