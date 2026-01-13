# SPECTER Electromagnetic Investigation

## Hypothesis

Natural variations in Earth's magnetic field could interact with seismic stress to produce stronger or weaker piezoelectric effects. Areas with elevated or depressed EM signatures might show different UFO report patterns.

## Data Source

- **USGS Magnetic Anomaly Map**: https://mrdata.usgs.gov/magnetic/
- Downloaded: `magnetic.xyz.gz` (23 MB, 2.5M grid points)
- Format: Longitude, Latitude, Magnetic anomaly (nanoTeslas)
- Coverage: Continental United States

## Key Finding

### STRONG NEGATIVE CORRELATION

| Metric | Value | p-value |
|--------|-------|---------|
| Magnetic vs Seismic Ratio (Spearman) | **ρ = -0.497** | **< 0.0001** |
| Magnetic Gradient vs Seismic Ratio | **ρ = -0.573** | **< 0.0001** |
| High vs Low Correlation T-test | t = 5.69 | **< 0.0001** |

### By Seismic Correlation Level

| Group | Mean Magnetic Anomaly | n |
|-------|----------------------|---|
| High seismic correlation (>2.0) | **28.5 nT** | 72 |
| Low seismic correlation (<1.5) | **270.3 nT** | 30 |

**Difference: 241.8 nT** (highly significant)

### Portland vs SF Bay Area

| Region | Magnetic Anomaly | Seismic Ratio |
|--------|-----------------|---------------|
| Portland | **283.7 nT** | 0.21 (low) |
| SF Bay Area | **30.0 nT** | 10.84 (high) |

**T-test: p < 0.0001**

## Geological Interpretation

This result **supports the piezoelectric hypothesis**:

### High Magnetic Anomaly (Portland)
- Columbia River Basalt = iron-rich volcanic rock
- Iron-rich rocks have high magnetic susceptibility
- Basalt is NOT piezoelectric
- Result: HIGH magnetic, LOW seismic-UFO correlation

### Low Magnetic Anomaly (SF Bay Area)
- Franciscan Complex = oceanic melange
- Contains serpentinite, chert, blueschist
- These rocks are LOW in iron (low magnetic)
- Serpentinite IS piezoelectric
- Result: LOW magnetic, HIGH seismic-UFO correlation

### Why Negative Correlation Makes Sense

```
Piezoelectric rock (serpentinite/Franciscan) → LOW iron → LOW magnetic anomaly
Non-piezoelectric rock (basalt)              → HIGH iron → HIGH magnetic anomaly
```

The magnetic signature acts as a **proxy for piezoelectric potential**:
- Low magnetic = likely piezoelectric = UFO reports correlate with seismic activity
- High magnetic = likely iron-rich/volcanic = UFO reports don't correlate with seismic activity

## Within-Bedrock Analysis

| Bedrock Type | Mean Magnetic | Seismic Correlation |
|--------------|---------------|---------------------|
| Serpentinite/Franciscan | **-13.8 nT** | 95.8% high |
| Franciscan melange | **67.7 nT** | 97.5% high |
| Basalt | **214.6 nT** | 0% high |
| Alluvial fill | **329.8 nT** | 0% high |
| Alluvial sediment | **369.8 nT** | 0% high |

The magnetic signature clearly separates the bedrock types that show seismic-UFO correlation from those that don't.

## Top 10 Hotspots

| Location | Reports | Seismic Ratio | Magnetic (nT) |
|----------|---------|---------------|---------------|
| Portland parking lot | 342 | 0.18 | **344.5** (high) |
| SF Civic Center | 191 | 24.80 | 81.6 (low) |
| San Jose Downtown | 191 | 20.56 | **-0.7** (low) |
| Vancouver WA | 137 | 0.16 | **539.1** (high) |
| Santa Rosa | 77 | 12.17 | -21.0 (low) |

The pattern is consistent: high seismic correlation = low magnetic anomaly.

## Files

- `magnetic_analysis.py` - Analysis script
- `magnetic_analysis_results.csv` - Results with magnetic values
- `magnetic.xyz` - USGS magnetic grid (decompressed)
- `magnetic.xyz.gz` - Original download (23 MB)

## Conclusion

**MAGNETIC ANOMALY STRONGLY PREDICTS SEISMIC-UFO CORRELATION**

The strong negative correlation (ρ = -0.497, p < 0.0001) provides independent confirmation that:

1. **Piezoelectric geology** (low magnetic, serpentinite/Franciscan) shows seismic-UFO correlation
2. **Non-piezoelectric geology** (high magnetic, basalt/alluvial) does NOT show correlation
3. **Portland vs SF difference** is explained by magnetic signature (and thus bedrock type)

This is the strongest statistical finding in Phase 3, achieving p < 0.0001 significance.
