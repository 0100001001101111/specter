"""Infrastructure data ingestion via Overpass API for Portland metro"""
import requests
import json
import time
import os
from config import RAW_DIR, PORTLAND_BBOX, OVERPASS_DELAY
from db_utils import insert_records

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def query_overpass(query):
    """Execute Overpass API query"""
    response = requests.post(OVERPASS_URL, data={'data': query}, timeout=180)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Overpass error: {response.status_code}")
        return None

def get_portland_bbox_str():
    """Get bounding box string for Overpass"""
    b = PORTLAND_BBOX
    return f"{b['min_lat']},{b['min_lon']},{b['max_lat']},{b['max_lon']}"

def fetch_cemeteries():
    """Fetch all cemeteries in Portland metro"""
    print("Fetching cemeteries...")
    bbox = get_portland_bbox_str()
    query = f"""
    [out:json][timeout:120];
    (
      node["landuse"="cemetery"]({bbox});
      way["landuse"="cemetery"]({bbox});
      relation["landuse"="cemetery"]({bbox});
      node["amenity"="grave_yard"]({bbox});
      way["amenity"="grave_yard"]({bbox});
    );
    out center;
    """
    return query_overpass(query)

def fetch_churches():
    """Fetch all churches/religious buildings"""
    print("Fetching churches and religious buildings...")
    bbox = get_portland_bbox_str()
    query = f"""
    [out:json][timeout:120];
    (
      node["amenity"="place_of_worship"]({bbox});
      way["amenity"="place_of_worship"]({bbox});
      node["building"="church"]({bbox});
      way["building"="church"]({bbox});
    );
    out center;
    """
    return query_overpass(query)

def fetch_hospitals():
    """Fetch hospitals and medical facilities"""
    print("Fetching hospitals...")
    bbox = get_portland_bbox_str()
    query = f"""
    [out:json][timeout:120];
    (
      node["amenity"="hospital"]({bbox});
      way["amenity"="hospital"]({bbox});
      node["healthcare"="hospital"]({bbox});
      way["healthcare"="hospital"]({bbox});
    );
    out center;
    """
    return query_overpass(query)

def fetch_power_infrastructure():
    """Fetch power lines and substations"""
    print("Fetching power infrastructure...")
    bbox = get_portland_bbox_str()
    query = f"""
    [out:json][timeout:180];
    (
      way["power"="line"]({bbox});
      node["power"="substation"]({bbox});
      way["power"="substation"]({bbox});
      node["power"="transformer"]({bbox});
      way["power"="tower"]({bbox});
    );
    out center;
    """
    return query_overpass(query)

def fetch_cell_towers():
    """Fetch cell/radio towers"""
    print("Fetching cell/radio towers...")
    bbox = get_portland_bbox_str()
    query = f"""
    [out:json][timeout:120];
    (
      node["tower:type"="communication"]({bbox});
      node["man_made"="mast"]({bbox});
      node["man_made"="tower"]["tower:type"="communication"]({bbox});
      node["telecom"="antenna"]({bbox});
    );
    out center;
    """
    return query_overpass(query)

def fetch_historic_buildings():
    """Fetch historic and old buildings"""
    print("Fetching historic buildings...")
    bbox = get_portland_bbox_str()
    query = f"""
    [out:json][timeout:120];
    (
      node["historic"]({bbox});
      way["historic"]({bbox});
      node["heritage"]({bbox});
      way["heritage"]({bbox});
    );
    out center;
    """
    return query_overpass(query)

def fetch_former_institutions():
    """Fetch prisons, asylums, schools"""
    print("Fetching institutional buildings...")
    bbox = get_portland_bbox_str()
    query = f"""
    [out:json][timeout:120];
    (
      node["amenity"="prison"]({bbox});
      way["amenity"="prison"]({bbox});
      node["amenity"="school"]({bbox});
      way["amenity"="school"]({bbox});
      node["building"="hospital"]({bbox});
      way["building"="hospital"]({bbox});
    );
    out center;
    """
    return query_overpass(query)

def extract_coords(element):
    """Extract coordinates from Overpass element"""
    if element['type'] == 'node':
        return element.get('lat'), element.get('lon')
    elif 'center' in element:
        return element['center'].get('lat'), element['center'].get('lon')
    return None, None

def process_overpass_result(data, infra_type):
    """Convert Overpass result to SPECTER infrastructure records"""
    if not data or 'elements' not in data:
        return []

    records = []
    for elem in data['elements']:
        lat, lon = extract_coords(elem)
        if lat is None or lon is None:
            continue

        tags = elem.get('tags', {})
        name = tags.get('name', tags.get('description', ''))

        record = {
            'infrastructure_type': infra_type,
            'name': name[:200] if name else None,
            'latitude': lat,
            'longitude': lon,
            'data_source': 'openstreetmap',
            'osm_id': elem.get('id'),
            'active': True
        }

        # Extract additional properties
        if 'voltage' in tags:
            try:
                record['voltage_kv'] = float(tags['voltage']) / 1000
            except:
                pass

        if 'start_date' in tags:
            try:
                year = int(tags['start_date'][:4])
                record['construction_year'] = year
            except:
                pass

        records.append(record)

    return records

def main():
    print("=" * 60)
    print("Portland Infrastructure Data Ingestion")
    print("=" * 60)

    all_records = []

    # Fetch each type with delays
    fetchers = [
        (fetch_cemeteries, 'cemetery'),
        (fetch_churches, 'church'),
        (fetch_hospitals, 'hospital'),
        (fetch_power_infrastructure, 'substation'),  # Will include various power types
        (fetch_cell_towers, 'cell_tower'),
        (fetch_historic_buildings, 'other'),
        (fetch_former_institutions, 'prison'),
    ]

    for fetcher, default_type in fetchers:
        try:
            data = fetcher()
            if data:
                elem_count = len(data.get('elements', []))
                print(f"  Found {elem_count} elements")

                records = process_overpass_result(data, default_type)
                all_records.extend(records)
                print(f"  Processed {len(records)} records")

            time.sleep(OVERPASS_DELAY)
        except Exception as e:
            print(f"  Error: {e}")
            continue

    print(f"\nTotal infrastructure records: {len(all_records)}")

    # Save raw data
    raw_file = os.path.join(RAW_DIR, "infrastructure_portland.json")
    with open(raw_file, 'w') as f:
        json.dump(all_records, f, indent=2, default=str)
    print(f"Saved to {raw_file}")

    # Insert into database
    print("\nInserting into database...")

    # Need to handle geometry separately - insert without geom first
    for record in all_records:
        lat = record.pop('latitude', None)
        lon = record.pop('longitude', None)
        if lat and lon:
            # We'll update geom later with SQL
            record['geom'] = f"SRID=4326;POINT({lon} {lat})"

    inserted, errors = insert_records('specter_infrastructure', all_records)
    print(f"Inserted {inserted} records")
    if errors:
        print(f"Errors: {len(errors)}")
        for e in errors[:3]:
            print(f"  {e}")

    return all_records

if __name__ == "__main__":
    main()
