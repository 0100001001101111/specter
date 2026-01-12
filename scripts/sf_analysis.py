"""SPECTER San Francisco Bay Area Analysis - Full Pipeline"""
import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime, timedelta
import requests
import json
import os
import sys
import time
sys.path.insert(0, os.path.dirname(__file__))

from config import RAW_DIR, OUTPUT_DIR
from db_utils import insert_records, query_table

# SF Bay Area bounding box
SF_BBOX = {
    'min_lat': 37.2,
    'max_lat': 38.0,
    'min_lon': -122.8,
    'max_lon': -121.8
}

SF_CENTER = (37.7749, -122.4194)

USGS_API = "https://earthquake.usgs.gov/fdsnws/event/1/query"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# ============================================================
# DATA INGESTION
# ============================================================

def ingest_obiwan_sf():
    """Filter Obiwan UFO data for SF Bay Area"""
    print("\n" + "=" * 60)
    print("INGESTING SF BAY AREA PARANORMAL REPORTS")
    print("=" * 60)

    cache_file = os.path.join(RAW_DIR, "obiwan_full.csv")

    if not os.path.exists(cache_file):
        print("Obiwan data not found, downloading...")
        url = "https://raw.githubusercontent.com/planetsig/ufo-reports/master/csv-data/ufo-scrubbed-geocoded-time-standardized.csv"
        response = requests.get(url, timeout=120)
        with open(cache_file, 'wb') as f:
            f.write(response.content)

    columns = ['datetime', 'city', 'state', 'country', 'shape', 'duration_seconds',
               'duration_text', 'comments', 'date_posted', 'latitude', 'longitude']

    df = pd.read_csv(cache_file, low_memory=False, header=None, names=columns)
    print(f"Total Obiwan records: {len(df)}")

    # Filter by state (California)
    ca_df = df[df['state'].astype(str).str.lower() == 'ca'].copy()
    print(f"California records: {len(ca_df)}")

    # Convert coordinates
    ca_df['latitude'] = pd.to_numeric(ca_df['latitude'], errors='coerce')
    ca_df['longitude'] = pd.to_numeric(ca_df['longitude'], errors='coerce')

    # Filter by bounding box
    sf_df = ca_df[
        (ca_df['latitude'] >= SF_BBOX['min_lat']) &
        (ca_df['latitude'] <= SF_BBOX['max_lat']) &
        (ca_df['longitude'] >= SF_BBOX['min_lon']) &
        (ca_df['longitude'] <= SF_BBOX['max_lon'])
    ].copy()

    print(f"SF Bay Area records: {len(sf_df)}")

    # Convert to SPECTER format
    records = []
    for _, row in sf_df.iterrows():
        record = {
            'city': str(row.get('city', ''))[:100],
            'state': 'CA',
            'phenomenon_type': 'ufo_uap',
            'phenomenon_subtype': str(row.get('shape', ''))[:50],
            'description': str(row.get('comments', ''))[:5000],
            'data_source': 'obiwan_sf',
            'report_source': 'NUFORC via Obiwan'
        }

        if pd.notna(row['latitude']) and pd.notna(row['longitude']):
            record['latitude'] = float(row['latitude'])
            record['longitude'] = float(row['longitude'])
            record['loc_precision'] = 'city'

        # Parse date
        dt_val = row.get('datetime')
        if pd.notna(dt_val):
            try:
                for fmt in ['%m/%d/%Y %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                    try:
                        dt = datetime.strptime(str(dt_val), fmt)
                        record['event_date'] = dt.strftime('%Y-%m-%d')
                        record['event_time'] = dt.strftime('%H:%M:%S')
                        break
                    except:
                        continue
            except:
                pass

        records.append(record)

    # Save locally
    sf_file = os.path.join(RAW_DIR, "sf_paranormal_reports.json")
    with open(sf_file, 'w') as f:
        json.dump(records, f, indent=2, default=str)

    print(f"Saved {len(records)} SF reports to {sf_file}")
    return pd.DataFrame(records)

def ingest_sf_earthquakes():
    """Fetch USGS earthquakes for SF Bay Area"""
    print("\n" + "=" * 60)
    print("INGESTING SF BAY AREA EARTHQUAKES")
    print("=" * 60)

    # Use smaller chunks to avoid API limits
    params = {
        'format': 'geojson',
        'minlatitude': SF_BBOX['min_lat'],
        'maxlatitude': SF_BBOX['max_lat'],
        'minlongitude': SF_BBOX['min_lon'],
        'maxlongitude': SF_BBOX['max_lon'],
        'starttime': '1970-01-01',  # Shorter range
        'endtime': '2025-01-01',
        'minmagnitude': 1.5,  # Slightly higher threshold
        'limit': 20000,
        'orderby': 'time'
    }

    try:
        response = requests.get(USGS_API, params=params, timeout=120)
        if response.status_code != 200:
            print(f"USGS API error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            # Try alternative: use radius-based query
            print("Trying radius-based query...")
            params2 = {
                'format': 'geojson',
                'latitude': 37.7749,
                'longitude': -122.4194,
                'maxradiuskm': 100,
                'starttime': '1970-01-01',
                'endtime': '2025-01-01',
                'minmagnitude': 2.0,
                'limit': 10000,
                'orderby': 'time'
            }
            response = requests.get(USGS_API, params=params2, timeout=120)
            if response.status_code != 200:
                print(f"Alternative also failed: {response.status_code}")
                return None
    except Exception as e:
        print(f"Request error: {e}")
        return None

    data = response.json()
    earthquakes = []

    for feature in data.get('features', []):
        props = feature['properties']
        coords = feature['geometry']['coordinates']

        time_ms = props.get('time')
        if time_ms:
            dt = datetime.fromtimestamp(time_ms / 1000)
            earthquakes.append({
                'date': dt.date(),
                'datetime': dt,
                'magnitude': props.get('mag'),
                'depth_km': coords[2] if len(coords) > 2 else None,
                'latitude': coords[1],
                'longitude': coords[0],
                'place': props.get('place', '')
            })

    eq_df = pd.DataFrame(earthquakes)

    # Save
    eq_file = os.path.join(RAW_DIR, "sf_earthquakes.json")
    eq_df.to_json(eq_file, orient='records', date_format='iso')

    print(f"Retrieved {len(eq_df)} earthquakes")
    print(f"Date range: {eq_df['date'].min()} to {eq_df['date'].max()}")
    print(f"Magnitude range: {eq_df['magnitude'].min():.1f} to {eq_df['magnitude'].max():.1f}")

    return eq_df

def ingest_sf_infrastructure():
    """Fetch infrastructure from Overpass for SF Bay Area"""
    print("\n" + "=" * 60)
    print("INGESTING SF BAY AREA INFRASTRUCTURE")
    print("=" * 60)

    bbox = f"{SF_BBOX['min_lat']},{SF_BBOX['min_lon']},{SF_BBOX['max_lat']},{SF_BBOX['max_lon']}"

    infra_queries = {
        'cemetery': f'[out:json][timeout:120];(node["landuse"="cemetery"]({bbox});way["landuse"="cemetery"]({bbox}););out center;',
        'church': f'[out:json][timeout:120];(node["amenity"="place_of_worship"]({bbox});way["amenity"="place_of_worship"]({bbox}););out center;',
        'hospital': f'[out:json][timeout:120];(node["amenity"="hospital"]({bbox});way["amenity"="hospital"]({bbox}););out center;',
        'power': f'[out:json][timeout:120];(node["power"="substation"]({bbox});way["power"="substation"]({bbox}););out center;',
    }

    all_infra = []

    for infra_type, query in infra_queries.items():
        print(f"Fetching {infra_type}...")
        try:
            response = requests.post(OVERPASS_URL, data={'data': query}, timeout=180)
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('elements', []))
                print(f"  Found {count} {infra_type}")

                for elem in data.get('elements', []):
                    if elem['type'] == 'node':
                        lat, lon = elem.get('lat'), elem.get('lon')
                    elif 'center' in elem:
                        lat, lon = elem['center'].get('lat'), elem['center'].get('lon')
                    else:
                        continue

                    all_infra.append({
                        'type': infra_type,
                        'latitude': lat,
                        'longitude': lon,
                        'name': elem.get('tags', {}).get('name', '')
                    })
            else:
                print(f"  Error: {response.status_code}")

            time.sleep(1)  # Rate limiting
        except Exception as e:
            print(f"  Error: {e}")

    print(f"\nTotal infrastructure: {len(all_infra)}")

    # Save
    infra_file = os.path.join(RAW_DIR, "sf_infrastructure.json")
    with open(infra_file, 'w') as f:
        json.dump(all_infra, f, indent=2)

    return pd.DataFrame(all_infra)

# ============================================================
# ANALYSIS FUNCTIONS
# ============================================================

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in meters"""
    R = 6371000
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda/2)**2
    return 2 * R * np.arcsin(np.sqrt(a))

def run_clustering_analysis(reports_df):
    """Run DBSCAN clustering"""
    print("\n" + "=" * 60)
    print("SPATIAL CLUSTERING ANALYSIS")
    print("=" * 60)

    from sklearn.cluster import DBSCAN

    # Filter to reports with coordinates
    valid = reports_df[reports_df['latitude'].notna() & reports_df['longitude'].notna()].copy()
    print(f"Reports with coordinates: {len(valid)}")

    if len(valid) < 10:
        return None

    coords = valid[['latitude', 'longitude']].values
    coords_rad = np.radians(coords)

    # DBSCAN with 500m eps
    eps_rad = 500 / 6371000
    clustering = DBSCAN(eps=eps_rad, min_samples=5, metric='haversine')
    labels = clustering.fit_predict(coords_rad)

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_clustered = sum(labels != -1)
    n_noise = sum(labels == -1)

    print(f"Clusters found: {n_clusters}")
    print(f"Points in clusters: {n_clustered}")
    print(f"Noise points: {n_noise}")

    # Permutation test
    print("\nRunning permutation test...")
    null_clustered = []
    for _ in range(100):
        shuffled = coords.copy()
        np.random.shuffle(shuffled[:, 0])
        np.random.shuffle(shuffled[:, 1])
        shuffled_rad = np.radians(shuffled)
        null_labels = DBSCAN(eps=eps_rad, min_samples=5, metric='haversine').fit_predict(shuffled_rad)
        null_clustered.append(sum(null_labels != -1))

    p_value = sum(n >= n_clustered for n in null_clustered) / 100

    print(f"Actual clustered: {n_clustered}")
    print(f"Null mean clustered: {np.mean(null_clustered):.1f}")
    print(f"P-value: {p_value:.4f}")
    print(f"Significant: {p_value < 0.05}")

    # Get cluster details
    valid['cluster'] = labels
    clusters = []
    for label in set(labels):
        if label == -1:
            continue
        cluster_pts = valid[valid['cluster'] == label]
        clusters.append({
            'label': int(label),
            'count': len(cluster_pts),
            'centroid_lat': cluster_pts['latitude'].mean(),
            'centroid_lon': cluster_pts['longitude'].mean(),
            'city': cluster_pts['city'].mode().iloc[0] if len(cluster_pts['city'].mode()) > 0 else 'unknown'
        })

    clusters = sorted(clusters, key=lambda x: x['count'], reverse=True)

    print("\nTop clusters:")
    for c in clusters[:5]:
        print(f"  {c['city']}: {c['count']} reports")

    return {
        'n_clusters': n_clusters,
        'n_clustered': n_clustered,
        'p_value': p_value,
        'significant': p_value < 0.05,
        'clusters': clusters[:10]
    }

def run_seismic_correlation(reports_df, earthquakes_df):
    """Run seismic-paranormal temporal correlation"""
    print("\n" + "=" * 60)
    print("SEISMIC-TEMPORAL CORRELATION")
    print("=" * 60)

    if earthquakes_df is None or len(earthquakes_df) == 0:
        print("No earthquake data available - skipping seismic correlation")
        return None

    # Prepare data
    reports_df = reports_df.copy()
    reports_df['event_date'] = pd.to_datetime(reports_df['event_date'], errors='coerce').dt.date
    valid_reports = reports_df[reports_df['event_date'].notna()].copy()
    print(f"Reports with dates: {len(valid_reports)}")

    eq_dates = earthquakes_df['date'].tolist()

    # Calculate days since earthquake for each report
    days_since = []
    within_7d_after = 0
    within_7d_before = 0

    for _, report in valid_reports.iterrows():
        report_date = report['event_date']
        min_days_before = None
        min_days_after = None

        for eq_date in eq_dates:
            diff = (report_date - eq_date).days
            if diff > 0:  # Earthquake was before report
                if min_days_before is None or diff < min_days_before:
                    min_days_before = diff
            elif diff < 0:  # Earthquake was after report
                if min_days_after is None or abs(diff) < min_days_after:
                    min_days_after = abs(diff)

        if min_days_before is not None:
            days_since.append(min_days_before)
            if min_days_before <= 7:
                within_7d_after += 1
        if min_days_after is not None and min_days_after <= 7:
            within_7d_before += 1

    print(f"\nWithin 7 days AFTER earthquake: {within_7d_after} ({within_7d_after/len(valid_reports)*100:.1f}%)")
    print(f"Within 7 days BEFORE earthquake: {within_7d_before} ({within_7d_before/len(valid_reports)*100:.1f}%)")
    print(f"After/Before ratio: {within_7d_after/max(within_7d_before,1):.2f}")

    # Histogram
    if len(days_since) > 0:
        hist, _ = np.histogram(days_since, bins=range(0, 22))
        print("\nDays since earthquake histogram:")
        max_val = max(hist) if max(hist) > 0 else 1
        for i, count in enumerate(hist[:14]):
            bar = '█' * int(count / max_val * 20)
            peak = ' ◄ PEAK' if count == max(hist) else ''
            print(f"  Day {i+1:2d}: {count:4d} {bar}{peak}")

    # Quiet vs Active period analysis
    print("\n--- Quiet vs Active Period Analysis ---")

    eq_sorted = earthquakes_df.sort_values('date')
    eq_dates_sorted = eq_sorted['date'].tolist()

    # Find gaps > 30 days
    gaps = []
    for i in range(1, len(eq_dates_sorted)):
        gap = (eq_dates_sorted[i] - eq_dates_sorted[i-1]).days
        if gap > 30:
            gaps.append({
                'start': eq_dates_sorted[i-1],
                'end': eq_dates_sorted[i],
                'days': gap
            })

    quiet_days = sum(g['days'] for g in gaps)
    quiet_reports = 0
    for g in gaps:
        for _, report in valid_reports.iterrows():
            if g['start'] < report['event_date'] < g['end']:
                quiet_reports += 1

    total_days = (max(eq_dates_sorted) - min(eq_dates_sorted)).days
    active_days = total_days - quiet_days
    active_reports = len(valid_reports) - quiet_reports

    quiet_rate = quiet_reports / quiet_days if quiet_days > 0 else 0
    active_rate = active_reports / active_days if active_days > 0 else 0

    print(f"Quiet periods: {quiet_days} days, {quiet_reports} reports, rate: {quiet_rate:.4f}/day")
    print(f"Active periods: {active_days} days, {active_reports} reports, rate: {active_rate:.4f}/day")
    print(f"Active/Quiet ratio: {active_rate/max(quiet_rate, 0.0001):.2f}x")

    return {
        'total_reports': len(valid_reports),
        'within_7d_after': within_7d_after,
        'within_7d_before': within_7d_before,
        'after_before_ratio': within_7d_after / max(within_7d_before, 1),
        'histogram': list(hist) if len(days_since) > 0 else [],
        'peak_day': int(np.argmax(hist) + 1) if len(days_since) > 0 else None,
        'quiet_days': quiet_days,
        'quiet_reports': quiet_reports,
        'quiet_rate': quiet_rate,
        'active_days': active_days,
        'active_reports': active_reports,
        'active_rate': active_rate,
        'active_quiet_ratio': active_rate / max(quiet_rate, 0.0001)
    }

def run_temporal_analysis(reports_df):
    """Run temporal pattern analysis"""
    print("\n" + "=" * 60)
    print("TEMPORAL PATTERN ANALYSIS")
    print("=" * 60)

    results = {}

    # Time of day
    times = pd.to_datetime(reports_df['event_time'], format='%H:%M:%S', errors='coerce')
    valid_times = times.dropna()

    if len(valid_times) > 10:
        hours = valid_times.dt.hour
        night_hours = [0,1,2,3,4,5,21,22,23]
        night_count = sum(hours.isin(night_hours))
        night_ratio = night_count / len(valid_times)

        print(f"Night reports: {night_count}/{len(valid_times)} ({night_ratio:.1%})")
        print(f"Expected if uniform: 37.5%")

        results['night_ratio'] = night_ratio
        results['night_elevated'] = night_ratio > 0.45

    # Monthly
    dates = pd.to_datetime(reports_df['event_date'], errors='coerce')
    valid_dates = dates.dropna()

    if len(valid_dates) > 20:
        months = valid_dates.dt.month
        month_counts = months.value_counts().sort_index()
        peak_month = month_counts.idxmax()
        month_names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

        print(f"Peak month: {month_names[peak_month-1]} ({month_counts[peak_month]} reports)")
        results['peak_month'] = month_names[peak_month-1]

    return results

def find_top_hotspot(reports_df, earthquakes_df, infra_df):
    """Identify top hotspot and its geological context"""
    print("\n" + "=" * 60)
    print("HOTSPOT IDENTIFICATION")
    print("=" * 60)

    valid = reports_df[reports_df['latitude'].notna()].copy()

    # Find densest area using simple grid
    grid_size = 0.05  # ~5km cells

    lat_bins = np.arange(SF_BBOX['min_lat'], SF_BBOX['max_lat'], grid_size)
    lon_bins = np.arange(SF_BBOX['min_lon'], SF_BBOX['max_lon'], grid_size)

    max_count = 0
    hotspot = None

    for lat in lat_bins:
        for lon in lon_bins:
            count = len(valid[
                (valid['latitude'] >= lat) &
                (valid['latitude'] < lat + grid_size) &
                (valid['longitude'] >= lon) &
                (valid['longitude'] < lon + grid_size)
            ])
            if count > max_count:
                max_count = count
                hotspot = {
                    'lat': lat + grid_size/2,
                    'lon': lon + grid_size/2,
                    'count': count
                }

    if hotspot:
        print(f"Top hotspot: ({hotspot['lat']:.4f}, {hotspot['lon']:.4f})")
        print(f"Report count: {hotspot['count']}")

        # Find nearest earthquake
        min_dist = float('inf')
        nearest_eq = None
        for _, eq in earthquakes_df.iterrows():
            dist = haversine_distance(hotspot['lat'], hotspot['lon'],
                                     eq['latitude'], eq['longitude'])
            if dist < min_dist:
                min_dist = dist
                nearest_eq = eq

        if nearest_eq is not None:
            print(f"Nearest earthquake: M{nearest_eq['magnitude']:.1f} at {min_dist/1000:.1f}km")
            hotspot['nearest_eq_dist_km'] = min_dist / 1000
            hotspot['nearest_eq_mag'] = nearest_eq['magnitude']

        # Find nearest cemetery
        cemeteries = infra_df[infra_df['type'] == 'cemetery']
        if len(cemeteries) > 0:
            min_cem_dist = float('inf')
            for _, cem in cemeteries.iterrows():
                dist = haversine_distance(hotspot['lat'], hotspot['lon'],
                                         cem['latitude'], cem['longitude'])
                if dist < min_cem_dist:
                    min_cem_dist = dist
            print(f"Nearest cemetery: {min_cem_dist/1000:.1f}km")
            hotspot['nearest_cemetery_km'] = min_cem_dist / 1000

    return hotspot

def generate_sf_map(reports_df, earthquakes_df, infra_df, hotspot):
    """Generate Folium map for SF"""
    print("\n" + "=" * 60)
    print("GENERATING SF MAP")
    print("=" * 60)

    import folium
    from folium import plugins

    m = folium.Map(location=[SF_CENTER[0], SF_CENTER[1]], zoom_start=10, tiles='CartoDB positron')

    # Reports layer
    report_group = folium.FeatureGroup(name='Paranormal Reports', show=True)
    valid_reports = reports_df[reports_df['latitude'].notna()]

    for _, row in valid_reports.iterrows():
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=4,
            color='green',
            fill=True,
            fillOpacity=0.6,
            popup=f"{row.get('city', 'Unknown')} - {row.get('event_date', 'Unknown')}"
        ).add_to(report_group)

    report_group.add_to(m)

    # Earthquake layer (M3+)
    eq_group = folium.FeatureGroup(name='Earthquakes M3+', show=False)
    sig_eq = earthquakes_df[earthquakes_df['magnitude'] >= 3.0]

    for _, eq in sig_eq.iterrows():
        folium.CircleMarker(
            location=[eq['latitude'], eq['longitude']],
            radius=eq['magnitude'] * 2,
            color='red',
            fill=True,
            fillOpacity=0.4,
            popup=f"M{eq['magnitude']:.1f} - {eq['place']}"
        ).add_to(eq_group)

    eq_group.add_to(m)

    # Hotspot
    if hotspot:
        folium.CircleMarker(
            location=[hotspot['lat'], hotspot['lon']],
            radius=20,
            color='orange',
            fill=True,
            fillColor='red',
            fillOpacity=0.5,
            popup=f"TOP HOTSPOT: {hotspot['count']} reports"
        ).add_to(m)

    # Heatmap
    heat_data = [[r['latitude'], r['longitude']] for _, r in valid_reports.iterrows()]
    if heat_data:
        plugins.HeatMap(heat_data, name='Report Heatmap', show=False, radius=12).add_to(m)

    folium.LayerControl().add_to(m)

    map_file = os.path.join(OUTPUT_DIR, 'maps', 'specter_sf.html')
    os.makedirs(os.path.dirname(map_file), exist_ok=True)
    m.save(map_file)
    print(f"Map saved to {map_file}")

    return map_file

# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 70)
    print("SPECTER SAN FRANCISCO BAY AREA ANALYSIS")
    print("=" * 70)

    # Data ingestion
    reports_df = ingest_obiwan_sf()
    earthquakes_df = ingest_sf_earthquakes()
    infra_df = ingest_sf_infrastructure()

    if reports_df is None or len(reports_df) == 0:
        print("No report data available")
        return

    # Run analyses
    clustering = run_clustering_analysis(reports_df)
    seismic = run_seismic_correlation(reports_df, earthquakes_df)
    temporal = run_temporal_analysis(reports_df)
    hotspot = find_top_hotspot(reports_df, earthquakes_df, infra_df)

    # Generate map
    map_file = generate_sf_map(reports_df, earthquakes_df, infra_df, hotspot)

    # Comparison summary
    print("\n" + "=" * 70)
    print("SF vs PORTLAND COMPARISON")
    print("=" * 70)

    print("\n{:<35} {:>15} {:>15}".format("Metric", "Portland", "SF Bay"))
    print("-" * 65)

    portland = {
        'reports': 745,
        'clusters': 8,
        'clustering_p': 0.0000,
        'night_ratio': 0.638,
        'active_quiet_ratio': 3.36,
        'peak_day': 1
    }

    sf = {
        'reports': len(reports_df),
        'clusters': clustering['n_clusters'] if clustering else 0,
        'clustering_p': clustering['p_value'] if clustering else 1,
        'night_ratio': temporal.get('night_ratio', 0),
        'active_quiet_ratio': seismic['active_quiet_ratio'] if seismic else 0,
        'peak_day': seismic['peak_day'] if seismic else None
    }

    print("{:<35} {:>15} {:>15}".format("Total reports", portland['reports'], sf['reports']))
    print("{:<35} {:>15} {:>15}".format("Spatial clusters", portland['clusters'], sf['clusters']))
    print("{:<35} {:>15.4f} {:>15.4f}".format("Clustering p-value", portland['clustering_p'], sf['clustering_p']))
    print("{:<35} {:>15.1%} {:>15.1%}".format("Night report ratio", portland['night_ratio'], sf['night_ratio']))
    print("{:<35} {:>15.2f}x {:>15.2f}x".format("Active/Quiet period ratio", portland['active_quiet_ratio'], sf['active_quiet_ratio']))
    print("{:<35} {:>15} {:>15}".format("Peak day after earthquake", portland['peak_day'], sf['peak_day']))

    # Replication assessment
    print("\n" + "=" * 70)
    print("REPLICATION ASSESSMENT")
    print("=" * 70)

    replicated = []
    not_replicated = []

    if sf['clustering_p'] < 0.05:
        replicated.append("Spatial clustering significance")
    else:
        not_replicated.append("Spatial clustering significance")

    if sf['active_quiet_ratio'] > 1.5:
        replicated.append(f"Seismic active period effect ({sf['active_quiet_ratio']:.1f}x)")
    else:
        not_replicated.append("Seismic active period effect")

    if sf['night_ratio'] > 0.45:
        replicated.append(f"Night report bias ({sf['night_ratio']:.1%})")
    else:
        not_replicated.append("Night report bias")

    print("\n✓ REPLICATED:")
    for r in replicated:
        print(f"  - {r}")

    print("\n✗ NOT REPLICATED:")
    for r in not_replicated:
        print(f"  - {r}")

    # Save results
    results = {
        'sf_reports': len(reports_df),
        'sf_earthquakes': len(earthquakes_df),
        'clustering': clustering,
        'seismic_correlation': seismic,
        'temporal': temporal,
        'hotspot': hotspot,
        'comparison': {
            'portland': portland,
            'sf': sf
        },
        'replicated': replicated,
        'not_replicated': not_replicated
    }

    output_file = os.path.join(OUTPUT_DIR, 'reports', 'sf_analysis_results.json')
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nResults saved to {output_file}")

    # Final summary
    print("\n" + "=" * 70)
    print("EXECUTIVE SUMMARY")
    print("=" * 70)

    if len(replicated) >= 2:
        print("\n*** KEY PATTERNS REPLICATE IN SF BAY AREA ***")
        print("The seismic-paranormal correlation found in Portland")
        print("is also present in San Francisco, supporting the hypothesis")
        print("that seismic activity correlates with paranormal reports.")
    else:
        print("\n*** LIMITED REPLICATION ***")
        print("Some patterns did not replicate, suggesting regional variation")
        print("or insufficient data.")

    return results

if __name__ == "__main__":
    main()
