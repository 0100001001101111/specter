# SPECTER

**Seismic-Perceptual Event Correlation and Temporal Evaluation Repository**

Analyzing the correlation between anomalous aerial phenomenon reports and micro-seismic activity.

## Overview

SPECTER investigates whether reports of unexplained aerial phenomena correlate with tectonic activity. Using 67 years of data from the Obiwan UFO Sighting Dataset and USGS earthquake records, the project identifies statistically significant relationships between seismic events and anomalous report clustering.

## Key Findings

### Phase 1: Correlation Established

- **Portland, OR:** 3.44x elevation in reports during seismically active periods (p < 0.0001)
- **San Francisco, CA:** 8.32x elevation (p < 0.0001)
- Spatial clustering along known fault lines
- Dose-response relationship between seismic frequency and report density

### Phase 2: Mechanism Discrimination

- **Precursor Signal:** Reports elevate exponentially BEFORE earthquakes, peaking on Day 0 (29.5x baseline in SF)
- **Spatial Persistence:** Same coordinate produced reports for 54 years in Portland, maintaining top rank across 6 decades
- **Physical Effects:** Reports with physiological symptoms show 1.4x higher seismic correlation than visual-only
- **Fault Proximity:** Fremont hotspot (directly on Hayward Fault) shows highest correlation at 4.33x
- **Duration Asymmetry:** Portland precursor sightings 12x shorter than post-event (50s vs 600s median)

### Bird Behavior Investigation

Community feedback suggested some reports might be birds disturbed by piezoelectric emissions. Analysis of V-formation/chevron shaped reports found:

- **Stronger Precursor Signal:** V-formations show 2.19x before/after ratio vs 1.76x for classic UFO shapes
- **Post-Quake Drop:** 80% reduction in V-formation reports after Day 0 (consistent with stress release)
- **October Spike:** Peak V-formation reports during fall migration
- **Bird Mentions:** Reports explicitly mentioning birds show highest seismic correlation (1.60x)

**Conclusion:** Partial support for bird hypothesis. Some V-formation reports may be disturbed bird flocks, but the precursor pattern exists across all shape categories, suggesting a broader geological phenomenon.

See [bird_investigation/](bird_investigation/) for full analysis.

## Papers

- **Phase 1:** [SPECTER_Phase1_Paper.pdf](paper/SPECTER_Phase1_Paper.pdf) - Correlation analysis
- **Phase 2:** [SPECTER_Phase2_Paper.pdf](paper/SPECTER_Phase2_Paper.pdf) - Mechanism discrimination

OSF Project: [osf.io/x2bmz](https://osf.io/x2bmz)

## Repository Structure

```
specter/
├── data/                    # Raw and processed datasets
├── scripts/                 # Analysis scripts
│   ├── specter_phase1.py
│   ├── specter_phase2_mechanism.py
│   ├── specter_phase2_5_deep.py
│   └── specter_phase2_6_comprehensive.py
├── figures/                 # Generated figures
│   ├── figure1_precursor_ramp_sf.png
│   ├── figure2_precursor_comparison.png
│   ├── figure3_spatial_persistence.png
│   ├── figure4_physical_effects.png
│   ├── figure5_sf_hotspots.png
│   └── figure6_duration.png
├── bird_investigation/      # Bird behavior analysis
│   ├── search_bird_terms.py
│   ├── v_formation_seismic_test.py
│   └── README.md
├── paper/                   # Publication PDFs
└── README.md
```

## Replication

```bash
pip install pandas numpy scipy matplotlib seaborn
python scripts/specter_phase1.py
python scripts/specter_phase2_mechanism.py
```

## Data Sources

- **Obiwan UFO Sighting Dataset** (1947-2014): Kaggle
- **USGS Earthquake Catalog**: earthquake.usgs.gov

## Citation

```
SPECTER Project (2026). Seismic-Perceptual Event Correlation and Temporal Evaluation.
GitHub: github.com/0100001001101111/specter
OSF: osf.io/x2bmz
```

## License

MIT
