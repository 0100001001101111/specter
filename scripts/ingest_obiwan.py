"""Download and process Obiwan UFO dataset for Oregon"""
import requests
import pandas as pd
import json
import os
from datetime import datetime
from config import RAW_DIR, OREGON_BBOX, PORTLAND_BBOX
from db_utils import insert_records

OBIWAN_URL = "https://raw.githubusercontent.com/planetsig/ufo-reports/master/csv-data/ufo-scrubbed-geocoded-time-standardized.csv"

def download_obiwan_data():
    """Download the Obiwan UFO dataset"""
    print("Downloading Obiwan UFO dataset...")
    print("(This is ~25MB, may take a minute)")

    cache_file = os.path.join(RAW_DIR, "obiwan_full.csv")

    # Define column names since the CSV has no headers
    columns = ['datetime', 'city', 'state', 'country', 'shape', 'duration_seconds',
               'duration_text', 'comments', 'date_posted', 'latitude', 'longitude']

    if os.path.exists(cache_file):
        print(f"Using cached file: {cache_file}")
        return pd.read_csv(cache_file, low_memory=False, header=None, names=columns)

    response = requests.get(OBIWAN_URL, timeout=120)
    if response.status_code != 200:
        print(f"Failed to download: {response.status_code}")
        return None

    with open(cache_file, 'wb') as f:
        f.write(response.content)

    print(f"Downloaded and saved to {cache_file}")
    return pd.read_csv(cache_file, low_memory=False, header=None, names=columns)

def filter_oregon(df):
    """Filter dataset for Oregon reports"""
    print(f"Columns: {df.columns.tolist()}")
    print(f"Sample data:\n{df.head(2)}")

    # Filter by state column
    if 'state' in df.columns:
        # Handle both 'or' and 'OR'
        oregon_df = df[df['state'].astype(str).str.lower() == 'or'].copy()
        print(f"Filtered by state: {len(oregon_df)} records")
        return oregon_df

    # Fallback: filter by coordinates
    print("Falling back to coordinate filter")
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')

    oregon_df = df[
        (df['latitude'] >= OREGON_BBOX['min_lat']) &
        (df['latitude'] <= OREGON_BBOX['max_lat']) &
        (df['longitude'] >= OREGON_BBOX['min_lon']) &
        (df['longitude'] <= OREGON_BBOX['max_lon'])
    ].copy()

    return oregon_df

def is_portland_metro(lat, lon):
    """Check if coordinates are in Portland metro area"""
    if pd.isna(lat) or pd.isna(lon):
        return False
    return (PORTLAND_BBOX['min_lat'] <= lat <= PORTLAND_BBOX['max_lat'] and
            PORTLAND_BBOX['min_lon'] <= lon <= PORTLAND_BBOX['max_lon'])

def convert_to_specter_format(df):
    """Convert Obiwan format to SPECTER schema"""
    records = []

    # Our columns: datetime, city, state, country, shape, duration_seconds, duration_text, comments, date_posted, latitude, longitude
    print(f"Converting {len(df)} records to SPECTER format...")

    for _, row in df.iterrows():
        try:
            lat = row.get('latitude')
            lon = row.get('longitude')

            record = {
                'city': str(row.get('city', ''))[:100],
                'state': 'OR',
                'phenomenon_type': 'ufo_uap',
                'phenomenon_subtype': str(row.get('shape', ''))[:50],
                'description': str(row.get('comments', ''))[:5000],
                'data_source': 'obiwan',
                'report_source': 'NUFORC via Obiwan'
            }

            # Handle coordinates
            if pd.notna(lat) and pd.notna(lon):
                try:
                    record['latitude'] = float(lat)
                    record['longitude'] = float(lon)
                    record['loc_precision'] = 'city'
                except:
                    pass

            # Handle date
            dt_val = row.get('datetime')
            if pd.notna(dt_val):
                try:
                    if isinstance(dt_val, str):
                        # Try multiple formats
                        for fmt in ['%m/%d/%Y %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                            try:
                                dt = datetime.strptime(dt_val, fmt)
                                record['event_date'] = dt.strftime('%Y-%m-%d')
                                record['event_time'] = dt.strftime('%H:%M:%S')
                                break
                            except:
                                continue
                except:
                    pass

            # Handle duration
            dur_val = row.get('duration_seconds')
            if pd.notna(dur_val):
                try:
                    record['duration_seconds'] = int(float(dur_val))
                except:
                    pass

            records.append(record)

        except Exception as e:
            continue

    return records

def main():
    print("=" * 60)
    print("Obiwan UFO Dataset - Oregon Filter")
    print("=" * 60)

    df = download_obiwan_data()
    if df is None:
        print("Failed to download data")
        return

    print(f"Total records in dataset: {len(df)}")

    oregon_df = filter_oregon(df)
    print(f"Oregon records: {len(oregon_df)}")

    # Save filtered raw data
    oregon_file = os.path.join(RAW_DIR, "obiwan_oregon.csv")
    oregon_df.to_csv(oregon_file, index=False)
    print(f"Saved Oregon data to {oregon_file}")

    # Convert to SPECTER format
    records = convert_to_specter_format(oregon_df)
    print(f"Converted {len(records)} records to SPECTER format")

    # Count Portland metro
    portland_count = sum(1 for r in records
                        if is_portland_metro(r.get('latitude'), r.get('longitude')))
    print(f"Portland metro area: {portland_count} records")

    # Save processed data
    processed_file = os.path.join(RAW_DIR, "obiwan_oregon_processed.json")
    with open(processed_file, 'w') as f:
        json.dump(records, f, indent=2, default=str)

    # Insert into database
    print("\nInserting into database...")
    inserted, errors = insert_records('specter_paranormal_reports', records)
    print(f"Inserted {inserted} records")
    if errors:
        print(f"Errors: {len(errors)}")
        for e in errors[:3]:
            print(f"  {e}")

    return records

if __name__ == "__main__":
    main()
