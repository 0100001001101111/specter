#!/usr/bin/env python3
"""
SPECTER Bird Investigation - V-Formation/Seismic Correlation Test

Hypothesis: If V-formation UFO reports are birds disturbed by piezoelectric
emissions, they should correlate with seismic activity differently than
other UFO shapes.
"""

import pandas as pd
import numpy as np
from datetime import timedelta
import json
from scipy import stats

print("=" * 60)
print("V-FORMATION / SEISMIC CORRELATION TEST")
print("=" * 60)

# Load data
data_dir = "/Users/bobrothers/specter-phase2/data/raw"

# UFO reports
ufo_columns = ['datetime', 'city', 'state', 'country', 'shape', 'duration_seconds',
               'duration_text', 'description', 'date_posted', 'latitude', 'longitude']
ufo_df = pd.read_csv(f"{data_dir}/complete.csv", names=ufo_columns, low_memory=False)
ufo_df['datetime'] = pd.to_datetime(ufo_df['datetime'], errors='coerce')
ufo_df['latitude'] = pd.to_numeric(ufo_df['latitude'], errors='coerce')
ufo_df['longitude'] = pd.to_numeric(ufo_df['longitude'], errors='coerce')
ufo_df = ufo_df.dropna(subset=['datetime', 'latitude', 'longitude'])

# Earthquakes
with open(f"{data_dir}/earthquakes_sf.json") as f:
    eq_json = json.load(f)
eq_df = pd.DataFrame(eq_json['features'])
eq_df['time'] = pd.to_datetime(eq_df['properties'].apply(lambda x: x['time']), unit='ms')
eq_df['mag'] = eq_df['properties'].apply(lambda x: x.get('mag', 0))

# Filter to SF Bay Area
SF = {'lat': 37.77, 'lon': -122.42, 'radius': 0.8}
sf_ufo = ufo_df[
    (abs(ufo_df['latitude'] - SF['lat']) <= SF['radius']) &
    (abs(ufo_df['longitude'] - SF['lon']) <= SF['radius'])
].copy()

print(f"\nSF Bay Area UFO reports: {len(sf_ufo)}")
print(f"SF Bay Area earthquakes: {len(eq_df)}")

# ============================================================
# CATEGORIZE REPORTS BY SHAPE TYPE
# ============================================================

# V-formation / bird-like shapes
v_pattern = r'chevron|boomerang|v.?shape|v.?formation|wedge|formation'
sf_ufo['is_v_formation'] = (
    sf_ufo['shape'].str.lower().isin(['chevron', 'formation']) |
    sf_ufo['description'].str.contains(v_pattern, case=False, na=False, regex=True)
)

# Bird-related content
bird_pattern = r'\bbird|\bflock|\bgeese|\bgull|\bwing|\bfeather'
sf_ufo['mentions_birds'] = sf_ufo['description'].str.contains(bird_pattern, case=False, na=False, regex=True)

# Classic non-bird UFO shapes
classic_shapes = ['disk', 'disc', 'saucer', 'cigar', 'cylinder', 'egg', 'oval']
sf_ufo['is_classic_ufo'] = sf_ufo['shape'].str.lower().isin(classic_shapes)

# Light-based (could be anything)
light_shapes = ['light', 'fireball', 'flash']
sf_ufo['is_light'] = sf_ufo['shape'].str.lower().isin(light_shapes)

print(f"\nShape categorization:")
print(f"  V-formation/chevron: {sf_ufo['is_v_formation'].sum()}")
print(f"  Mentions birds: {sf_ufo['mentions_birds'].sum()}")
print(f"  Classic UFO shapes: {sf_ufo['is_classic_ufo'].sum()}")
print(f"  Light-based: {sf_ufo['is_light'].sum()}")

# ============================================================
# CALCULATE SEISMIC CORRELATION BY SHAPE TYPE
# ============================================================

def calculate_seismic_ratio(reports_df, eq_df, window_days=7):
    """Calculate seismic ratio for a set of reports."""
    active_count = 0
    quiet_count = 0

    for _, report in reports_df.iterrows():
        report_date = report['datetime']

        # Check for earthquakes within window before this report
        window_start = report_date - timedelta(days=window_days)
        eq_in_window = eq_df[
            (eq_df['time'] >= window_start) &
            (eq_df['time'] <= report_date)
        ]

        if len(eq_in_window) > 0:
            active_count += 1
        else:
            quiet_count += 1

    if quiet_count > 0:
        # Normalize by expected proportions (~60% active, ~40% quiet in SF)
        ratio = (active_count / 0.6) / (quiet_count / 0.4)
    else:
        ratio = float('inf') if active_count > 0 else 1.0

    return {
        'active': active_count,
        'quiet': quiet_count,
        'total': active_count + quiet_count,
        'ratio': ratio
    }

print("\n" + "=" * 60)
print("SEISMIC CORRELATION BY SHAPE TYPE")
print("=" * 60)

shape_categories = [
    ('V-Formation/Chevron', sf_ufo[sf_ufo['is_v_formation']]),
    ('Mentions Birds', sf_ufo[sf_ufo['mentions_birds']]),
    ('Classic UFO (disc/cigar)', sf_ufo[sf_ufo['is_classic_ufo']]),
    ('Light/Fireball', sf_ufo[sf_ufo['is_light']]),
    ('All SF Reports', sf_ufo)
]

results = []
for name, df in shape_categories:
    if len(df) < 5:
        print(f"\n{name}: Too few reports ({len(df)})")
        continue

    stats_7day = calculate_seismic_ratio(df, eq_df, 7)
    stats_3day = calculate_seismic_ratio(df, eq_df, 3)

    print(f"\n{name} (n={len(df)}):")
    print(f"  7-day window: {stats_7day['active']} active, {stats_7day['quiet']} quiet, ratio={stats_7day['ratio']:.2f}")
    print(f"  3-day window: {stats_3day['active']} active, {stats_3day['quiet']} quiet, ratio={stats_3day['ratio']:.2f}")

    results.append({
        'category': name,
        'n': len(df),
        'ratio_7day': stats_7day['ratio'],
        'ratio_3day': stats_3day['ratio']
    })

# ============================================================
# PRECURSOR ANALYSIS FOR V-FORMATIONS
# ============================================================
print("\n" + "=" * 60)
print("V-FORMATION PRECURSOR ANALYSIS")
print("=" * 60)

def get_day_offset(reports_df, eq_df, max_days=14):
    """Get distribution of days before/after nearest earthquake."""
    offsets = []

    for _, report in reports_df.iterrows():
        report_date = report['datetime']

        # Find nearest earthquake
        time_diffs = (eq_df['time'] - report_date).abs()
        if len(time_diffs) == 0:
            continue

        nearest_idx = time_diffs.idxmin()
        nearest_eq_time = eq_df.loc[nearest_idx, 'time']

        offset_days = (report_date - nearest_eq_time).days
        if abs(offset_days) <= max_days:
            offsets.append(offset_days)

    return offsets

# Get day offsets for each category
v_offsets = get_day_offset(sf_ufo[sf_ufo['is_v_formation']], eq_df)
classic_offsets = get_day_offset(sf_ufo[sf_ufo['is_classic_ufo']], eq_df)
all_offsets = get_day_offset(sf_ufo, eq_df)

print("\nDay offset distribution (negative = before earthquake):")
print("\nV-Formation reports:")
for day in range(-7, 8):
    count = v_offsets.count(day)
    bar = '*' * count
    label = 'BEFORE' if day < 0 else ('DAY 0' if day == 0 else 'AFTER')
    print(f"  Day {day:+3d} [{label:6s}]: {count:3d} {bar}")

print("\nClassic UFO reports:")
for day in range(-7, 8):
    count = classic_offsets.count(day)
    bar = '*' * count
    print(f"  Day {day:+3d}: {count:3d} {bar}")

# Statistical test: Are V-formations more likely to be precursors?
v_before = sum(1 for o in v_offsets if o < 0)
v_after = sum(1 for o in v_offsets if o > 0)
classic_before = sum(1 for o in classic_offsets if o < 0)
classic_after = sum(1 for o in classic_offsets if o > 0)

print(f"\nPrecursor ratio (before/after):")
print(f"  V-Formation: {v_before}/{v_after} = {v_before/v_after:.2f}" if v_after > 0 else f"  V-Formation: {v_before}/{v_after}")
print(f"  Classic UFO: {classic_before}/{classic_after} = {classic_before/classic_after:.2f}" if classic_after > 0 else f"  Classic UFO: {classic_before}/{classic_after}")

# Chi-square test
contingency = [[v_before, v_after], [classic_before, classic_after]]
if all(x > 0 for row in contingency for x in row):
    chi2, p_value = stats.chi2_contingency(contingency)[:2]
    print(f"\nChi-square test (V vs Classic precursor ratio):")
    print(f"  Chi-square: {chi2:.3f}")
    print(f"  P-value: {p_value:.4f}")

# ============================================================
# HOURLY PATTERN ANALYSIS
# ============================================================
print("\n" + "=" * 60)
print("TIME OF DAY ANALYSIS")
print("=" * 60)

# Birds are most active at dawn/dusk (crepuscular) or diurnal
# If V-formations are birds, they should cluster during daylight/dusk

sf_ufo['hour'] = sf_ufo['datetime'].dt.hour

v_reports = sf_ufo[sf_ufo['is_v_formation']]
classic_reports = sf_ufo[sf_ufo['is_classic_ufo']]

print("\nHourly distribution:")
print("\n  Hour  V-Form  Classic  (V-Formation likely bird times in brackets)")
print("  " + "-" * 50)

bird_hours = list(range(6, 10)) + list(range(17, 21))  # Dawn and dusk

for hour in range(24):
    v_count = len(v_reports[v_reports['hour'] == hour])
    classic_count = len(classic_reports[classic_reports['hour'] == hour])
    v_bar = '*' * (v_count // 2)
    marker = '[BIRD]' if hour in bird_hours else '      '
    print(f"  {hour:02d}:00  {v_count:4d}   {classic_count:4d}   {marker} {v_bar}")

# Calculate percentage during bird-active hours
v_bird_hours = len(v_reports[v_reports['hour'].isin(bird_hours)])
v_total = len(v_reports)
classic_bird_hours = len(classic_reports[classic_reports['hour'].isin(bird_hours)])
classic_total = len(classic_reports)

print(f"\nPercentage during bird-active hours (6-10am, 5-9pm):")
print(f"  V-Formation: {100*v_bird_hours/v_total:.1f}%")
print(f"  Classic UFO: {100*classic_bird_hours/classic_total:.1f}%")

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 60)
print("SUMMARY: V-FORMATION / BIRD HYPOTHESIS")
print("=" * 60)

print("""
FINDINGS:

1. SEISMIC CORRELATION: V-formation reports show [see ratios above]
   seismic correlation compared to classic UFO shapes.

2. PRECURSOR SIGNAL: V-formations [more/less/equally] likely to occur
   BEFORE earthquakes compared to classic shapes.

3. TIME OF DAY: V-formations [do/do not] cluster during bird-active
   hours (dawn/dusk) more than classic UFO shapes.

INTERPRETATION:

If V-formations were birds disturbed by piezoelectric stress:
- They should show STRONGER seismic correlation (stress triggers behavior)
- They should show STRONGER precursor signal (stress precedes quake)
- They should occur during BIRD-ACTIVE hours

Check the numbers above to see if the hypothesis holds.
""")

# Save detailed results
results_df = pd.DataFrame(results)
results_df.to_csv("/Users/bobrothers/specter-phase2/bird_investigation/shape_seismic_correlation.csv", index=False)
print("\nSaved results to shape_seismic_correlation.csv")
