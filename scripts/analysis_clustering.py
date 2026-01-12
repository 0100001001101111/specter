"""SPECTER Spatial Clustering Analysis"""
import numpy as np
import pandas as pd
from scipy import stats
from scipy.spatial.distance import cdist
import json
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from config import RAW_DIR, OUTPUT_DIR, PORTLAND_BBOX, CLUSTER_EPS_METERS, CLUSTER_MIN_SAMPLES
from db_utils import query_table, insert_records

def fetch_report_data():
    """Fetch paranormal reports with coordinates"""
    reports = query_table(
        'specter_paranormal_reports',
        select='id,latitude,longitude,city,event_date,phenomenon_type',
        filters='latitude=not.is.null&longitude=not.is.null',
        limit=5000
    )
    return pd.DataFrame(reports)

def fetch_infrastructure_data():
    """Fetch infrastructure data"""
    infra = query_table(
        'specter_infrastructure',
        select='id,geom,infrastructure_type,name',
        limit=10000
    )
    return infra

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in meters"""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)

    a = np.sin(dphi/2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda/2)**2
    return 2 * R * np.arcsin(np.sqrt(a))

def dbscan_clustering(coords, eps_meters=500, min_samples=5):
    """Run DBSCAN clustering on coordinates"""
    from sklearn.cluster import DBSCAN

    # Convert to radians for haversine
    coords_rad = np.radians(coords)

    # DBSCAN with haversine metric
    # eps in radians: eps_meters / earth_radius
    eps_rad = eps_meters / 6371000

    clustering = DBSCAN(
        eps=eps_rad,
        min_samples=min_samples,
        metric='haversine'
    )
    labels = clustering.fit_predict(coords_rad)

    return labels

def hdbscan_clustering(coords, min_cluster_size=5):
    """Run HDBSCAN clustering"""
    try:
        import hdbscan

        # Convert to radians
        coords_rad = np.radians(coords)

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            metric='haversine'
        )
        labels = clusterer.fit_predict(coords_rad)

        return labels, clusterer.probabilities_
    except ImportError:
        print("HDBSCAN not available, using DBSCAN only")
        return None, None

def analyze_clusters(df, labels):
    """Analyze identified clusters"""
    clusters = []

    unique_labels = set(labels)
    unique_labels.discard(-1)  # Remove noise label

    for label in unique_labels:
        mask = labels == label
        cluster_points = df[mask]

        centroid_lat = cluster_points['latitude'].mean()
        centroid_lon = cluster_points['longitude'].mean()

        # Calculate cluster statistics
        report_count = len(cluster_points)

        # Date range
        dates = pd.to_datetime(cluster_points['event_date'], errors='coerce')
        valid_dates = dates.dropna()

        date_range = None
        if len(valid_dates) > 0:
            date_range = f"{valid_dates.min().strftime('%Y')} - {valid_dates.max().strftime('%Y')}"

        # Most common phenomenon type
        type_counts = cluster_points['phenomenon_type'].value_counts()
        dominant_type = type_counts.index[0] if len(type_counts) > 0 else 'unknown'

        # City
        city_counts = cluster_points['city'].value_counts()
        primary_city = city_counts.index[0] if len(city_counts) > 0 else 'unknown'

        clusters.append({
            'cluster_label': int(label),
            'centroid_lat': centroid_lat,
            'centroid_lon': centroid_lon,
            'report_count': report_count,
            'date_range': date_range,
            'dominant_type': dominant_type,
            'primary_city': primary_city,
            'cities': list(cluster_points['city'].unique())
        })

    return sorted(clusters, key=lambda x: x['report_count'], reverse=True)

def test_cluster_significance(df, labels, n_permutations=100):
    """Test if clustering is statistically significant vs random distribution"""
    from sklearn.cluster import DBSCAN

    # Count actual clusters
    actual_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    actual_clustered = sum(labels != -1)

    # Permutation test - shuffle coordinates
    coords = df[['latitude', 'longitude']].values

    null_cluster_counts = []
    null_clustered_counts = []

    for _ in range(n_permutations):
        # Shuffle latitude and longitude independently
        shuffled = coords.copy()
        np.random.shuffle(shuffled[:, 0])
        np.random.shuffle(shuffled[:, 1])

        # Re-cluster
        shuffled_rad = np.radians(shuffled)
        eps_rad = CLUSTER_EPS_METERS / 6371000

        clustering = DBSCAN(eps=eps_rad, min_samples=CLUSTER_MIN_SAMPLES, metric='haversine')
        null_labels = clustering.fit_predict(shuffled_rad)

        null_clusters = len(set(null_labels)) - (1 if -1 in null_labels else 0)
        null_clustered = sum(null_labels != -1)

        null_cluster_counts.append(null_clusters)
        null_clustered_counts.append(null_clustered)

    # Calculate p-values
    p_value_clusters = sum(n >= actual_clusters for n in null_cluster_counts) / n_permutations
    p_value_clustered = sum(n >= actual_clustered for n in null_clustered_counts) / n_permutations

    return {
        'actual_clusters': actual_clusters,
        'actual_clustered_points': actual_clustered,
        'null_mean_clusters': np.mean(null_cluster_counts),
        'null_std_clusters': np.std(null_cluster_counts),
        'p_value_clusters': p_value_clusters,
        'null_mean_clustered': np.mean(null_clustered_counts),
        'p_value_clustered': p_value_clustered,
        'significant': p_value_clustered < 0.05
    }

def main():
    print("=" * 60)
    print("SPECTER Spatial Clustering Analysis")
    print("=" * 60)

    # Fetch data
    print("\nFetching paranormal report data...")
    df = fetch_report_data()
    print(f"Retrieved {len(df)} reports with coordinates")

    if len(df) < 10:
        print("Insufficient data for clustering analysis")
        return None

    # Filter to Portland metro area for focused analysis
    portland_df = df[
        (df['latitude'] >= PORTLAND_BBOX['min_lat']) &
        (df['latitude'] <= PORTLAND_BBOX['max_lat']) &
        (df['longitude'] >= PORTLAND_BBOX['min_lon']) &
        (df['longitude'] <= PORTLAND_BBOX['max_lon'])
    ].copy()

    print(f"Portland metro reports: {len(portland_df)}")

    # Use all Oregon data if Portland subset is too small
    analysis_df = portland_df if len(portland_df) >= 50 else df
    print(f"Analyzing {len(analysis_df)} reports")

    # Run DBSCAN clustering
    print("\n--- DBSCAN Clustering ---")
    coords = analysis_df[['latitude', 'longitude']].values

    dbscan_labels = dbscan_clustering(coords, eps_meters=CLUSTER_EPS_METERS, min_samples=CLUSTER_MIN_SAMPLES)

    n_clusters = len(set(dbscan_labels)) - (1 if -1 in dbscan_labels else 0)
    n_noise = sum(dbscan_labels == -1)

    print(f"DBSCAN found {n_clusters} clusters")
    print(f"Points in clusters: {len(dbscan_labels) - n_noise}")
    print(f"Noise points: {n_noise}")

    # Analyze clusters
    clusters = analyze_clusters(analysis_df, dbscan_labels)

    print("\n--- Top Clusters ---")
    for i, cluster in enumerate(clusters[:10]):
        print(f"\nCluster {cluster['cluster_label']}:")
        print(f"  Reports: {cluster['report_count']}")
        print(f"  Location: {cluster['primary_city']} ({cluster['centroid_lat']:.4f}, {cluster['centroid_lon']:.4f})")
        print(f"  Dominant type: {cluster['dominant_type']}")
        print(f"  Date range: {cluster['date_range']}")

    # Statistical significance test
    print("\n--- Significance Testing ---")
    print("Running permutation test (this may take a moment)...")

    significance = test_cluster_significance(analysis_df, dbscan_labels, n_permutations=100)

    print(f"Actual clusters: {significance['actual_clusters']}")
    print(f"Null mean clusters: {significance['null_mean_clusters']:.2f} +/- {significance['null_std_clusters']:.2f}")
    print(f"P-value (clusters): {significance['p_value_clusters']:.4f}")
    print(f"P-value (clustered points): {significance['p_value_clustered']:.4f}")
    print(f"Significant at p<0.05: {significance['significant']}")

    # Try HDBSCAN
    print("\n--- HDBSCAN Clustering ---")
    hdbscan_labels, probabilities = hdbscan_clustering(coords, min_cluster_size=CLUSTER_MIN_SAMPLES)

    if hdbscan_labels is not None:
        n_clusters_h = len(set(hdbscan_labels)) - (1 if -1 in hdbscan_labels else 0)
        print(f"HDBSCAN found {n_clusters_h} clusters")

        hdbscan_clusters = analyze_clusters(analysis_df, hdbscan_labels)

        for i, cluster in enumerate(hdbscan_clusters[:5]):
            print(f"\nHDBSCAN Cluster {cluster['cluster_label']}: {cluster['report_count']} reports at {cluster['primary_city']}")

    # Save results
    results = {
        'total_reports_analyzed': len(analysis_df),
        'dbscan_clusters': n_clusters,
        'dbscan_cluster_details': clusters,
        'significance_test': significance,
        'hdbscan_clusters': n_clusters_h if hdbscan_labels is not None else None
    }

    output_file = os.path.join(OUTPUT_DIR, 'reports', 'clustering_results.json')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nResults saved to {output_file}")

    # Store significant clusters in database
    if clusters:
        db_records = []
        for c in clusters[:20]:  # Top 20 clusters
            db_records.append({
                'cluster_label': c['cluster_label'],
                'centroid': f"SRID=4326;POINT({c['centroid_lon']} {c['centroid_lat']})",
                'report_count': c['report_count'],
                'significant': significance['significant'],
                'p_value': significance['p_value_clustered']
            })

        inserted, errors = insert_records('specter_clusters', db_records)
        print(f"Stored {inserted} cluster records in database")

    return results

if __name__ == "__main__":
    main()
