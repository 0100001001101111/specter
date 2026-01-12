# SPECTER: Spatial Paranormal Event Correlation & Terrain Analysis Engine

**Author:** Tars

A geospatial data science project investigating correlations between paranormal reports and environmental factors, with focus on seismic activity.

## Key Findings

Analysis of 1,904 paranormal reports across Portland, OR and San Francisco Bay Area reveals:

1. **Seismic Correlation**: Reports occur 3.4x more frequently (Portland) and 8.3x more frequently (SF) during seismically active periods compared to quiet periods (>30 days without earthquakes).

2. **Temporal Pattern**: Reports peak 1-2 days after earthquakes and decay exponentially over 7 days.

3. **Spatial Clustering**: Reports cluster significantly near active fault lines (Portland Hills Fault, San Andreas, Hayward).

4. **Night Bias**: 48-64% of reports occur at night (expected: 37.5%).

5. **Dose-Response**: The effect scales with regional earthquake frequency, suggesting a causal relationship.

## Data Sources

| Dataset | Source | URL |
|---------|--------|-----|
| UFO Reports | Obiwan/NUFORC | https://github.com/planetsig/ufo-reports |
| Earthquakes | USGS FDSNWS | https://earthquake.usgs.gov/fdsnws/event/1/ |
| Infrastructure | OpenStreetMap | https://overpass-api.de/api/interpreter |
| Fault Lines | USGS | https://earthquake.usgs.gov/hazards/qfaults/ |

## Installation

```bash
# Clone repository
git clone https://github.com/[username]/specter.git
cd specter

# Install dependencies
pip install -r requirements.txt
```

## Dependencies

- Python 3.10+
- pandas, numpy, scipy
- geopandas, shapely
- scikit-learn, hdbscan
- matplotlib, seaborn, folium
- requests

## Usage

### 1. Data Ingestion

```bash
# Fetch and process paranormal reports (Oregon)
python scripts/ingest_obiwan.py

# Fetch infrastructure data
python scripts/ingest_infrastructure.py

# Fetch geological/earthquake data
python scripts/ingest_geology.py
```

### 2. Run Analyses

```bash
# Spatial clustering
python scripts/analysis_clustering.py

# Seismic-temporal correlation
python scripts/analysis_seismic_correlation.py

# Temporal patterns
python scripts/analysis_temporal.py

# Multi-layer hotspot detection
python scripts/analysis_hotspots.py
```

### 3. San Francisco Replication

```bash
# Run full SF Bay Area analysis
python scripts/sf_analysis.py
```

### 4. Generate Outputs

```bash
# Generate interactive maps
python scripts/generate_map.py

# Generate publication figures
python scripts/generate_figures.py

# Generate executive summary
python scripts/generate_report.py
```

## Project Structure

```
specter-release/
├── README.md
├── requirements.txt
├── scripts/
│   ├── config.py              # Configuration and constants
│   ├── db_utils.py            # Database utilities
│   ├── ingest_*.py            # Data ingestion scripts
│   ├── analysis_*.py          # Analysis scripts
│   ├── generate_*.py          # Output generation
│   └── sf_analysis.py         # SF Bay Area replication
├── data/
│   ├── raw/
│   │   └── FETCH_DATA.md      # Instructions to fetch raw data
│   └── outputs/
│       ├── clustering_results.json
│       ├── correlation_results.json
│       ├── seismic_correlation_results.json
│       ├── temporal_results.json
│       ├── hotspot_results.json
│       └── sf_analysis_results.json
├── figures/
│   ├── figure1_hotspot_maps.png
│   ├── figure2_days_histogram.png
│   ├── figure3_active_quiet.png
│   ├── figure4_scaling.png
│   ├── figure5_timeline.png
│   ├── specter_portland.html  # Interactive map
│   └── specter_sf.html        # Interactive map
└── paper/
    └── SPECTER_Executive_Summary.md
```

## Results Summary

| Metric | Portland | SF Bay Area |
|--------|----------|-------------|
| Total Reports | 745 | 1,159 |
| Spatial Clusters | 8 | 48 |
| Clustering p-value | < 0.0001 | < 0.0001 |
| Night Report Ratio | 63.8% | 48.3% |
| Active/Quiet Ratio | 3.4x | 8.3x |
| Peak Day After EQ | Day 1 | Day 2 |

## Database Setup (Optional)

The scripts can use Supabase/PostgreSQL with PostGIS for data storage. Update `config.py` with your credentials:

```python
SUPABASE_URL = "your-url"
SUPABASE_KEY = "your-key"
```

Or run locally by modifying scripts to use pandas DataFrames instead.

## Citation

If you use this project in research, please cite:

```
SPECTER: Spatial Paranormal Event Correlation & Terrain Analysis Engine
https://github.com/[username]/specter
```

## License

MIT License

## Acknowledgments

- USGS Earthquake Hazards Program
- National UFO Reporting Center (NUFORC)
- OpenStreetMap contributors
