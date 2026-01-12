"""SPECTER Executive Summary Report Generator"""
import json
import os
import sys
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))

from config import OUTPUT_DIR
from db_utils import query_table

def load_analysis_results():
    """Load all analysis results"""
    results = {}
    reports_dir = os.path.join(OUTPUT_DIR, 'reports')

    files = ['clustering_results.json', 'correlation_results.json',
             'temporal_results.json', 'hotspot_results.json']

    for f in files:
        path = os.path.join(reports_dir, f)
        if os.path.exists(path):
            with open(path) as fp:
                results[f.replace('.json', '')] = json.load(fp)
                print(f"Loaded {f}")

    return results

def get_database_stats():
    """Get summary statistics from database"""
    stats = {}

    # Report counts
    reports = query_table('specter_paranormal_reports', select='count', limit=1)

    # Count by phenomenon type
    types_query = query_table(
        'specter_paranormal_reports',
        select='phenomenon_type',
        limit=5000
    )
    type_counts = {}
    for r in types_query:
        t = r.get('phenomenon_type', 'unknown')
        type_counts[t] = type_counts.get(t, 0) + 1
    stats['phenomenon_types'] = type_counts
    stats['total_reports'] = sum(type_counts.values())

    # Infrastructure counts
    infra = query_table('specter_infrastructure', select='infrastructure_type', limit=5000)
    infra_counts = {}
    for i in infra:
        t = i.get('infrastructure_type', 'unknown')
        infra_counts[t] = infra_counts.get(t, 0) + 1
    stats['infrastructure'] = infra_counts

    # Historical events
    hist = query_table('specter_historical_events', select='event_type', limit=5000)
    stats['historical_events'] = len(hist)

    return stats

def generate_markdown_report(results, stats):
    """Generate markdown executive summary"""
    report = []

    report.append("# SPECTER Phase 1 Analysis Report")
    report.append(f"## Portland, Oregon - {datetime.now().strftime('%Y-%m-%d')}")
    report.append("")
    report.append("---")
    report.append("")

    # Executive Summary
    report.append("## Executive Summary")
    report.append("")
    report.append(f"SPECTER Phase 1 analyzed **{stats['total_reports']} paranormal reports** in Oregon, ")
    report.append(f"with focus on the Portland metropolitan area. The analysis correlated these reports ")
    report.append(f"with **{sum(stats['infrastructure'].values())} infrastructure points** and ")
    report.append(f"**{stats['historical_events']} historical events**.")
    report.append("")

    # Key Findings
    report.append("## Key Findings")
    report.append("")

    # Clustering results
    if 'clustering_results' in results:
        cr = results['clustering_results']
        sig = cr.get('significance_test', {})

        report.append("### Spatial Clustering")
        report.append("")
        report.append(f"- **{cr.get('dbscan_clusters', 0)} spatial clusters** identified")
        report.append(f"- Statistical significance: p = {sig.get('p_value_clustered', 1):.4f}")

        if sig.get('significant'):
            report.append(f"- **SIGNIFICANT**: Reports cluster more than expected by chance")
        else:
            report.append(f"- Not significant at p<0.05 - clustering may be due to population density")

        # Top clusters
        clusters = cr.get('dbscan_cluster_details', [])[:5]
        if clusters:
            report.append("")
            report.append("**Top Report Clusters:**")
            for i, c in enumerate(clusters):
                report.append(f"  {i+1}. {c['primary_city']}: {c['report_count']} reports ({c['date_range']})")
        report.append("")

    # Correlation results
    if 'correlation_results' in results:
        corr = results['correlation_results']

        report.append("### Feature Correlations")
        report.append("")

        significant = []
        not_significant = []

        for feature, data in corr.items():
            if data.get('significant'):
                significant.append((feature, data))
            else:
                not_significant.append((feature, data))

        if significant:
            report.append("**Significant Correlations Found:**")
            for feature, data in sorted(significant, key=lambda x: x[1]['p_value']):
                direction = data['direction']
                p = data['p_value']
                effect = data['effect_size']
                report.append(f"- **{feature}**: Reports are {direction} than random (p={p:.4f}, d={effect:.2f})")
            report.append("")

        if not_significant:
            report.append("**Not Significant:**")
            for feature, data in not_significant:
                report.append(f"- {feature}: p={data['p_value']:.3f}")
            report.append("")

    # Temporal patterns
    if 'temporal_results' in results:
        temp = results['temporal_results']

        report.append("### Temporal Patterns")
        report.append("")

        # Time of day
        tod = temp.get('time_of_day', {})
        if tod:
            report.append(f"- Night reports: {tod.get('night_ratio', 0):.1%} (expected: 37.5%)")
            if tod.get('uniform_rejected'):
                report.append("  - **SIGNIFICANT**: Non-uniform time distribution")

        # Lunar phase
        lunar = temp.get('lunar_phase', {})
        if lunar:
            report.append(f"- Full moon reports: {lunar.get('full_moon_ratio', 0):.1%} (expected: 25%)")
            if lunar.get('full_moon_enriched'):
                report.append("  - Elevated full moon activity observed")

        # Monthly
        monthly = temp.get('monthly_pattern', {})
        if monthly and monthly.get('seasonal_pattern'):
            peaks = monthly.get('peak_months', [])
            report.append(f"- Seasonal pattern detected: peaks in {', '.join(peaks)}")

        report.append("")

    # Hotspots
    if 'hotspot_results' in results:
        hs = results['hotspot_results']

        report.append("### Convergence Hotspots")
        report.append("")
        report.append(f"- **{hs.get('total_hotspots', 0)} hotspot locations** identified")
        report.append(f"- High convergence (score > 0.6): {hs.get('high_convergence_count', 0)}")
        report.append(f"- Multi-factor hotspots (3+ indicators): {hs.get('multi_factor_count', 0)}")
        report.append("")

        hotspots = hs.get('hotspots', [])[:5]
        if hotspots:
            report.append("**Top Hotspots:**")
            for i, h in enumerate(hotspots):
                report.append(f"  {i+1}. ({h['latitude']:.4f}, {h['longitude']:.4f}) - Score: {h['combined_score']:.3f}")
        report.append("")

    # Data Summary
    report.append("## Data Summary")
    report.append("")
    report.append("### Paranormal Reports by Type")
    for ptype, count in sorted(stats['phenomenon_types'].items(), key=lambda x: -x[1]):
        report.append(f"- {ptype}: {count}")
    report.append("")

    report.append("### Infrastructure Data")
    for itype, count in sorted(stats['infrastructure'].items(), key=lambda x: -x[1]):
        report.append(f"- {itype}: {count}")
    report.append("")

    # Methodology
    report.append("## Methodology")
    report.append("")
    report.append("1. **Spatial Clustering**: DBSCAN and HDBSCAN with haversine distance metric")
    report.append("2. **Feature Correlation**: Permutation testing (n=1000) comparing actual vs random point distributions")
    report.append("3. **Temporal Analysis**: Chi-square tests against uniform distributions")
    report.append("4. **Hotspot Detection**: Multi-layer scoring combining report density and proximity to features")
    report.append("")

    # Limitations
    report.append("## Limitations")
    report.append("")
    report.append("- Population density not fully controlled (reports correlate with where people live)")
    report.append("- Geocoding precision varies (city-level for many reports)")
    report.append("- Historical data incomplete (NUFORC scraping blocked, limited newspaper access)")
    report.append("- Temporal data sparse (many reports lack exact times)")
    report.append("")

    # Conclusions
    report.append("## Conclusions")
    report.append("")

    # Determine which scenario from the spec
    clustering = results.get('clustering_results', {}).get('significance_test', {})
    correlations = results.get('correlation_results', {})

    sig_correlations = [k for k, v in correlations.items() if v.get('significant')]

    if not clustering.get('significant') and not sig_correlations:
        report.append("**Scenario A: Limited Evidence**")
        report.append("")
        report.append("Reports do not show significant clustering beyond population effects, ")
        report.append("and no strong correlations with environmental features were found. ")
        report.append("This suggests paranormal reports may be primarily psychological/cultural phenomena, ")
        report.append("or the dataset is too small/imprecise for detection.")

    elif sig_correlations:
        report.append("**Scenario B: Environmental Correlations Found**")
        report.append("")
        report.append(f"Reports show significant correlation with: **{', '.join(sig_correlations)}**. ")
        report.append("This suggests environmental factors may influence paranormal experiences. ")
        report.append("Recommended: Deploy monitoring equipment at high-correlation locations.")

    report.append("")
    report.append("---")
    report.append("")
    report.append("*Generated by SPECTER - Spatial Paranormal Event Correlation & Terrain Analysis Engine*")

    return '\n'.join(report)

def main():
    print("=" * 60)
    print("SPECTER Executive Summary Generator")
    print("=" * 60)

    # Load analysis results
    print("\nLoading analysis results...")
    results = load_analysis_results()

    # Get database stats
    print("Fetching database statistics...")
    stats = get_database_stats()

    print(f"\nDatabase stats:")
    print(f"  Total reports: {stats['total_reports']}")
    print(f"  Infrastructure points: {sum(stats['infrastructure'].values())}")
    print(f"  Historical events: {stats['historical_events']}")

    # Generate report
    print("\nGenerating executive summary...")
    report = generate_markdown_report(results, stats)

    # Save report
    report_file = os.path.join(OUTPUT_DIR, 'reports', 'SPECTER_Executive_Summary.md')
    os.makedirs(os.path.dirname(report_file), exist_ok=True)

    with open(report_file, 'w') as f:
        f.write(report)

    print(f"\nExecutive summary saved to {report_file}")

    # Also save as JSON for programmatic access
    json_file = os.path.join(OUTPUT_DIR, 'reports', 'summary_data.json')
    summary_data = {
        'stats': stats,
        'results_available': list(results.keys()),
        'generated': datetime.now().isoformat()
    }
    with open(json_file, 'w') as f:
        json.dump(summary_data, f, indent=2, default=str)

    return report_file

if __name__ == "__main__":
    main()
