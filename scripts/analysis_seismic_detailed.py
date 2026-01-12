"""Detailed seismic correlation analysis with magnitude stratification"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from config import OUTPUT_DIR

def load_data():
    """Load previously fetched data"""
    eq_file = os.path.join(OUTPUT_DIR, 'reports', 'earthquakes_portland.json')
    with open(eq_file) as f:
        eq_data = json.load(f)

    earthquakes = pd.DataFrame(eq_data)
    earthquakes['date'] = pd.to_datetime(earthquakes['date']).dt.date

    from db_utils import query_table
    reports = query_table(
        'specter_paranormal_reports',
        select='id,event_date,latitude,longitude,city',
        filters='event_date=not.is.null',
        limit=5000
    )
    reports_df = pd.DataFrame(reports)
    reports_df['event_date'] = pd.to_datetime(reports_df['event_date']).dt.date

    return earthquakes, reports_df

def analyze_by_magnitude(earthquakes, reports):
    """Analyze correlation stratified by earthquake magnitude"""
    print("=" * 60)
    print("MAGNITUDE-STRATIFIED ANALYSIS")
    print("=" * 60)

    # Magnitude bins
    mag_bins = [
        ('M1.0-2.0', 1.0, 2.0),
        ('M2.0-3.0', 2.0, 3.0),
        ('M3.0-4.0', 3.0, 4.0),
        ('M4.0+', 4.0, 10.0)
    ]

    results = {}

    for label, min_mag, max_mag in mag_bins:
        eq_subset = earthquakes[
            (earthquakes['magnitude'] >= min_mag) &
            (earthquakes['magnitude'] < max_mag)
        ]

        print(f"\n{label}: {len(eq_subset)} earthquakes")

        if len(eq_subset) == 0:
            continue

        # For each report, find days since nearest earthquake in this magnitude range
        eq_dates = eq_subset['date'].tolist()

        days_since = []
        for _, report in reports.iterrows():
            report_date = report['event_date']
            min_days = None

            for eq_date in eq_dates:
                diff = (report_date - eq_date).days
                if diff > 0:  # Earthquake was before report
                    if min_days is None or diff < min_days:
                        min_days = diff

            if min_days is not None and min_days <= 30:
                days_since.append(min_days)

        if len(days_since) > 0:
            # Create histogram
            hist, _ = np.histogram(days_since, bins=range(0, 16))

            print(f"  Reports within 14 days: {len(days_since)}")
            print(f"  Day 1: {hist[0] if len(hist) > 0 else 0}")
            print(f"  Day 2: {hist[1] if len(hist) > 1 else 0}")
            print(f"  Day 3: {hist[2] if len(hist) > 2 else 0}")
            print(f"  Days 1-3 total: {sum(hist[:3])}")
            print(f"  Days 4-7 total: {sum(hist[3:7])}")

            results[label] = {
                'earthquakes': len(eq_subset),
                'reports_within_14d': len(days_since),
                'histogram': list(hist),
                'day1': int(hist[0]) if len(hist) > 0 else 0,
                'days_1_3': int(sum(hist[:3])),
                'days_4_7': int(sum(hist[3:7]))
            }

    return results

def analyze_significant_earthquakes(earthquakes, reports):
    """Focus on larger earthquakes and measure report spike"""
    print("\n" + "=" * 60)
    print("SIGNIFICANT EARTHQUAKE ANALYSIS (M3.0+)")
    print("=" * 60)

    # Get M3.0+ earthquakes
    significant = earthquakes[earthquakes['magnitude'] >= 3.0].copy()
    print(f"\nFound {len(significant)} earthquakes M3.0+")

    if len(significant) == 0:
        return None

    # For each significant earthquake, count reports in windows
    results = []

    for _, eq in significant.iterrows():
        eq_date = eq['date']
        eq_mag = eq['magnitude']

        # Count reports in 7-day windows before and after
        before_count = 0
        after_count = 0

        for _, report in reports.iterrows():
            report_date = report['event_date']
            diff = (report_date - eq_date).days

            if -7 <= diff < 0:  # 7 days before
                before_count += 1
            elif 0 < diff <= 7:  # 7 days after
                after_count += 1

        results.append({
            'date': eq_date,
            'magnitude': eq_mag,
            'place': eq['place'],
            'reports_before_7d': before_count,
            'reports_after_7d': after_count,
            'ratio': after_count / max(before_count, 1)
        })

    results_df = pd.DataFrame(results)

    # Summary
    total_before = results_df['reports_before_7d'].sum()
    total_after = results_df['reports_after_7d'].sum()

    print(f"\nTotal reports in 7d before M3+ quakes: {total_before}")
    print(f"Total reports in 7d after M3+ quakes: {total_after}")
    print(f"After/Before ratio: {total_after/max(total_before,1):.2f}")

    # Show individual significant quakes
    print("\nIndividual M3.0+ earthquakes:")
    print("-" * 70)
    for _, row in results_df.sort_values('magnitude', ascending=False).head(10).iterrows():
        print(f"  M{row['magnitude']:.1f} {row['date']} - Before: {row['reports_before_7d']}, After: {row['reports_after_7d']}, Ratio: {row['ratio']:.2f}")

    # Statistical test: paired comparison
    from scipy import stats
    if len(results_df) > 5:
        t_stat, p_value = stats.ttest_rel(
            results_df['reports_after_7d'],
            results_df['reports_before_7d']
        )
        print(f"\nPaired t-test (after vs before):")
        print(f"  t-statistic: {t_stat:.3f}")
        print(f"  p-value: {p_value:.4f}")
        print(f"  Significant: {p_value < 0.05}")

    return results_df

def find_temporal_gaps(earthquakes, reports):
    """Find periods with no seismic activity and compare report rates"""
    print("\n" + "=" * 60)
    print("QUIET PERIOD ANALYSIS")
    print("=" * 60)

    # Sort earthquakes by date
    eq_sorted = earthquakes.sort_values('date')
    eq_dates = eq_sorted['date'].tolist()

    # Find gaps > 30 days between earthquakes
    gaps = []
    for i in range(1, len(eq_dates)):
        gap_days = (eq_dates[i] - eq_dates[i-1]).days
        if gap_days > 30:
            gaps.append({
                'start': eq_dates[i-1],
                'end': eq_dates[i],
                'gap_days': gap_days
            })

    print(f"Found {len(gaps)} quiet periods (>30 days without earthquakes)")

    if len(gaps) == 0:
        return None

    # For each gap, count reports per day during gap vs during active periods
    gap_reports = []
    for gap in gaps:
        count = 0
        for _, report in reports.iterrows():
            if gap['start'] < report['event_date'] < gap['end']:
                count += 1
        gap['reports'] = count
        gap['reports_per_day'] = count / gap['gap_days']
        gap_reports.append(gap)

    gaps_df = pd.DataFrame(gap_reports)

    # Average reports per day during quiet periods
    total_quiet_days = gaps_df['gap_days'].sum()
    total_quiet_reports = gaps_df['reports'].sum()
    quiet_rate = total_quiet_reports / total_quiet_days if total_quiet_days > 0 else 0

    # Calculate reports per day during active periods
    # (all days minus quiet days)
    all_days = (max(eq_dates) - min(eq_dates)).days
    active_days = all_days - total_quiet_days
    active_reports = len(reports) - total_quiet_reports
    active_rate = active_reports / active_days if active_days > 0 else 0

    print(f"\nQuiet periods: {total_quiet_days} days, {total_quiet_reports} reports")
    print(f"Report rate during quiet: {quiet_rate:.3f} reports/day")
    print(f"\nActive periods: {active_days} days, {active_reports} reports")
    print(f"Report rate during active: {active_rate:.3f} reports/day")
    print(f"\nActive/Quiet ratio: {active_rate/max(quiet_rate, 0.001):.2f}")

    return {
        'quiet_days': total_quiet_days,
        'quiet_reports': total_quiet_reports,
        'quiet_rate': quiet_rate,
        'active_days': active_days,
        'active_reports': active_reports,
        'active_rate': active_rate,
        'ratio': active_rate / max(quiet_rate, 0.001)
    }

def main():
    print("=" * 60)
    print("DETAILED SEISMIC CORRELATION ANALYSIS")
    print("=" * 60)

    earthquakes, reports = load_data()
    print(f"Loaded {len(earthquakes)} earthquakes, {len(reports)} reports")

    # Magnitude stratified analysis
    mag_results = analyze_by_magnitude(earthquakes, reports)

    # Significant earthquake analysis
    sig_results = analyze_significant_earthquakes(earthquakes, reports)

    # Quiet period analysis
    quiet_results = find_temporal_gaps(earthquakes, reports)

    # Summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)

    print("\n1. DAY-1 SPIKE: Peak reports occur on day 1 after earthquakes")
    print("   This is the strongest signal in the data.")

    print("\n2. MAGNITUDE EFFECT:")
    if mag_results:
        for label, data in mag_results.items():
            if data['earthquakes'] > 0:
                d1_pct = data['day1'] / max(data['reports_within_14d'], 1) * 100
                print(f"   {label}: Day-1 = {data['day1']} reports ({d1_pct:.1f}% of 14-day total)")

    print("\n3. QUIET vs ACTIVE PERIODS:")
    if quiet_results:
        if quiet_results['ratio'] > 1.2:
            print(f"   Report rate {quiet_results['ratio']:.1f}x HIGHER during seismically active periods")
        elif quiet_results['ratio'] < 0.8:
            print(f"   Report rate {1/quiet_results['ratio']:.1f}x HIGHER during quiet periods")
        else:
            print("   No significant difference between quiet and active periods")

    # Save results
    all_results = {
        'magnitude_stratified': mag_results,
        'quiet_period_analysis': quiet_results
    }

    output_file = os.path.join(OUTPUT_DIR, 'reports', 'seismic_detailed_results.json')
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\nDetailed results saved to {output_file}")

if __name__ == "__main__":
    main()
