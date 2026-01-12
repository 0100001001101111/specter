# Data Fetching Instructions

This document provides instructions for fetching the raw data used in the SPECTER analysis.

## 1. Paranormal Reports (Obiwan/NUFORC)

**Source**: https://github.com/planetsig/ufo-reports

```bash
# Download the complete scrubbed dataset
curl -L -o scrubbed.csv "https://raw.githubusercontent.com/planetsig/ufo-reports/master/csv-data/scrubbed.csv"
```

The CSV contains ~80,000 reports. Filter for your region of interest:
- Oregon: state == "or"
- California: state == "ca"

**Columns**: datetime, city, state, country, shape, duration (seconds), duration (hours/min), comments, date posted, latitude, longitude

## 2. Earthquake Data (USGS)

**Source**: https://earthquake.usgs.gov/fdsnws/event/1/

### Portland Region (1994-2024)
```bash
curl -o earthquakes_portland.json "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime=1994-01-01&endtime=2024-12-31&minlatitude=44.5&maxlatitude=46.5&minlongitude=-124.0&maxlongitude=-121.5&minmagnitude=1.0"
```

### San Francisco Bay Area (1994-2024)
```bash
curl -o earthquakes_sf.json "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime=1994-01-01&endtime=2024-12-31&latitude=37.7749&longitude=-122.4194&maxradiuskm=100&minmagnitude=1.0"
```

## 3. Fault Line Data (USGS)

**Source**: https://earthquake.usgs.gov/hazards/qfaults/

Download the Quaternary Fault and Fold Database shapefile:
1. Visit https://earthquake.usgs.gov/hazards/qfaults/
2. Click "Download Data"
3. Select GeoJSON or Shapefile format
4. Filter for your region

### Portland Area Faults
Key faults to extract:
- Portland Hills Fault
- East Bank Fault
- Oatfield Fault
- Bolton Fault
- Cascadia Subduction Zone

## 4. Infrastructure Data (OpenStreetMap)

**Source**: https://overpass-api.de/api/interpreter

### Cemeteries
```
[out:json][timeout:60];
area["name"="Oregon"]["admin_level"="4"]->.searchArea;
(
  node["landuse"="cemetery"](area.searchArea);
  way["landuse"="cemetery"](area.searchArea);
  relation["landuse"="cemetery"](area.searchArea);
);
out center;
```

### Churches/Religious Buildings
```
[out:json][timeout:60];
area["name"="Oregon"]["admin_level"="4"]->.searchArea;
(
  node["amenity"="place_of_worship"](area.searchArea);
  way["amenity"="place_of_worship"](area.searchArea);
);
out center;
```

### Hospitals
```
[out:json][timeout:60];
area["name"="Oregon"]["admin_level"="4"]->.searchArea;
(
  node["amenity"="hospital"](area.searchArea);
  way["amenity"="hospital"](area.searchArea);
);
out center;
```

### Power Substations
```
[out:json][timeout:60];
area["name"="Oregon"]["admin_level"="4"]->.searchArea;
node["power"="substation"](area.searchArea);
out;
```

### Cell Towers
```
[out:json][timeout:60];
area["name"="Oregon"]["admin_level"="4"]->.searchArea;
node["tower:type"="communication"](area.searchArea);
out;
```

**To execute these queries:**
```bash
curl -X POST -d 'YOUR_QUERY_HERE' https://overpass-api.de/api/interpreter > output.json
```

## 5. Historical Events

### NTSB Aviation Accidents
**Source**: https://www.ntsb.gov/Pages/AviationQueryV2.aspx

Query parameters:
- State: Oregon or California
- Date range: 1994-2024
- Export as CSV

### Historical Newspapers (Optional)
**Source**: https://chroniclingamerica.loc.gov/

API endpoint: `https://chroniclingamerica.loc.gov/search/pages/results/`

Parameters:
- `state`: Oregon
- `dateFilterType`: yearRange
- `date1`: 1900
- `date2`: 1960
- `proxtext`: "ghost OR haunted OR apparition"
- `format`: json

## Data Processing Notes

1. **Coordinate Systems**: All data should be in WGS84 (EPSG:4326)
2. **Date Formats**: Standardize to ISO 8601 (YYYY-MM-DD)
3. **Missing Values**: Handle gracefully in analysis scripts
4. **API Rate Limits**:
   - USGS: No strict limits, but be respectful
   - Overpass: ~10,000 requests/day
   - Chronicling America: ~20 requests/minute

## Supabase Setup (Optional)

If using Supabase for storage:

1. Create a new project at https://supabase.com
2. Enable PostGIS extension:
   ```sql
   CREATE EXTENSION IF NOT EXISTS postgis;
   ```
3. Update `config.py` with your credentials
4. Run the ingestion scripts to populate tables
