"""SPECTER Feature Correlation Analysis"""
import numpy as np
import pandas as pd
from scipy import stats
import json
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from config import OUTPUT_DIR, PORTLAND_BBOX, PERMUTATION_ITERATIONS
from db_utils import query_table, insert_records

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in meters"""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)

    a = np.sin(dphi/2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda/2)**2
    return 2 * R * np.arcsin(np.sqrt(a))

def fetch_paranormal_reports():
    """Fetch paranormal reports with coordinates"""
    reports = query_table(
        'specter_paranormal_reports',
        select='id,latitude,longitude,event_date,phenomenon_type',
        filters='latitude=not.is.null&longitude=not.is.null',
        limit=5000
    )
    return pd.DataFrame(reports)

def fetch_infrastructure_by_type(infra_type):
    """Fetch infrastructure of a specific type"""
    # Parse geometry to get lat/lon
    # The geom is stored as WKT, need to extract coordinates
    infra = query_table(
        'specter_infrastructure',
        select='id,geom,infrastructure_type,name',
        filters=f'infrastructure_type=eq.{infra_type}',
        limit=5000
    )
    return infra

def fetch_historical_events():
    """Fetch historical events with coordinates"""
    events = query_table(
        'specter_historical_events',
        select='id,latitude,longitude,event_type,event_year,death_count',
        filters='latitude=not.is.null&longitude=not.is.null',
        limit=5000
    )
    return pd.DataFrame(events)

def parse_point_from_wkt(geom_str):
    """Extract lat/lon from WKT point string"""
    if not geom_str or not isinstance(geom_str, str):
        return None, None
    try:
        # Format: SRID=4326;POINT(lon lat) or POINT(lon lat)
        if 'POINT' in geom_str:
            coords = geom_str.split('POINT')[1].replace('(', '').replace(')', '').strip()
            lon, lat = coords.split()
            return float(lat), float(lon)
    except:
        pass
    return None, None

def calculate_min_distances(report_coords, feature_coords):
    """Calculate minimum distance from each report to any feature"""
    if len(feature_coords) == 0:
        return np.array([np.nan] * len(report_coords))

    distances = []
    for r_lat, r_lon in report_coords:
        min_dist = np.inf
        for f_lat, f_lon in feature_coords:
            d = haversine_distance(r_lat, r_lon, f_lat, f_lon)
            if d < min_dist:
                min_dist = d
        distances.append(min_dist)

    return np.array(distances)

def permutation_test(report_coords, feature_coords, n_permutations=50):
    """Test if reports are closer to features than expected by chance"""
    # Actual mean distance
    actual_distances = calculate_min_distances(report_coords, feature_coords)
    actual_mean = np.nanmean(actual_distances)

    if np.isnan(actual_mean):
        return None

    # Generate null distribution by shuffling report locations
    null_means = []

    # Get bounding box of reports
    lats = [c[0] for c in report_coords]
    lons = [c[1] for c in report_coords]
    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)

    for _ in range(n_permutations):
        # Generate random points in same bounding box
        random_lats = np.random.uniform(lat_min, lat_max, len(report_coords))
        random_lons = np.random.uniform(lon_min, lon_max, len(report_coords))
        random_coords = list(zip(random_lats, random_lons))

        null_distances = calculate_min_distances(random_coords, feature_coords)
        null_means.append(np.nanmean(null_distances))

    # Calculate p-value (one-tailed: are reports CLOSER than random?)
    p_value = sum(nm <= actual_mean for nm in null_means) / n_permutations

    # Effect size (Cohen's d)
    null_std = np.std(null_means)
    effect_size = (np.mean(null_means) - actual_mean) / null_std if null_std > 0 else 0

    return {
        'actual_mean_distance_m': actual_mean,
        'null_mean_distance_m': np.mean(null_means),
        'null_std_m': null_std,
        'p_value': p_value,
        'effect_size': effect_size,
        'direction': 'closer' if actual_mean < np.mean(null_means) else 'farther',
        'significant': p_value < 0.05
    }

def analyze_feature_correlation(reports_df, feature_name, feature_coords):
    """Analyze correlation between reports and a specific feature"""
    print(f"\nAnalyzing correlation with {feature_name}...")
    print(f"  Reports: {len(reports_df)}, Features: {len(feature_coords)}")

    if len(feature_coords) == 0:
        print(f"  No {feature_name} features found")
        return None

    report_coords = list(zip(reports_df['latitude'].values, reports_df['longitude'].values))

    # Run permutation test
    result = permutation_test(report_coords, feature_coords, n_permutations=PERMUTATION_ITERATIONS)

    if result:
        print(f"  Actual mean distance: {result['actual_mean_distance_m']:.1f}m")
        print(f"  Null mean distance: {result['null_mean_distance_m']:.1f}m")
        print(f"  Direction: Reports are {result['direction']} than random")
        print(f"  P-value: {result['p_value']:.4f}")
        print(f"  Significant (p<0.05): {result['significant']}")

    return result

def main():
    print("=" * 60)
    print("SPECTER Feature Correlation Analysis")
    print("=" * 60)

    # Fetch reports
    print("\nFetching paranormal reports...")
    reports_df = fetch_paranormal_reports()
    print(f"Retrieved {len(reports_df)} reports")

    # Filter to Portland metro for focused analysis
    portland_reports = reports_df[
        (reports_df['latitude'] >= PORTLAND_BBOX['min_lat']) &
        (reports_df['latitude'] <= PORTLAND_BBOX['max_lat']) &
        (reports_df['longitude'] >= PORTLAND_BBOX['min_lon']) &
        (reports_df['longitude'] <= PORTLAND_BBOX['max_lon'])
    ].copy()

    analysis_df = portland_reports if len(portland_reports) >= 30 else reports_df
    print(f"Analyzing {len(analysis_df)} reports")

    results = {}

    # Test correlation with each infrastructure type
    infra_types = ['cemetery', 'church', 'hospital', 'substation', 'cell_tower']

    for infra_type in infra_types:
        infra_data = fetch_infrastructure_by_type(infra_type)
        print(f"\nFetched {len(infra_data)} {infra_type} records")

        # Parse coordinates from geometry
        feature_coords = []
        for item in infra_data:
            lat, lon = parse_point_from_wkt(item.get('geom'))
            if lat and lon:
                feature_coords.append((lat, lon))

        print(f"  Parsed {len(feature_coords)} coordinates")

        result = analyze_feature_correlation(analysis_df, infra_type, feature_coords)
        if result:
            results[infra_type] = result

    # Test correlation with historical events
    print("\n" + "=" * 40)
    print("Historical Event Correlations")

    historical_df = fetch_historical_events()
    print(f"Fetched {len(historical_df)} historical events")

    if len(historical_df) > 0:
        # All historical events
        hist_coords = list(zip(historical_df['latitude'].values, historical_df['longitude'].values))
        result = analyze_feature_correlation(analysis_df, 'historical_events', hist_coords)
        if result:
            results['historical_events'] = result

        # By event type
        for event_type in historical_df['event_type'].unique():
            type_df = historical_df[historical_df['event_type'] == event_type]
            if len(type_df) >= 5:
                type_coords = list(zip(type_df['latitude'].values, type_df['longitude'].values))
                result = analyze_feature_correlation(analysis_df, f'historical_{event_type}', type_coords)
                if result:
                    results[f'historical_{event_type}'] = result

    # Summary
    print("\n" + "=" * 60)
    print("CORRELATION SUMMARY")
    print("=" * 60)

    significant_correlations = []
    for feature, result in results.items():
        if result['significant']:
            significant_correlations.append({
                'feature': feature,
                'direction': result['direction'],
                'p_value': result['p_value'],
                'effect_size': result['effect_size']
            })

    if significant_correlations:
        print("\nSIGNIFICANT CORRELATIONS FOUND:")
        for corr in sorted(significant_correlations, key=lambda x: x['p_value']):
            print(f"  - {corr['feature']}: reports are {corr['direction']} (p={corr['p_value']:.4f}, d={corr['effect_size']:.2f})")
    else:
        print("\nNo significant correlations found at p<0.05")

    # Non-significant results
    print("\nNon-significant results:")
    for feature, result in results.items():
        if not result['significant']:
            print(f"  - {feature}: p={result['p_value']:.4f}")

    # Save results
    output_file = os.path.join(OUTPUT_DIR, 'reports', 'correlation_results.json')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nResults saved to {output_file}")

    # Store in database
    db_records = []
    for feature, result in results.items():
        db_records.append({
            'feature_name': feature,
            'actual_mean_distance': result['actual_mean_distance_m'],
            'null_mean_distance': result['null_mean_distance_m'],
            'p_value': result['p_value'],
            'effect_size': result['effect_size'],
            'direction': result['direction']
        })

    inserted, errors = insert_records('specter_correlations', db_records)
    print(f"Stored {inserted} correlation results in database")

    return results

if __name__ == "__main__":
    main()
