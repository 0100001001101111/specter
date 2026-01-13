# SPECTER Karst Investigation

## Hypothesis

Karst topography (limestone/dolomite cave systems) could amplify or channel piezoelectric effects during seismic stress. Underground voids might also collapse or shift, producing acoustic phenomena or surface effects that get reported as UFOs.

## Method

Downloaded the [USGS National Karst Map](https://pubs.usgs.gov/of/2014/1156/) (269 MB shapefile dataset) containing:
- 77,837 carbonate karst polygons (limestone/dolomite)
- 3,801 volcanic pseudokarst polygons (lava tubes)
- 8,220 evaporite karst polygons (salt/gypsum)

Performed spatial overlay with our 102 identified hotspots using geopandas.

## Results

| Metric | Value |
|--------|-------|
| Total hotspots | 102 |
| Hotspots in karst areas | **0 (0.0%)** |
| Expected if random (US avg) | ~20% |
| High-correlation (>2.0) in karst | 0/72 (0.0%) |
| Low-correlation (<1.5) in karst | 0/30 (0.0%) |

### By Karst Type
- Carbonate (limestone caves): 0 hotspots
- Volcanic (lava tubes): 0 hotspots
- Evaporite (salt/gypsum caves): 0 hotspots

## Conclusion

**KARST HYPOTHESIS: NOT SUPPORTED**

Neither Portland nor SF Bay Area contain significant karst geology:

- **Portland:** Underlain by Columbia River Basalt. No carbonate karst.
- **SF Bay Area:** Franciscan Complex melange. Some small marble/limestone units but no major karst.

This is valuable as a **negative control finding**:

1. If UFO reports correlated with karst, we'd expect hotspots in Florida, Kentucky, Missouri, and Texas (major US karst regions)
2. Our hotspots are in non-karst areas
3. This strengthens the case for the **piezoelectric/fault mechanism** as the explanation

## Remaining Tests (Skipped)

Since the overlay showed 0% karst involvement, the following tests were not performed:

- Test 2: Karst vs non-karst piezoelectric comparison (no karst sites available)
- Test 3: EM anomaly overlay (separate investigation if desired)
- Test 4: Cave density analysis (no relevant caves in study areas)

## Files

- `karst_overlay_analysis.py` - Spatial analysis script
- `karst_analysis_results.csv` - Results with karst flags
- `Shapefiles/` - USGS karst shapefiles
- `USKarstMap.zip` - Original download (269 MB)

## Data Source

Weary, D.J., and Doctor, D.H., 2014, Karst in the United States: A digital map compilation and database: U.S. Geological Survey Open-File Report 2014–1156.

https://pubs.usgs.gov/of/2014/1156/
