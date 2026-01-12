"""SPECTER Interactive Map Generator"""
import folium
from folium import plugins
import json
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from config import OUTPUT_DIR, PORTLAND_BBOX
from db_utils import query_table

# Portland center
PORTLAND_CENTER = [45.5152, -122.6784]

def fetch_map_data():
    """Fetch all data for map visualization"""
    data = {}

    # Paranormal reports
    reports = query_table(
        'specter_paranormal_reports',
        select='latitude,longitude,city,event_date,phenomenon_type,description',
        filters='latitude=not.is.null&longitude=not.is.null',
        limit=2000
    )
    data['reports'] = reports
    print(f"Reports: {len(reports)}")

    # Infrastructure
    for infra_type in ['cemetery', 'church', 'hospital', 'substation', 'cell_tower']:
        infra = query_table(
            'specter_infrastructure',
            select='geom,name,infrastructure_type',
            filters=f'infrastructure_type=eq.{infra_type}',
            limit=1000
        )
        data[f'infra_{infra_type}'] = infra
        print(f"{infra_type}: {len(infra)}")

    # Historical events
    events = query_table(
        'specter_historical_events',
        select='latitude,longitude,location_name,event_type,event_year,description',
        filters='latitude=not.is.null&longitude=not.is.null',
        limit=500
    )
    data['historical'] = events
    print(f"Historical: {len(events)}")

    # Hotspots (from analysis)
    hotspots = query_table(
        'specter_hotspots',
        select='latitude,longitude,combined_score,report_density_score,cemetery_proximity_score',
        limit=50
    )
    data['hotspots'] = hotspots
    print(f"Hotspots: {len(hotspots)}")

    # Clusters
    clusters = query_table(
        'specter_clusters',
        select='centroid,report_count,p_value',
        limit=50
    )
    data['clusters'] = clusters
    print(f"Clusters: {len(clusters)}")

    return data

def parse_wkt_point(geom_str):
    """Parse WKT point to (lat, lon)"""
    if not geom_str:
        return None, None
    try:
        if 'POINT' in str(geom_str):
            coords = str(geom_str).split('POINT')[1].replace('(', '').replace(')', '').strip()
            lon, lat = coords.split()
            return float(lat), float(lon)
    except:
        pass
    return None, None

def get_phenomenon_color(ptype):
    """Get color for phenomenon type"""
    colors = {
        'ufo_uap': 'green',
        'apparition': 'purple',
        'poltergeist': 'red',
        'shadow_figure': 'darkpurple',
        'light_anomaly': 'orange',
        'sound_anomaly': 'blue',
        'other': 'gray'
    }
    return colors.get(ptype, 'gray')

def create_map(data):
    """Create Folium map with all layers"""
    print("\nCreating map...")

    # Base map
    m = folium.Map(
        location=PORTLAND_CENTER,
        zoom_start=11,
        tiles='CartoDB positron'
    )

    # Add different tile layers
    folium.TileLayer('OpenStreetMap').add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='Dark Mode').add_to(m)

    # === Paranormal Reports Layer ===
    reports_group = folium.FeatureGroup(name='Paranormal Reports', show=True)

    for report in data['reports']:
        lat, lon = report.get('latitude'), report.get('longitude')
        if lat and lon:
            popup_html = f"""
            <b>{report.get('phenomenon_type', 'Unknown')}</b><br>
            City: {report.get('city', 'Unknown')}<br>
            Date: {report.get('event_date', 'Unknown')}<br>
            <small>{str(report.get('description', ''))[:200]}...</small>
            """
            folium.CircleMarker(
                location=[lat, lon],
                radius=5,
                color=get_phenomenon_color(report.get('phenomenon_type')),
                fill=True,
                fillOpacity=0.7,
                popup=folium.Popup(popup_html, max_width=300)
            ).add_to(reports_group)

    reports_group.add_to(m)

    # === Cemetery Layer ===
    cemetery_group = folium.FeatureGroup(name='Cemeteries', show=False)

    for item in data.get('infra_cemetery', []):
        lat, lon = parse_wkt_point(item.get('geom'))
        if lat and lon:
            folium.Marker(
                location=[lat, lon],
                icon=folium.Icon(color='black', icon='plus-sign'),
                popup=item.get('name', 'Cemetery')
            ).add_to(cemetery_group)

    cemetery_group.add_to(m)

    # === Churches Layer ===
    church_group = folium.FeatureGroup(name='Churches', show=False)

    for item in data.get('infra_church', []):
        lat, lon = parse_wkt_point(item.get('geom'))
        if lat and lon:
            folium.CircleMarker(
                location=[lat, lon],
                radius=3,
                color='blue',
                fill=True,
                popup=item.get('name', 'Church')
            ).add_to(church_group)

    church_group.add_to(m)

    # === Power Infrastructure Layer ===
    power_group = folium.FeatureGroup(name='Power Infrastructure', show=False)

    for item in data.get('infra_substation', []):
        lat, lon = parse_wkt_point(item.get('geom'))
        if lat and lon:
            folium.CircleMarker(
                location=[lat, lon],
                radius=4,
                color='yellow',
                fill=True,
                fillColor='yellow',
                popup=item.get('name', 'Substation')
            ).add_to(power_group)

    power_group.add_to(m)

    # === Cell Towers Layer ===
    tower_group = folium.FeatureGroup(name='Cell Towers', show=False)

    for item in data.get('infra_cell_tower', []):
        lat, lon = parse_wkt_point(item.get('geom'))
        if lat and lon:
            folium.CircleMarker(
                location=[lat, lon],
                radius=3,
                color='red',
                fill=True,
                popup='Cell Tower'
            ).add_to(tower_group)

    tower_group.add_to(m)

    # === Historical Events Layer ===
    historical_group = folium.FeatureGroup(name='Historical Events', show=False)

    for event in data.get('historical', []):
        lat, lon = event.get('latitude'), event.get('longitude')
        if lat and lon:
            popup_html = f"""
            <b>{event.get('event_type', 'Unknown')}</b><br>
            Year: {event.get('event_year', 'Unknown')}<br>
            {event.get('location_name', '')}<br>
            <small>{str(event.get('description', ''))[:150]}...</small>
            """
            folium.CircleMarker(
                location=[lat, lon],
                radius=6,
                color='darkred',
                fill=True,
                fillColor='red',
                fillOpacity=0.5,
                popup=folium.Popup(popup_html, max_width=300)
            ).add_to(historical_group)

    historical_group.add_to(m)

    # === Hotspots Layer ===
    hotspot_group = folium.FeatureGroup(name='Convergence Hotspots', show=True)

    for hs in data.get('hotspots', []):
        lat, lon = hs.get('latitude'), hs.get('longitude')
        if lat and lon:
            score = hs.get('combined_score', 0)
            # Size based on score
            radius = 10 + (score * 20)

            popup_html = f"""
            <b>HOTSPOT</b><br>
            Score: {score:.3f}<br>
            Report Density: {hs.get('report_density_score', 0):.3f}<br>
            Cemetery Proximity: {hs.get('cemetery_proximity_score', 0):.3f}
            """

            folium.CircleMarker(
                location=[lat, lon],
                radius=radius,
                color='red',
                fill=True,
                fillColor='orange',
                fillOpacity=0.4,
                popup=folium.Popup(popup_html, max_width=200)
            ).add_to(hotspot_group)

    hotspot_group.add_to(m)

    # === Report Heatmap ===
    heat_data = []
    for report in data['reports']:
        lat, lon = report.get('latitude'), report.get('longitude')
        if lat and lon:
            heat_data.append([lat, lon])

    if heat_data:
        plugins.HeatMap(
            heat_data,
            name='Report Heatmap',
            show=False,
            radius=15,
            blur=10,
            max_zoom=13
        ).add_to(m)

    # Add layer control
    folium.LayerControl(collapsed=False).add_to(m)

    # Add fullscreen
    plugins.Fullscreen().add_to(m)

    # Add measure tool
    plugins.MeasureControl(position='topleft').add_to(m)

    return m

def main():
    print("=" * 60)
    print("SPECTER Map Generator")
    print("=" * 60)

    # Fetch data
    print("\nFetching map data...")
    data = fetch_map_data()

    # Create map
    m = create_map(data)

    # Save map
    map_file = os.path.join(OUTPUT_DIR, 'maps', 'specter_portland.html')
    os.makedirs(os.path.dirname(map_file), exist_ok=True)

    m.save(map_file)
    print(f"\nMap saved to {map_file}")

    # Create summary stats
    stats = {
        'total_reports': len(data['reports']),
        'cemeteries': len(data.get('infra_cemetery', [])),
        'churches': len(data.get('infra_church', [])),
        'power_infra': len(data.get('infra_substation', [])),
        'cell_towers': len(data.get('infra_cell_tower', [])),
        'historical_events': len(data.get('historical', [])),
        'hotspots': len(data.get('hotspots', []))
    }

    print("\n--- Map Data Summary ---")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    return map_file

if __name__ == "__main__":
    main()
