"""SPECTER Temporal Pattern Analysis"""
import numpy as np
import pandas as pd
from scipy import stats
import json
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

import ephem
from datetime import datetime, timedelta

from config import OUTPUT_DIR
from db_utils import query_table

def fetch_reports_with_dates():
    """Fetch reports with temporal data"""
    reports = query_table(
        'specter_paranormal_reports',
        select='id,event_date,event_time,phenomenon_type,city',
        filters='event_date=not.is.null',
        limit=5000
    )
    return pd.DataFrame(reports)

def get_lunar_phase(date):
    """Get lunar phase for a date (0=new, 0.5=full)"""
    if pd.isna(date):
        return None
    try:
        if isinstance(date, str):
            date = datetime.strptime(date[:10], '%Y-%m-%d')
        moon = ephem.Moon(date)
        return moon.phase / 100  # 0-1 scale
    except:
        return None

def categorize_lunar_phase(phase):
    """Categorize lunar phase"""
    if phase is None:
        return 'unknown'
    if phase < 0.125:
        return 'new'
    elif phase < 0.375:
        return 'waxing'
    elif phase < 0.625:
        return 'full'
    elif phase < 0.875:
        return 'waning'
    else:
        return 'new'

def analyze_time_of_day(df):
    """Analyze time-of-day distribution"""
    print("\n--- Time of Day Analysis ---")

    # Parse times
    times = pd.to_datetime(df['event_time'], format='%H:%M:%S', errors='coerce')
    valid_times = times.dropna()

    if len(valid_times) < 10:
        print("Insufficient time data")
        return None

    hours = valid_times.dt.hour

    # Distribution
    hour_counts = hours.value_counts().sort_index()
    print(f"Reports with valid times: {len(valid_times)}")

    # Chi-square test against uniform distribution
    observed = np.array([hour_counts.get(h, 0) for h in range(24)])
    expected = np.full(24, len(valid_times) / 24)

    # Only include hours with expected > 5 for valid chi-square
    chi2, p_value = stats.chisquare(observed + 1, expected + 1)  # Add 1 to avoid zeros

    print(f"Chi-square: {chi2:.2f}, p-value: {p_value:.4f}")

    # Peak hours
    peak_hours = hour_counts.nlargest(5)
    print(f"Peak hours: {dict(peak_hours)}")

    # Night vs day
    night_hours = [0,1,2,3,4,5,21,22,23]
    day_hours = [6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]

    night_count = sum(hour_counts.get(h, 0) for h in night_hours)
    day_count = sum(hour_counts.get(h, 0) for h in day_hours)

    night_ratio = night_count / len(valid_times)
    expected_night_ratio = len(night_hours) / 24

    print(f"Night reports: {night_count} ({night_ratio:.1%})")
    print(f"Expected if uniform: {expected_night_ratio:.1%}")

    return {
        'distribution': {str(k): int(v) for k, v in hour_counts.items()},
        'chi2': chi2,
        'p_value': p_value,
        'uniform_rejected': p_value < 0.05,
        'night_ratio': night_ratio,
        'peak_hours': {str(k): int(v) for k, v in peak_hours.items()}
    }

def analyze_day_of_week(df):
    """Analyze day-of-week distribution"""
    print("\n--- Day of Week Analysis ---")

    dates = pd.to_datetime(df['event_date'], errors='coerce')
    valid_dates = dates.dropna()

    if len(valid_dates) < 10:
        print("Insufficient date data")
        return None

    dow = valid_dates.dt.dayofweek
    dow_counts = dow.value_counts().sort_index()

    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    print(f"Reports by day of week:")
    for i, name in enumerate(day_names):
        count = dow_counts.get(i, 0)
        print(f"  {name}: {count}")

    # Chi-square test
    observed = np.array([dow_counts.get(i, 0) for i in range(7)])
    expected = np.full(7, len(valid_dates) / 7)
    chi2, p_value = stats.chisquare(observed + 1, expected + 1)

    print(f"Chi-square: {chi2:.2f}, p-value: {p_value:.4f}")

    # Weekend vs weekday
    weekend_count = dow_counts.get(5, 0) + dow_counts.get(6, 0)
    weekday_count = sum(dow_counts.get(i, 0) for i in range(5))

    weekend_ratio = weekend_count / len(valid_dates)
    expected_weekend_ratio = 2/7

    print(f"Weekend reports: {weekend_count} ({weekend_ratio:.1%})")
    print(f"Expected if uniform: {expected_weekend_ratio:.1%}")

    return {
        'distribution': {day_names[k]: int(v) for k, v in dow_counts.items()},
        'chi2': chi2,
        'p_value': p_value,
        'uniform_rejected': p_value < 0.05,
        'weekend_ratio': weekend_ratio
    }

def analyze_lunar_phase(df):
    """Analyze lunar phase correlation"""
    print("\n--- Lunar Phase Analysis ---")

    dates = pd.to_datetime(df['event_date'], errors='coerce')
    valid_dates = dates.dropna()

    if len(valid_dates) < 20:
        print("Insufficient data for lunar analysis")
        return None

    # Calculate lunar phases
    phases = []
    categories = []
    for date in valid_dates:
        phase = get_lunar_phase(date)
        phases.append(phase)
        categories.append(categorize_lunar_phase(phase))

    phase_series = pd.Series(categories)
    phase_counts = phase_series.value_counts()

    print(f"Reports by lunar phase:")
    for phase, count in phase_counts.items():
        print(f"  {phase}: {count}")

    # Chi-square test (4 categories should be roughly equal)
    cat_order = ['new', 'waxing', 'full', 'waning']
    observed = np.array([phase_counts.get(c, 0) for c in cat_order])
    expected = np.full(4, len(valid_dates) / 4)

    chi2, p_value = stats.chisquare(observed + 1, expected + 1)

    print(f"Chi-square: {chi2:.2f}, p-value: {p_value:.4f}")

    # Full moon enrichment
    full_ratio = phase_counts.get('full', 0) / len(valid_dates)
    expected_ratio = 0.25

    print(f"Full moon reports: {phase_counts.get('full', 0)} ({full_ratio:.1%})")
    print(f"Expected if uniform: {expected_ratio:.1%}")

    return {
        'distribution': {k: int(v) for k, v in phase_counts.items()},
        'chi2': chi2,
        'p_value': p_value,
        'uniform_rejected': p_value < 0.05,
        'full_moon_ratio': full_ratio,
        'full_moon_enriched': full_ratio > 0.30
    }

def analyze_yearly_trends(df):
    """Analyze yearly trends"""
    print("\n--- Yearly Trends ---")

    dates = pd.to_datetime(df['event_date'], errors='coerce')
    valid_dates = dates.dropna()

    if len(valid_dates) < 20:
        print("Insufficient data")
        return None

    years = valid_dates.dt.year
    year_counts = years.value_counts().sort_index()

    print(f"Reports by year (top 10):")
    for year, count in year_counts.nlargest(10).items():
        print(f"  {year}: {count}")

    # Trend analysis
    years_arr = np.array(year_counts.index)
    counts_arr = np.array(year_counts.values)

    if len(years_arr) > 2:
        slope, intercept, r_value, p_value, std_err = stats.linregress(years_arr, counts_arr)
        print(f"\nTrend: slope={slope:.2f} reports/year, R²={r_value**2:.3f}, p={p_value:.4f}")
    else:
        slope, r_value, p_value = 0, 0, 1

    return {
        'distribution': {int(k): int(v) for k, v in year_counts.items()},
        'trend_slope': slope,
        'trend_r_squared': r_value**2,
        'trend_p_value': p_value,
        'increasing': slope > 0
    }

def analyze_monthly_pattern(df):
    """Analyze monthly seasonality"""
    print("\n--- Monthly Seasonality ---")

    dates = pd.to_datetime(df['event_date'], errors='coerce')
    valid_dates = dates.dropna()

    if len(valid_dates) < 20:
        print("Insufficient data")
        return None

    months = valid_dates.dt.month
    month_counts = months.value_counts().sort_index()

    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    print(f"Reports by month:")
    for m in range(1, 13):
        print(f"  {month_names[m-1]}: {month_counts.get(m, 0)}")

    # Chi-square test
    observed = np.array([month_counts.get(m, 0) for m in range(1, 13)])
    expected = np.full(12, len(valid_dates) / 12)
    chi2, p_value = stats.chisquare(observed + 1, expected + 1)

    print(f"Chi-square: {chi2:.2f}, p-value: {p_value:.4f}")

    # Peak months
    peak_months = month_counts.nlargest(3)
    print(f"Peak months: {[(month_names[m-1], c) for m, c in peak_months.items()]}")

    return {
        'distribution': {month_names[k-1]: int(v) for k, v in month_counts.items()},
        'chi2': chi2,
        'p_value': p_value,
        'seasonal_pattern': p_value < 0.05,
        'peak_months': [month_names[m-1] for m in peak_months.index]
    }

def main():
    print("=" * 60)
    print("SPECTER Temporal Pattern Analysis")
    print("=" * 60)

    # Fetch data
    print("\nFetching temporal data...")
    df = fetch_reports_with_dates()
    print(f"Retrieved {len(df)} reports with dates")

    if len(df) < 10:
        print("Insufficient data for temporal analysis")
        return None

    results = {}

    # Run all temporal analyses
    results['time_of_day'] = analyze_time_of_day(df)
    results['day_of_week'] = analyze_day_of_week(df)
    results['lunar_phase'] = analyze_lunar_phase(df)
    results['yearly_trends'] = analyze_yearly_trends(df)
    results['monthly_pattern'] = analyze_monthly_pattern(df)

    # Summary
    print("\n" + "=" * 60)
    print("TEMPORAL ANALYSIS SUMMARY")
    print("=" * 60)

    significant_patterns = []
    for analysis_name, result in results.items():
        if result and result.get('p_value', 1) < 0.05:
            significant_patterns.append(analysis_name)

    if significant_patterns:
        print("\nSIGNIFICANT TEMPORAL PATTERNS FOUND:")
        for pattern in significant_patterns:
            print(f"  - {pattern}")
    else:
        print("\nNo significant temporal patterns found at p<0.05")
        print("Reports appear uniformly distributed over time dimensions tested.")

    # Key findings
    print("\nKEY FINDINGS:")

    if results['time_of_day']:
        print(f"  - Night ratio: {results['time_of_day']['night_ratio']:.1%} (expected: 37.5%)")

    if results['lunar_phase']:
        print(f"  - Full moon ratio: {results['lunar_phase']['full_moon_ratio']:.1%} (expected: 25%)")

    if results['monthly_pattern']:
        peaks = results['monthly_pattern'].get('peak_months', [])
        if peaks:
            print(f"  - Peak months: {', '.join(peaks)}")

    # Save results
    output_file = os.path.join(OUTPUT_DIR, 'reports', 'temporal_results.json')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nResults saved to {output_file}")

    return results

if __name__ == "__main__":
    main()
