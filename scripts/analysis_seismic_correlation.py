"""SPECTER Seismic-Paranormal Temporal Correlation Analysis"""
import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime, timedelta
import requests
import json
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from config import OUTPUT_DIR
from db_utils import query_table

# Portland metro bounding box
PORTLAND_BBOX = {
    'min_lat': 45.4,
    'max_lat': 45.6,
    'min_lon': -122.8,
    'max_lon': -122.5
}

# Expanded for more earthquake coverage
OREGON_BBOX = {
    'min_lat': 45.2,
    'max_lat': 45.8,
    'min_lon': -123.0,
    'max_lon': -122.3
}

USGS_API = "https://earthquake.usgs.gov/fdsnws/event/1/query"

def fetch_usgs_earthquakes():
    """Fetch all earthquakes from USGS for Portland region"""
    print("Fetching USGS earthquake data...")

    params = {
        'format': 'geojson',
        'minlatitude': OREGON_BBOX['min_lat'],
        'maxlatitude': OREGON_BBOX['max_lat'],
        'minlongitude': OREGON_BBOX['min_lon'],
        'maxlongitude': OREGON_BBOX['max_lon'],
        'starttime': '1950-01-01',
        'endtime': '2025-01-01',
        'minmagnitude': 1.0,  # Include micro-earthquakes
        'orderby': 'time'
    }

    response = requests.get(USGS_API, params=params, timeout=60)
    if response.status_code != 200:
        print(f"USGS API error: {response.status_code}")
        return None

    data = response.json()
    earthquakes = []

    for feature in data.get('features', []):
        props = feature['properties']
        coords = feature['geometry']['coordinates']

        # Convert timestamp to date
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

    return pd.DataFrame(earthquakes)

def fetch_paranormal_reports():
    """Fetch paranormal reports with dates"""
    reports = query_table(
        'specter_paranormal_reports',
        select='id,event_date,latitude,longitude,city',
        filters='event_date=not.is.null',
        limit=5000
    )

    df = pd.DataFrame(reports)
    df['event_date'] = pd.to_datetime(df['event_date']).dt.date
    return df

def calculate_days_to_nearest_earthquake(report_date, earthquake_dates, window_days=30):
    """Calculate days between report and nearest earthquake"""
    if len(earthquake_dates) == 0:
        return None, None, None

    # Convert to datetime for comparison
    report_dt = datetime.combine(report_date, datetime.min.time())

    days_before = None  # Nearest earthquake BEFORE report (negative = quake was X days ago)
    days_after = None   # Nearest earthquake AFTER report (positive = quake will be in X days)

    min_before = float('inf')
    min_after = float('inf')

    for eq_date in earthquake_dates:
        eq_dt = datetime.combine(eq_date, datetime.min.time())
        diff = (report_dt - eq_dt).days  # Positive = report is after earthquake

        if diff > 0 and diff < min_before:  # Earthquake was before report
            min_before = diff
            days_before = diff
        elif diff < 0 and abs(diff) < min_after:  # Earthquake was after report
            min_after = abs(diff)
            days_after = abs(diff)
        elif diff == 0:
            days_before = 0
            days_after = 0

    # Nearest overall
    nearest = min(min_before, min_after) if min(min_before, min_after) != float('inf') else None
    direction = 'after_eq' if min_before <= min_after else 'before_eq'

    return days_before, days_after, nearest

def analyze_temporal_correlation(reports_df, earthquakes_df, window_days=7):
    """Analyze if reports cluster after earthquakes"""
    print(f"\nAnalyzing temporal correlation (window={window_days} days)...")

    eq_dates = earthquakes_df['date'].tolist()

    results = []
    for _, report in reports_df.iterrows():
        report_date = report['event_date']
        days_before, days_after, nearest = calculate_days_to_nearest_earthquake(
            report_date, eq_dates, window_days
        )

        results.append({
            'report_date': report_date,
            'days_since_last_eq': days_before,  # Days since most recent earthquake
            'days_until_next_eq': days_after,   # Days until next earthquake
            'nearest_eq_days': nearest,
            'within_7d_after_eq': days_before is not None and days_before <= 7,
            'within_7d_before_eq': days_after is not None and days_after <= 7
        })

    return pd.DataFrame(results)

def run_permutation_test(correlation_df, earthquakes_df, n_permutations=1000):
    """Permutation test: are reports more likely after earthquakes than by chance?"""
    print(f"\nRunning permutation test (n={n_permutations})...")

    # Observed: count of reports within 7 days AFTER an earthquake
    observed_after = correlation_df['within_7d_after_eq'].sum()
    observed_before = correlation_df['within_7d_before_eq'].sum()

    print(f"Observed reports within 7d AFTER earthquake: {observed_after}")
    print(f"Observed reports within 7d BEFORE earthquake: {observed_before}")

    # Generate null distribution by shuffling report dates
    eq_dates = earthquakes_df['date'].tolist()
    report_dates = correlation_df['report_date'].tolist()

    # Date range for shuffling
    min_date = min(report_dates)
    max_date = max(report_dates)
    date_range = (max_date - min_date).days

    null_after_counts = []
    null_before_counts = []

    for i in range(n_permutations):
        # Shuffle report dates within the same range
        shuffled_dates = [min_date + timedelta(days=np.random.randint(0, date_range))
                         for _ in range(len(report_dates))]

        after_count = 0
        before_count = 0

        for report_date in shuffled_dates:
            days_before, days_after, _ = calculate_days_to_nearest_earthquake(
                report_date, eq_dates, 7
            )
            if days_before is not None and days_before <= 7:
                after_count += 1
            if days_after is not None and days_after <= 7:
                before_count += 1

        null_after_counts.append(after_count)
        null_before_counts.append(before_count)

        if (i + 1) % 100 == 0:
            print(f"  Permutation {i + 1}/{n_permutations}")

    # Calculate p-values
    p_value_after = sum(n >= observed_after for n in null_after_counts) / n_permutations
    p_value_ratio = sum(
        (null_after_counts[i] - null_before_counts[i]) >= (observed_after - observed_before)
        for i in range(n_permutations)
    ) / n_permutations

    return {
        'observed_after': observed_after,
        'observed_before': observed_before,
        'observed_ratio': observed_after / max(observed_before, 1),
        'null_mean_after': np.mean(null_after_counts),
        'null_std_after': np.std(null_after_counts),
        'null_mean_before': np.mean(null_before_counts),
        'p_value_after': p_value_after,
        'p_value_ratio': p_value_ratio,
        'significant': p_value_ratio < 0.05
    }

def analyze_decay_function(correlation_df):
    """Analyze if there's a decay pattern in days since earthquake"""
    print("\nAnalyzing decay function...")

    # Get reports that occurred after earthquakes
    after_eq = correlation_df[correlation_df['days_since_last_eq'].notna()]
    days = after_eq['days_since_last_eq'].values

    # Bin by days
    bins = list(range(0, 31, 1))  # 0-30 days, 1-day bins
    hist, bin_edges = np.histogram(days, bins=bins)

    print("\nReport frequency by days since last earthquake:")
    print("Days | Count | Bar")
    print("-" * 40)

    max_count = max(hist) if len(hist) > 0 else 1
    for i, count in enumerate(hist[:14]):  # First 14 days
        bar = '#' * int(count / max_count * 20)
        print(f"{i:2d}-{i+1:2d} | {count:4d} | {bar}")

    # Test for decay: is day 1-3 higher than day 5-7?
    early = sum(hist[1:4]) if len(hist) > 3 else 0  # Days 1-3
    late = sum(hist[5:8]) if len(hist) > 7 else 0   # Days 5-7

    return {
        'histogram': list(hist),
        'bin_edges': list(bin_edges),
        'days_1_3_count': early,
        'days_5_7_count': late,
        'decay_ratio': early / max(late, 1),
        'decay_present': early > late * 1.5
    }

def main():
    print("=" * 60)
    print("SPECTER Seismic-Paranormal Temporal Correlation")
    print("=" * 60)

    # Fetch earthquake data
    earthquakes_df = fetch_usgs_earthquakes()
    if earthquakes_df is None or len(earthquakes_df) == 0:
        print("No earthquake data available")
        return None

    print(f"Retrieved {len(earthquakes_df)} earthquakes")
    print(f"Date range: {earthquakes_df['date'].min()} to {earthquakes_df['date'].max()}")
    print(f"Magnitude range: {earthquakes_df['magnitude'].min():.1f} to {earthquakes_df['magnitude'].max():.1f}")

    # Save earthquake data
    eq_file = os.path.join(OUTPUT_DIR, 'reports', 'earthquakes_portland.json')
    earthquakes_df.to_json(eq_file, orient='records', date_format='iso')
    print(f"Saved earthquake data to {eq_file}")

    # Fetch paranormal reports
    print("\nFetching paranormal reports...")
    reports_df = fetch_paranormal_reports()
    print(f"Retrieved {len(reports_df)} reports with dates")
    print(f"Date range: {reports_df['event_date'].min()} to {reports_df['event_date'].max()}")

    # Calculate temporal correlations
    correlation_df = analyze_temporal_correlation(reports_df, earthquakes_df, window_days=7)

    # Summary stats
    print("\n" + "=" * 60)
    print("TEMPORAL CORRELATION RESULTS")
    print("=" * 60)

    total = len(correlation_df)
    after_7d = correlation_df['within_7d_after_eq'].sum()
    before_7d = correlation_df['within_7d_before_eq'].sum()

    print(f"\nTotal reports analyzed: {total}")
    print(f"Reports within 7 days AFTER an earthquake: {after_7d} ({after_7d/total*100:.1f}%)")
    print(f"Reports within 7 days BEFORE an earthquake: {before_7d} ({before_7d/total*100:.1f}%)")
    print(f"After/Before ratio: {after_7d/max(before_7d,1):.2f}")

    # Permutation test
    perm_results = run_permutation_test(correlation_df, earthquakes_df, n_permutations=500)

    print("\n--- Permutation Test Results ---")
    print(f"Null mean (after): {perm_results['null_mean_after']:.1f}")
    print(f"Observed (after): {perm_results['observed_after']}")
    print(f"P-value (after > null): {perm_results['p_value_after']:.4f}")
    print(f"P-value (after-before ratio): {perm_results['p_value_ratio']:.4f}")
    print(f"Significant at p<0.05: {perm_results['significant']}")

    # Decay analysis
    decay_results = analyze_decay_function(correlation_df)

    print("\n--- Decay Analysis ---")
    print(f"Reports days 1-3 after earthquake: {decay_results['days_1_3_count']}")
    print(f"Reports days 5-7 after earthquake: {decay_results['days_5_7_count']}")
    print(f"Decay ratio (early/late): {decay_results['decay_ratio']:.2f}")
    print(f"Decay pattern present: {decay_results['decay_present']}")

    # Final interpretation
    print("\n" + "=" * 60)
    print("INTERPRETATION")
    print("=" * 60)

    if perm_results['significant']:
        if perm_results['observed_after'] > perm_results['observed_before']:
            print("\n*** SIGNIFICANT FINDING ***")
            print("Reports are MORE LIKELY to occur in the 7 days FOLLOWING")
            print("a seismic event than in the 7 days BEFORE.")
            print("\nThis supports the hypothesis that seismic activity may")
            print("trigger or correlate with paranormal experiences.")

            if decay_results['decay_present']:
                print(f"\nDecay pattern detected: Peak reports occur 1-3 days after")
                print(f"earthquakes, declining by days 5-7.")
        else:
            print("\nReports are more likely BEFORE earthquakes (unusual pattern)")
    else:
        print("\nNo significant temporal asymmetry detected.")
        print("Report timing does not appear to correlate with seismic events.")

    # Save all results
    results = {
        'earthquakes_analyzed': len(earthquakes_df),
        'reports_analyzed': len(correlation_df),
        'within_7d_after': int(after_7d),
        'within_7d_before': int(before_7d),
        'permutation_test': perm_results,
        'decay_analysis': decay_results,
        'conclusion': 'significant_after' if perm_results['significant'] and perm_results['observed_after'] > perm_results['observed_before'] else 'not_significant'
    }

    output_file = os.path.join(OUTPUT_DIR, 'reports', 'seismic_correlation_results.json')
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nResults saved to {output_file}")

    # Generate histogram visualization data
    generate_histogram_report(correlation_df, decay_results)

    return results

def generate_histogram_report(correlation_df, decay_results):
    """Generate a text-based histogram report"""
    print("\n" + "=" * 60)
    print("HISTOGRAM: Report Frequency by Days Since Earthquake")
    print("=" * 60)

    hist = decay_results['histogram']
    max_val = max(hist) if hist else 1

    print("\n Days | Count | Distribution")
    print("-" * 50)

    for i, count in enumerate(hist[:21]):  # First 21 days
        bar_len = int(count / max_val * 30) if max_val > 0 else 0
        bar = '█' * bar_len
        marker = ' ◄── PEAK' if count == max_val and count > 0 else ''
        print(f" {i:2d}   | {count:4d}  | {bar}{marker}")

    print("-" * 50)
    print(f"\nPeak day: {hist.index(max(hist))} days after earthquake")
    print(f"Peak count: {max(hist)} reports")

if __name__ == "__main__":
    main()
