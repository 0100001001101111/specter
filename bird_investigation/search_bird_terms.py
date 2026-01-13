#!/usr/bin/env python3
"""
SPECTER Bird Investigation - Test 4: Search NUFORC for Bird-Related Terms
"""

import pandas as pd
import numpy as np
import re
from collections import Counter

print("=" * 60)
print("BIRD-UFO CORRELATION: SEARCHING NUFORC FOR BIRD TERMS")
print("=" * 60)

# Load UFO data
data_dir = "/Users/bobrothers/specter-phase2/data/raw"
ufo_columns = ['datetime', 'city', 'state', 'country', 'shape', 'duration_seconds',
               'duration_text', 'description', 'date_posted', 'latitude', 'longitude']
ufo_df = pd.read_csv(f"{data_dir}/complete.csv", names=ufo_columns, low_memory=False)
ufo_df['datetime'] = pd.to_datetime(ufo_df['datetime'], errors='coerce')
ufo_df['latitude'] = pd.to_numeric(ufo_df['latitude'], errors='coerce')
ufo_df['longitude'] = pd.to_numeric(ufo_df['longitude'], errors='coerce')

print(f"\nTotal NUFORC records: {len(ufo_df):,}")

# Define regions
PORTLAND = {'name': 'Portland', 'lat': 45.52, 'lon': -122.68, 'radius': 0.5}
SF = {'name': 'SF Bay Area', 'lat': 37.77, 'lon': -122.42, 'radius': 0.8}

def filter_region(df, region):
    return df[
        (abs(df['latitude'] - region['lat']) <= region['radius']) &
        (abs(df['longitude'] - region['lon']) <= region['radius'])
    ].copy()

portland_ufo = filter_region(ufo_df, PORTLAND)
sf_ufo = filter_region(ufo_df, SF)

print(f"Portland reports: {len(portland_ufo):,}")
print(f"SF Bay Area reports: {len(sf_ufo):,}")

# ============================================================
# BIRD-RELATED SEARCH TERMS
# ============================================================

BIRD_TERMS = [
    # Direct bird references
    r'\bbird\b', r'\bbirds\b', r'\bflock\b', r'\bflocks\b',
    r'\bgeese\b', r'\bgoose\b', r'\bduck\b', r'\bducks\b',
    r'\bseagull\b', r'\bgull\b', r'\bhawk\b', r'\beagle\b',
    r'\bcrow\b', r'\bcrows\b', r'\braven\b', r'\bpelican\b',
    r'\bfeather\b', r'\bwing\b', r'\bwings\b', r'\bflapping\b',
    r'\bmigrat', r'\bswarm\b',

    # Formation patterns (bird-like)
    r'\bv.?shape\b', r'\bv.?formation\b', r'\bwedge\b',
    r'\bchevron\b', r'\bboomerang\b',
    r'\bformation\b', r'\bflying.{0,20}formation\b',

    # Movement descriptions that could be birds
    r'\bundulat',  # undulating
    r'\bglid',     # gliding
    r'\bsoar',     # soaring
    r'\bswoop',    # swooping
    r'\bhover',    # hovering (also hummingbirds)
]

# Search patterns that suggest biological origin
BEHAVIOR_TERMS = [
    r'\berratic\b', r'\berratically\b',
    r'\birregular\b', r'\bunusual\b',
    r'\bconfused\b', r'\bdisoriented\b',
    r'\bcircl\w+\b',  # circling
    r'\bscatter\b', r'\bscattered\b',
    r'\bmass\b', r'\bswarm\b',
]

def search_descriptions(df, patterns, name=""):
    """Search descriptions for patterns."""
    results = []
    df = df.dropna(subset=['description'])

    for pattern in patterns:
        matches = df[df['description'].str.contains(pattern, case=False, na=False, regex=True)]
        if len(matches) > 0:
            results.append({
                'pattern': pattern,
                'count': len(matches),
                'pct': 100 * len(matches) / len(df)
            })

    return pd.DataFrame(results).sort_values('count', ascending=False)

# Search all regions
print("\n" + "=" * 60)
print("BIRD-RELATED TERMS IN NUFORC DATA")
print("=" * 60)

# Full dataset
print("\n--- FULL DATASET (All US) ---")
full_results = search_descriptions(ufo_df, BIRD_TERMS, "Full")
print(full_results.head(15).to_string(index=False))

# SF Bay Area
print("\n--- SF BAY AREA ---")
sf_results = search_descriptions(sf_ufo, BIRD_TERMS, "SF")
print(sf_results.head(15).to_string(index=False))

# Portland
print("\n--- PORTLAND ---")
portland_results = search_descriptions(portland_ufo, BIRD_TERMS, "Portland")
print(portland_results.head(15).to_string(index=False))

# ============================================================
# EXTRACT BIRD-RELATED REPORTS
# ============================================================
print("\n" + "=" * 60)
print("DETAILED BIRD-RELATED REPORTS")
print("=" * 60)

# Create combined pattern
bird_pattern = '|'.join([r'\bbird', r'\bflock', r'\bgeese', r'\bgull',
                         r'v.?formation', r'\bchevron', r'\bwedge'])

# Find bird-related reports in SF Bay Area
sf_bird_reports = sf_ufo[sf_ufo['description'].str.contains(bird_pattern, case=False, na=False, regex=True)]
print(f"\nSF Bay Area reports mentioning birds/formations: {len(sf_bird_reports)}")

if len(sf_bird_reports) > 0:
    print("\nSample bird-related SF reports:")
    print("-" * 80)
    for _, row in sf_bird_reports.head(10).iterrows():
        date_str = row['datetime'].strftime('%Y-%m-%d') if pd.notna(row['datetime']) else 'Unknown'
        shape = row['shape'] if pd.notna(row['shape']) else 'Unknown'
        desc = str(row['description'])[:300] if pd.notna(row['description']) else 'No description'
        print(f"\n[{date_str}] Shape: {shape}")
        print(f"  {desc}...")

# Portland
portland_bird_reports = portland_ufo[portland_ufo['description'].str.contains(bird_pattern, case=False, na=False, regex=True)]
print(f"\n\nPortland reports mentioning birds/formations: {len(portland_bird_reports)}")

if len(portland_bird_reports) > 0:
    print("\nSample bird-related Portland reports:")
    print("-" * 80)
    for _, row in portland_bird_reports.head(10).iterrows():
        date_str = row['datetime'].strftime('%Y-%m-%d') if pd.notna(row['datetime']) else 'Unknown'
        shape = row['shape'] if pd.notna(row['shape']) else 'Unknown'
        desc = str(row['description'])[:300] if pd.notna(row['description']) else 'No description'
        print(f"\n[{date_str}] Shape: {shape}")
        print(f"  {desc}...")

# ============================================================
# V-FORMATION / CHEVRON ANALYSIS
# ============================================================
print("\n" + "=" * 60)
print("V-FORMATION / CHEVRON SHAPE ANALYSIS")
print("=" * 60)

# These are classic bird formation shapes
v_shapes = ['chevron', 'boomerang', 'v-shaped', 'formation']

for region_name, region_df in [('SF Bay', sf_ufo), ('Portland', portland_ufo), ('Full US', ufo_df)]:
    chevron_reports = region_df[region_df['shape'].str.lower().isin(['chevron', 'formation']) |
                                 region_df['description'].str.contains(r'v.?shape|v.?formation|chevron|boomerang',
                                                                        case=False, na=False, regex=True)]
    print(f"\n{region_name}: {len(chevron_reports)} chevron/V-formation reports ({100*len(chevron_reports)/len(region_df):.2f}%)")

# ============================================================
# MIGRATION SEASON ANALYSIS
# ============================================================
print("\n" + "=" * 60)
print("MIGRATION SEASON ANALYSIS")
print("=" * 60)

# Bird migration peaks: Spring (Mar-May) and Fall (Sep-Nov)
sf_ufo['month'] = sf_ufo['datetime'].dt.month

# Define migration vs non-migration
migration_months = [3, 4, 5, 9, 10, 11]  # Spring and Fall
sf_ufo['migration_season'] = sf_ufo['month'].isin(migration_months)

migration_reports = sf_ufo[sf_ufo['migration_season']]
non_migration_reports = sf_ufo[~sf_ufo['migration_season']]

print(f"\nSF Bay Area by Season:")
print(f"  Migration season (Mar-May, Sep-Nov): {len(migration_reports)} reports")
print(f"  Non-migration season: {len(non_migration_reports)} reports")
print(f"  Migration/Non-migration ratio: {len(migration_reports)/len(non_migration_reports):.2f}")

# Expected ratio if uniform: 6/6 = 1.0
print(f"  Expected ratio if uniform: 1.0")

# Check V-formations specifically during migration
v_pattern = r'v.?shape|v.?formation|chevron|boomerang|formation|flock'
sf_v_reports = sf_ufo[sf_ufo['description'].str.contains(v_pattern, case=False, na=False, regex=True) |
                       sf_ufo['shape'].str.lower().isin(['chevron', 'formation'])]

sf_v_migration = sf_v_reports[sf_v_reports['migration_season']]
sf_v_non_migration = sf_v_reports[~sf_v_reports['migration_season']]

print(f"\nV-Formation/Chevron reports:")
print(f"  During migration: {len(sf_v_migration)}")
print(f"  Outside migration: {len(sf_v_non_migration)}")
if len(sf_v_non_migration) > 0:
    print(f"  Migration/Non-migration ratio: {len(sf_v_migration)/len(sf_v_non_migration):.2f}")

# Monthly breakdown of V-formations
print("\nV-Formation reports by month (SF Bay):")
v_by_month = sf_v_reports.groupby('month').size()
for month in range(1, 13):
    count = v_by_month.get(month, 0)
    bar = '*' * int(count / 2)
    month_name = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][month-1]
    migration = '*' if month in migration_months else ' '
    print(f"  {month_name} [{migration}]: {count:3d} {bar}")

# ============================================================
# SAVE BIRD-RELATED REPORTS
# ============================================================
combined_regions = pd.concat([sf_ufo, portland_ufo])
all_bird_reports = combined_regions[
    combined_regions['description'].str.contains(bird_pattern, case=False, na=False, regex=True)
]
all_bird_reports['region'] = all_bird_reports.apply(
    lambda x: 'Portland' if abs(x['latitude'] - 45.52) < 0.5 else 'SF Bay', axis=1
)

output_path = "/Users/bobrothers/specter-phase2/bird_investigation/bird_related_reports.csv"
all_bird_reports.to_csv(output_path, index=False)
print(f"\n\nSaved {len(all_bird_reports)} bird-related reports to: {output_path}")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print("""
KEY FINDINGS:

1. V-FORMATIONS: Chevron and V-shaped reports exist in significant numbers.
   These are classic bird flock formations.

2. MIGRATION CORRELATION: Need to check if V-formation reports spike
   during migration seasons (Spring/Fall).

3. DIRECT BIRD MENTIONS: Some reporters explicitly mention birds or
   question whether they saw birds.

4. NEXT STEPS:
   - Correlate V-formation reports with seismic activity
   - Pull eBird data for same coordinates/dates
   - Check NEXRAD radar for mass bird movements
""")
