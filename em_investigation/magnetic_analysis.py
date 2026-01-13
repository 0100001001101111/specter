#!/usr/bin/env python3
"""
SPECTER EM Investigation - Magnetic Anomaly Analysis
Extract magnetic values at hotspot coordinates and correlate with seismic ratios.
"""

import pandas as pd
import numpy as np
from scipy import stats
from scipy.spatial import cKDTree

print("=" * 60)
print("MAGNETIC ANOMALY / UFO HOTSPOT CORRELATION ANALYSIS")
print("=" * 60)

# Load hotspots
hotspots = pd.read_csv("/Users/bobrothers/specter-phase2/phase3/data/hotspots_complete.csv")
print(f"\nLoaded {len(hotspots)} hotspots")

# Load magnetic data
print("\nLoading magnetic anomaly grid (2.5M points)...")
mag_data = pd.read_csv(
    "/Users/bobrothers/specter-phase2/em_investigation/magnetic.xyz",
    sep=r'\s+',
    names=['lon', 'lat', 'mag_anomaly'],
    dtype={'lon': np.float32, 'lat': np.float32, 'mag_anomaly': np.float32}
)
print(f"  Loaded {len(mag_data):,} magnetic data points")
print(f"  Magnetic anomaly range: {mag_data['mag_anomaly'].min():.1f} to {mag_data['mag_anomaly'].max():.1f} nT")

# Build KD-tree for fast nearest-neighbor lookup
print("\nBuilding spatial index...")
mag_coords = mag_data[['lon', 'lat']].values
tree = cKDTree(mag_coords)

# Extract magnetic values at hotspot locations
print("Extracting magnetic values at hotspot coordinates...")

results = []
for idx, row in hotspots.iterrows():
    hotspot_coord = [row['lon'], row['lat']]

    # Find nearest magnetic data point
    dist, nearest_idx = tree.query(hotspot_coord)
    mag_value = mag_data.iloc[nearest_idx]['mag_anomaly']

    # Also get surrounding points for gradient calculation
    # Query 5 nearest points
    dists, indices = tree.query(hotspot_coord, k=5)
    nearby_mags = mag_data.iloc[indices]['mag_anomaly'].values

    # Calculate local gradient (std of nearby points)
    mag_gradient = np.std(nearby_mags)

    results.append({
        'lat': row['lat'],
        'lon': row['lon'],
        'report_count': row['report_count'],
        'seismic_ratio': row['seismic_ratio'],
        'city_label': row['city_label'],
        'bedrock_type': row.get('bedrock_type', 'unknown'),
        'mag_anomaly': mag_value,
        'mag_gradient': mag_gradient,
        'nearest_dist_deg': dist
    })

results_df = pd.DataFrame(results)

# ============================================================
# TEST 1: MAGNETIC ANOMALY CORRELATION
# ============================================================
print("\n" + "=" * 60)
print("TEST 1: MAGNETIC ANOMALY vs SEISMIC CORRELATION")
print("=" * 60)

# Filter out inf seismic ratios for correlation
finite_df = results_df[results_df['seismic_ratio'] != np.inf].copy()

print(f"\nMagnetic anomaly statistics:")
print(f"  Mean: {results_df['mag_anomaly'].mean():.1f} nT")
print(f"  Std: {results_df['mag_anomaly'].std():.1f} nT")
print(f"  Min: {results_df['mag_anomaly'].min():.1f} nT")
print(f"  Max: {results_df['mag_anomaly'].max():.1f} nT")

# Pearson correlation
corr_pearson, p_pearson = stats.pearsonr(finite_df['mag_anomaly'], finite_df['seismic_ratio'])
print(f"\nPearson correlation (mag vs seismic ratio):")
print(f"  r = {corr_pearson:.3f}, p = {p_pearson:.4f}")

# Spearman correlation (rank-based, more robust)
corr_spearman, p_spearman = stats.spearmanr(finite_df['mag_anomaly'], finite_df['seismic_ratio'])
print(f"\nSpearman correlation:")
print(f"  rho = {corr_spearman:.3f}, p = {p_spearman:.4f}")

# Compare high vs low seismic correlation groups
high_corr = results_df[results_df['seismic_ratio'] > 2.0]
low_corr = results_df[results_df['seismic_ratio'] < 1.5]

print(f"\nMagnetic anomaly by seismic correlation:")
print(f"  High correlation (>2.0): mean={high_corr['mag_anomaly'].mean():.1f} nT, n={len(high_corr)}")
print(f"  Low correlation (<1.5): mean={low_corr['mag_anomaly'].mean():.1f} nT, n={len(low_corr)}")

# T-test
t_stat, p_ttest = stats.ttest_ind(high_corr['mag_anomaly'], low_corr['mag_anomaly'])
print(f"  T-test p-value: {p_ttest:.4f}")

# ============================================================
# TEST 2: MAGNETIC GRADIENT ANALYSIS
# ============================================================
print("\n" + "=" * 60)
print("TEST 2: MAGNETIC GRADIENT ANALYSIS")
print("=" * 60)

print(f"\nMagnetic gradient statistics:")
print(f"  Mean: {results_df['mag_gradient'].mean():.2f} nT")
print(f"  Std: {results_df['mag_gradient'].std():.2f} nT")

# Correlation with seismic ratio
corr_grad, p_grad = stats.spearmanr(finite_df['mag_gradient'], finite_df['seismic_ratio'])
print(f"\nGradient vs seismic ratio (Spearman):")
print(f"  rho = {corr_grad:.3f}, p = {p_grad:.4f}")

print(f"\nGradient by seismic correlation:")
print(f"  High correlation: mean={high_corr['mag_gradient'].mean():.2f} nT")
print(f"  Low correlation: mean={low_corr['mag_gradient'].mean():.2f} nT")

# ============================================================
# TEST 3: PORTLAND vs SF BAY COMPARISON
# ============================================================
print("\n" + "=" * 60)
print("TEST 3: PORTLAND vs SF BAY MAGNETIC SIGNATURES")
print("=" * 60)

portland = results_df[results_df['city_label'] == 'Portland']
sf = results_df[results_df['city_label'] == 'SF Bay Area']

print(f"\nPortland (n={len(portland)}):")
print(f"  Mean magnetic anomaly: {portland['mag_anomaly'].mean():.1f} nT")
print(f"  Std: {portland['mag_anomaly'].std():.1f} nT")
print(f"  Mean seismic ratio: {portland['seismic_ratio'].replace([np.inf], np.nan).mean():.2f}")

print(f"\nSF Bay Area (n={len(sf)}):")
print(f"  Mean magnetic anomaly: {sf['mag_anomaly'].mean():.1f} nT")
print(f"  Std: {sf['mag_anomaly'].std():.1f} nT")
print(f"  Mean seismic ratio: {sf['seismic_ratio'].replace([np.inf], np.nan).mean():.2f}")

# Is there a significant difference?
t_city, p_city = stats.ttest_ind(portland['mag_anomaly'], sf['mag_anomaly'])
print(f"\nT-test (Portland vs SF magnetic):")
print(f"  t = {t_city:.3f}, p = {p_city:.4f}")

# ============================================================
# TEST 4: WITHIN-BEDROCK ANALYSIS
# ============================================================
print("\n" + "=" * 60)
print("TEST 4: MAGNETIC ANOMALY WITHIN BEDROCK TYPES")
print("=" * 60)

for bedrock in results_df['bedrock_type'].unique():
    bedrock_df = results_df[results_df['bedrock_type'] == bedrock]
    if len(bedrock_df) < 3:
        continue

    finite_bedrock = bedrock_df[bedrock_df['seismic_ratio'] != np.inf]
    if len(finite_bedrock) < 3:
        continue

    corr, p = stats.spearmanr(finite_bedrock['mag_anomaly'], finite_bedrock['seismic_ratio'])
    print(f"\n{bedrock} (n={len(bedrock_df)}):")
    print(f"  Mean mag anomaly: {bedrock_df['mag_anomaly'].mean():.1f} nT")
    print(f"  Mag vs seismic ratio: rho={corr:.3f}, p={p:.4f}")

# ============================================================
# TOP 10 HOTSPOTS WITH MAGNETIC DATA
# ============================================================
print("\n" + "=" * 60)
print("TOP 10 HOTSPOTS WITH MAGNETIC DATA")
print("=" * 60)

top10 = results_df.nlargest(10, 'report_count')
print("\n" + "-" * 90)
print(f"{'Lat':>9} {'Lon':>11} {'Reports':>8} {'Ratio':>8} {'Mag (nT)':>10} {'City':<15}")
print("-" * 90)

for _, row in top10.iterrows():
    ratio_str = f"{row['seismic_ratio']:.2f}" if row['seismic_ratio'] != np.inf else 'inf'
    print(f"{row['lat']:>9.3f} {row['lon']:>11.3f} {row['report_count']:>8} "
          f"{ratio_str:>8} {row['mag_anomaly']:>10.1f} {row['city_label']:<15}")

# ============================================================
# SAVE RESULTS
# ============================================================
output_path = "/Users/bobrothers/specter-phase2/em_investigation/magnetic_analysis_results.csv"
results_df.to_csv(output_path, index=False)
print(f"\n\nSaved results to: {output_path}")

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

print(f"""
MAGNETIC ANOMALY FINDINGS:

1. OVERALL CORRELATION: {'SIGNIFICANT' if p_spearman < 0.05 else 'NOT SIGNIFICANT'}
   Spearman rho = {corr_spearman:.3f}, p = {p_spearman:.4f}

2. HIGH vs LOW CORRELATION HOTSPOTS:
   High (>2.0): {high_corr['mag_anomaly'].mean():.1f} nT
   Low (<1.5): {low_corr['mag_anomaly'].mean():.1f} nT
   Difference: {high_corr['mag_anomaly'].mean() - low_corr['mag_anomaly'].mean():.1f} nT
   T-test p = {p_ttest:.4f}

3. PORTLAND vs SF BAY AREA:
   Portland: {portland['mag_anomaly'].mean():.1f} nT (low seismic correlation)
   SF Bay: {sf['mag_anomaly'].mean():.1f} nT (high seismic correlation)
   Difference: {sf['mag_anomaly'].mean() - portland['mag_anomaly'].mean():.1f} nT
   T-test p = {p_city:.4f}

4. GRADIENT CORRELATION:
   Spearman rho = {corr_grad:.3f}, p = {p_grad:.4f}

INTERPRETATION:
""")

if p_city < 0.05:
    diff = sf['mag_anomaly'].mean() - portland['mag_anomaly'].mean()
    if diff > 0:
        print("   SF Bay Area has HIGHER magnetic anomaly than Portland.")
        print("   This could indicate more iron-rich basement rock.")
    else:
        print("   Portland has HIGHER magnetic anomaly than SF Bay Area.")
else:
    print("   No significant magnetic difference between cities.")

if abs(corr_spearman) > 0.3 and p_spearman < 0.05:
    print(f"\n   {'Positive' if corr_spearman > 0 else 'Negative'} correlation found between")
    print("   magnetic anomaly and seismic UFO correlation.")
else:
    print("\n   Magnetic anomaly does NOT strongly predict seismic correlation.")
    print("   The piezoelectric/fault effect appears independent of magnetic field.")
