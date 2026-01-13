#!/usr/bin/env python3
"""
BOVINE-SPECTER Correlation Check
Do cattle mutilation locations cluster on piezoelectric geology?
"""

import json
import numpy as np
from scipy import stats
from scipy.interpolate import RegularGridInterpolator
import os

print("=" * 70)
print("BOVINE-SPECTER PIEZOELECTRIC CORRELATION CHECK")
print("=" * 70)

# Load mutilation cases
with open('/Users/bobrothers/bovine_research/analysis_data.json', 'r') as f:
    data = json.load(f)

cases = data['mutilation_cases']
print(f"\nLoaded {len(cases)} mutilation cases")

# Extract coordinates
mutilation_coords = []
for case in cases:
    if case.get('lat') and case.get('lon'):
        mutilation_coords.append({
            'lat': case['lat'],
            'lon': case['lon'],
            'state': case['state'],
            'county': case.get('county', 'Unknown')
        })

print(f"Cases with coordinates: {len(mutilation_coords)}")

# Simple magnetic grid class
class MagneticGrid:
    """Load and query USGS magnetic anomaly grid."""

    def __init__(self, filepath):
        print(f"Loading grid from {filepath}...")
        lons, lats, vals = [], [], []

        with open(filepath, 'r') as f:
            for i, line in enumerate(f):
                if i % 100000 == 0:
                    print(f"  Loaded {i:,} points...", end='\r')
                parts = line.strip().split()
                if len(parts) >= 3:
                    try:
                        lon, lat, val = float(parts[0]), float(parts[1]), float(parts[2])
                        lons.append(lon)
                        lats.append(lat)
                        vals.append(val)
                    except ValueError:
                        continue

        print(f"\n  Total points: {len(vals):,}")

        # Build grid
        unique_lons = sorted(set(lons))
        unique_lats = sorted(set(lats))

        self.lon_min, self.lon_max = min(unique_lons), max(unique_lons)
        self.lat_min, self.lat_max = min(unique_lats), max(unique_lats)

        # Create lookup dict for fast access
        self.data = {}
        for lon, lat, val in zip(lons, lats, vals):
            self.data[(round(lon, 2), round(lat, 2))] = val

        print(f"  Grid bounds: lat [{self.lat_min:.1f}, {self.lat_max:.1f}], lon [{self.lon_min:.1f}, {self.lon_max:.1f}]")

    def get_anomaly(self, lat, lon):
        """Get magnetic anomaly at location (nearest neighbor)."""
        if lat < self.lat_min or lat > self.lat_max:
            return None
        if lon < self.lon_min or lon > self.lon_max:
            return None

        # Round to grid resolution
        key = (round(lon, 2), round(lat, 2))
        if key in self.data:
            return self.data[key]

        # Try nearby points
        for d_lon in [0, 0.01, -0.01, 0.02, -0.02]:
            for d_lat in [0, 0.01, -0.01, 0.02, -0.02]:
                key = (round(lon + d_lon, 2), round(lat + d_lat, 2))
                if key in self.data:
                    return self.data[key]

        return None

# Load magnetic grid
print("\nLoading magnetic anomaly grid...")
grid_paths = [
    '/Users/bobrothers/specter-watch/magnetic.xyz',
    '/Users/bobrothers/specter-phase2/em_investigation/magnetic.xyz'
]

grid_path = None
for path in grid_paths:
    if os.path.exists(path):
        grid_path = path
        break

if not grid_path:
    print("ERROR: Magnetic grid not found. Please download from USGS.")
    print("Expected locations:")
    for p in grid_paths:
        print(f"  {p}")
    exit(1)

grid = MagneticGrid(grid_path)

# Query magnetic values at mutilation sites
print("\n" + "-" * 70)
print("MAGNETIC ANOMALY AT MUTILATION SITES")
print("-" * 70)

mutilation_magnetic = []
print(f"\n{'State':<15} {'County':<15} {'Lat':>8} {'Lon':>10} {'Mag (nT)':>10} {'Zone':>15}")
print("-" * 75)

for coord in mutilation_coords:
    mag = grid.get_anomaly(coord['lat'], coord['lon'])
    if mag is not None:
        mutilation_magnetic.append(mag)
        zone = "PIEZOELECTRIC" if abs(mag) < 100 else "Non-piezo"
        print(f"{coord['state']:<15} {coord['county']:<15} {coord['lat']:>8.2f} {coord['lon']:>10.2f} {mag:>10.1f} {zone:>15}")
    else:
        print(f"{coord['state']:<15} {coord['county']:<15} {coord['lat']:>8.2f} {coord['lon']:>10.2f} {'N/A':>10} {'--':>15}")

print(f"\nSites with magnetic data: {len(mutilation_magnetic)}/{len(mutilation_coords)}")

if len(mutilation_magnetic) == 0:
    print("\nERROR: No magnetic data found for any mutilation sites.")
    print("Grid may not cover these locations.")
    exit(1)

# Generate random US locations for comparison
print("\n" + "-" * 70)
print("RANDOM US BASELINE (n=500)")
print("-" * 70)

np.random.seed(42)
random_magnetic = []

# Continental US bounds (within grid)
US_BOUNDS = {'lat_min': 25, 'lat_max': 49, 'lon_min': -125, 'lon_max': -67}

attempts = 0
while len(random_magnetic) < 500 and attempts < 3000:
    lat = np.random.uniform(US_BOUNDS['lat_min'], US_BOUNDS['lat_max'])
    lon = np.random.uniform(US_BOUNDS['lon_min'], US_BOUNDS['lon_max'])
    mag = grid.get_anomaly(lat, lon)
    if mag is not None:
        random_magnetic.append(mag)
    attempts += 1
    if attempts % 500 == 0:
        print(f"  Sampled {len(random_magnetic)} random locations...")

print(f"Random US locations sampled: {len(random_magnetic)}")

# SPECTER hotspot reference values (from Phase 1-3)
# SF Bay Area low-magnetic hotspots had mean ~30 nT
specter_hotspot_mean = 30.0
specter_hotspot_std = 45.0

# Calculate statistics
print("\n" + "=" * 70)
print("COMPARISON: MUTILATIONS vs RANDOM vs SPECTER HOTSPOTS")
print("=" * 70)

mut_mean = np.mean(mutilation_magnetic)
mut_std = np.std(mutilation_magnetic)
mut_median = np.median(mutilation_magnetic)

rand_mean = np.mean(random_magnetic)
rand_std = np.std(random_magnetic)
rand_median = np.median(random_magnetic)

print(f"\n{'Metric':<25} {'Mutilations':>15} {'Random US':>15} {'SPECTER UFO':>15}")
print("-" * 72)
print(f"{'Mean magnetic (nT)':<25} {mut_mean:>15.1f} {rand_mean:>15.1f} {specter_hotspot_mean:>15.1f}")
print(f"{'Std dev':<25} {mut_std:>15.1f} {rand_std:>15.1f} {specter_hotspot_std:>15.1f}")
print(f"{'Median':<25} {mut_median:>15.1f} {rand_median:>15.1f} {'~25':>15}")
print(f"{'N':<25} {len(mutilation_magnetic):>15} {len(random_magnetic):>15} {'~490':>15}")

# Low magnetic zone counts
mut_low_mag = sum(1 for m in mutilation_magnetic if abs(m) < 100)
rand_low_mag = sum(1 for m in random_magnetic if abs(m) < 100)

mut_pct = 100 * mut_low_mag / len(mutilation_magnetic) if mutilation_magnetic else 0
rand_pct = 100 * rand_low_mag / len(random_magnetic) if random_magnetic else 0

print(f"\n{'% in low-mag zone (<100nT)':<25} {mut_pct:>14.1f}% {rand_pct:>14.1f}% {'~85%':>15}")

# Statistical tests
print("\n" + "-" * 70)
print("STATISTICAL TESTS")
print("-" * 70)

# T-test: mutilations vs random
t_stat, t_pval = stats.ttest_ind(mutilation_magnetic, random_magnetic)
print(f"\nT-test (mutilations vs random US):")
print(f"  t-statistic: {t_stat:.3f}")
print(f"  p-value: {t_pval:.6f}")
print(f"  Significant: {'YES' if t_pval < 0.05 else 'NO'}")

# Mann-Whitney U (non-parametric)
u_stat, u_pval = stats.mannwhitneyu(mutilation_magnetic, random_magnetic, alternative='two-sided')
print(f"\nMann-Whitney U test:")
print(f"  U-statistic: {u_stat:.1f}")
print(f"  p-value: {u_pval:.6f}")
print(f"  Significant: {'YES' if u_pval < 0.05 else 'NO'}")

# Chi-square: proportion in low-mag zones
from scipy.stats import chi2_contingency

contingency = [
    [mut_low_mag, len(mutilation_magnetic) - mut_low_mag],
    [rand_low_mag, len(random_magnetic) - rand_low_mag]
]
chi2, chi_pval, dof, expected = chi2_contingency(contingency)
print(f"\nChi-square (low-mag zone proportion):")
print(f"  Chi-square: {chi2:.3f}")
print(f"  p-value: {chi_pval:.6f}")
print(f"  Significant: {'YES' if chi_pval < 0.05 else 'NO'}")

# Interpretation
print("\n" + "=" * 70)
print("INTERPRETATION")
print("=" * 70)

# Check if mutilations cluster on low-magnetic like SPECTER hotspots
specter_like = abs(mut_mean) < 100 and mut_pct > 70

if mut_pct > rand_pct + 10 and abs(mut_mean) < abs(rand_mean):
    connection = "POSSIBLE CONNECTION"
    explanation = f"""
Mutilation sites show LOWER magnetic anomaly than random US locations:
  - Mutilation mean: {mut_mean:.1f} nT vs Random mean: {rand_mean:.1f} nT
  - Mutilation low-mag: {mut_pct:.1f}% vs Random low-mag: {rand_pct:.1f}%
  - SPECTER UFO hotspots: ~30 nT mean, ~85% low-mag

This suggests mutilations may cluster on similar geology to UFO hotspots.
However, this could also reflect:
  1. Ranching occurring in specific Western geology
  2. Selection bias in case documentation
  3. Actual geological correlation worth investigating
"""
elif abs(mut_mean - rand_mean) < 50 and abs(mut_pct - rand_pct) < 15:
    connection = "NO CLEAR CONNECTION"
    explanation = f"""
Mutilation sites show SIMILAR magnetic signature to random US locations:
  - Mutilation mean: {mut_mean:.1f} nT vs Random mean: {rand_mean:.1f} nT
  - Mutilation low-mag: {mut_pct:.1f}% vs Random low-mag: {rand_pct:.1f}%
  - SPECTER UFO hotspots: ~30 nT mean, ~85% low-mag

Mutilations do NOT cluster on piezoelectric geology like UFO reports do.
The phenomena appear geologically independent.
"""
else:
    connection = "INCONCLUSIVE"
    explanation = f"""
Results are mixed:
  - Mutilation mean: {mut_mean:.1f} nT vs Random mean: {rand_mean:.1f} nT
  - Mutilation low-mag: {mut_pct:.1f}% vs Random low-mag: {rand_pct:.1f}%

More data needed for definitive conclusion.
"""

print(f"\nVERDICT: {connection}")
print(explanation)

# State-by-state breakdown
print("\n" + "-" * 70)
print("STATE-BY-STATE MAGNETIC PROFILE")
print("-" * 70)

state_magnetic = {}
for i, coord in enumerate(mutilation_coords):
    mag = grid.get_anomaly(coord['lat'], coord['lon'])
    if mag is not None:
        state = coord['state']
        if state not in state_magnetic:
            state_magnetic[state] = []
        state_magnetic[state].append(mag)

print(f"\n{'State':<15} {'Cases':>8} {'Mean Mag':>12} {'Low-Mag %':>12}")
print("-" * 50)
for state in sorted(state_magnetic.keys()):
    mags = state_magnetic[state]
    low_pct = 100 * sum(1 for m in mags if abs(m) < 100) / len(mags)
    print(f"{state:<15} {len(mags):>8} {np.mean(mags):>12.1f} {low_pct:>11.1f}%")

# Save results
results = {
    'mutilation_mean_magnetic': float(mut_mean),
    'mutilation_std': float(mut_std),
    'mutilation_low_mag_pct': float(mut_pct),
    'mutilation_n': len(mutilation_magnetic),
    'random_us_mean_magnetic': float(rand_mean),
    'random_us_low_mag_pct': float(rand_pct),
    'random_us_n': len(random_magnetic),
    'specter_hotspot_mean': specter_hotspot_mean,
    'specter_hotspot_low_mag_pct': 85.0,
    't_test_pvalue': float(t_pval),
    'mann_whitney_pvalue': float(u_pval),
    'chi_square_pvalue': float(chi_pval),
    'verdict': connection,
    'state_breakdown': {s: {'n': len(m), 'mean': float(np.mean(m)),
                           'low_mag_pct': float(100*sum(1 for x in m if abs(x)<100)/len(m))}
                        for s, m in state_magnetic.items()}
}

with open('/Users/bobrothers/specter-phase2/bovine_research/piezoelectric_correlation_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\n\nResults saved to piezoelectric_correlation_results.json")
