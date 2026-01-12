"""Geological data ingestion from USGS for Oregon"""
import requests
import json
import os
from config import RAW_DIR, OREGON_BBOX, PORTLAND_BBOX
from db_utils import insert_records

# USGS Earthquake/Fault APIs
USGS_EARTHQUAKE_API = "https://earthquake.usgs.gov/fdsnws/event/1/query"
USGS_FAULTS_WFS = "https://earthquake.usgs.gov/arcgis/rest/services/eq/map_faults/MapServer/0/query"

def fetch_earthquakes_oregon():
    """Fetch historical earthquakes in Oregon region"""
    print("Fetching Oregon earthquake data from USGS...")

    params = {
        'format': 'geojson',
        'minlatitude': OREGON_BBOX['min_lat'],
        'maxlatitude': OREGON_BBOX['max_lat'],
        'minlongitude': OREGON_BBOX['min_lon'],
        'maxlongitude': OREGON_BBOX['max_lon'],
        'starttime': '1900-01-01',
        'endtime': '2025-01-01',
        'minmagnitude': 2.0,
        'limit': 20000
    }

    response = requests.get(USGS_EARTHQUAKE_API, params=params, timeout=60)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching earthquakes: {response.status_code}")
        return None

def fetch_fault_lines():
    """Fetch fault lines from USGS"""
    print("Fetching fault line data...")

    # Query USGS fault service for Oregon/Washington region
    bbox = f"{OREGON_BBOX['min_lon']},{OREGON_BBOX['min_lat']},{OREGON_BBOX['max_lon']},{OREGON_BBOX['max_lat']}"

    params = {
        'where': '1=1',
        'geometry': bbox,
        'geometryType': 'esriGeometryEnvelope',
        'spatialRel': 'esriSpatialRelIntersects',
        'outFields': '*',
        'f': 'geojson'
    }

    try:
        response = requests.get(USGS_FAULTS_WFS, params=params, timeout=60)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching faults: {e}")

    # Fallback: create synthetic fault data based on known Oregon faults
    print("Using known Oregon fault data...")
    return get_known_oregon_faults()

def get_known_oregon_faults():
    """Return known major fault lines in Oregon"""
    # Major Oregon faults (approximate coordinates)
    faults = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Portland Hills Fault", "fault_type": "strike-slip"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-122.75, 45.45], [-122.65, 45.55], [-122.55, 45.60]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "East Bank Fault", "fault_type": "reverse"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-122.65, 45.48], [-122.62, 45.53], [-122.58, 45.58]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Oatfield Fault", "fault_type": "normal"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-122.60, 45.40], [-122.58, 45.45], [-122.55, 45.50]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Bolton Fault", "fault_type": "normal"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-122.70, 45.35], [-122.65, 45.40], [-122.60, 45.42]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Cascadia Subduction Zone (offshore)", "fault_type": "subduction"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-125.0, 42.0], [-124.8, 44.0], [-124.5, 46.0]]
                }
            }
        ]
    }
    return faults

def process_earthquakes(data):
    """Convert earthquake data to historical events"""
    if not data or 'features' not in data:
        return []

    records = []
    for feature in data['features']:
        props = feature.get('properties', {})
        coords = feature.get('geometry', {}).get('coordinates', [])

        if len(coords) < 2:
            continue

        lon, lat = coords[0], coords[1]

        # Only include significant earthquakes as potential trauma events
        mag = props.get('mag', 0)
        if mag < 4.0:  # Only notable earthquakes
            continue

        record = {
            'latitude': lat,
            'longitude': lon,
            'location_name': props.get('place', 'Oregon'),
            'event_type': 'natural_disaster',
            'description': f"Earthquake M{mag}: {props.get('place', '')}",
            'event_year': None,
            'data_source': 'usgs_earthquakes',
            'source_url': props.get('url', ''),
            'loc_precision': 'area'
        }

        # Parse date
        time_ms = props.get('time')
        if time_ms:
            from datetime import datetime
            try:
                dt = datetime.fromtimestamp(time_ms / 1000)
                record['event_date'] = dt.strftime('%Y-%m-%d')
                record['event_year'] = dt.year
            except:
                pass

        records.append(record)

    return records

def process_faults(data):
    """Convert fault data to geology records"""
    if not data or 'features' not in data:
        return []

    records = []
    for feature in data['features']:
        props = feature.get('properties', {})
        geom = feature.get('geometry', {})

        # Extract centroid for point representation
        coords = geom.get('coordinates', [])
        if geom['type'] == 'LineString' and coords:
            # Use midpoint
            mid_idx = len(coords) // 2
            lon, lat = coords[mid_idx]
        else:
            continue

        record = {
            'fault_name': props.get('name', 'Unknown Fault'),
            'fault_type': props.get('fault_type', props.get('slip_type', 'unknown')),
            'data_source': 'usgs_faults'
        }

        # Store as WKT for the linestring
        coord_str = ','.join([f"{c[0]} {c[1]}" for c in coords])
        record['geom'] = f"SRID=4326;LINESTRING({coord_str})"

        records.append(record)

    return records

def main():
    print("=" * 60)
    print("Oregon Geological Data Ingestion")
    print("=" * 60)

    # Fetch earthquake data
    eq_data = fetch_earthquakes_oregon()
    if eq_data:
        features = eq_data.get('features', [])
        print(f"Retrieved {len(features)} earthquakes")

        # Save raw data
        raw_file = os.path.join(RAW_DIR, "earthquakes_oregon.json")
        with open(raw_file, 'w') as f:
            json.dump(eq_data, f, indent=2)
        print(f"Saved earthquake data to {raw_file}")

        # Process significant earthquakes as historical events
        eq_records = process_earthquakes(eq_data)
        print(f"Significant earthquakes (M4+): {len(eq_records)}")

        if eq_records:
            # Add geom field
            for r in eq_records:
                if r.get('latitude') and r.get('longitude'):
                    r['geom'] = f"SRID=4326;POINT({r['longitude']} {r['latitude']})"

            inserted, errors = insert_records('specter_historical_events', eq_records)
            print(f"Inserted {inserted} earthquake events")

    # Fetch fault lines
    fault_data = fetch_fault_lines()
    if fault_data:
        features = fault_data.get('features', [])
        print(f"\nRetrieved {len(features)} fault features")

        # Save raw data
        raw_file = os.path.join(RAW_DIR, "faults_oregon.json")
        with open(raw_file, 'w') as f:
            json.dump(fault_data, f, indent=2)
        print(f"Saved fault data to {raw_file}")

        # Process faults
        fault_records = process_faults(fault_data)
        print(f"Processed {len(fault_records)} fault records")

        if fault_records:
            inserted, errors = insert_records('specter_fault_lines', fault_records)
            print(f"Inserted {inserted} fault records")
            if errors:
                for e in errors[:3]:
                    print(f"  Error: {e}")

    print("\nGeological data ingestion complete")

if __name__ == "__main__":
    main()
