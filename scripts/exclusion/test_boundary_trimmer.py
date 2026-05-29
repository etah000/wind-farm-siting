#!/usr/bin/env python3
"""Test for boundary_trimmer: loads changpin.geojson and beijing-260416.osm.pbf,
prints area before/after trimming and saves a before/after figure.
"""
from pathlib import Path
import sys
import matplotlib.pyplot as plt

from scripts.exclusion.boundary_trimmer import get_allowed_area, plot_shapely_geometry


def main():
    geojson_file = Path(__file__).parent.parent / "data" / "changpin.geojson"
    osm_file = Path(__file__).parent.parent / "data" / "beijing-260416.osm.pbf"

    if not geojson_file.exists():
        print(f"GeoJSON not found: {geojson_file}")
        sys.exit(1)
    if not osm_file.exists():
        print(f"OSM PBF not found: {osm_file}")
        sys.exit(1)

    try:
        boundary_utm, exclusions_utm, allowed_area, allowed_boundaries, target_crs = get_allowed_area(
            geojson_file, osm_file
        )
    except Exception as e:
        print("Error computing allowed area:", e)
        sys.exit(1)

    print(f"Target CRS: {target_crs}")
    print(f"Boundary area (m^2): {boundary_utm.area:.2f}")
    print(f"Exclusions area (m^2): {exclusions_utm.area:.2f}")
    print(f"Allowed area (m^2): {allowed_area.area:.2f}")
    print(f"Allowed polygons: {len(allowed_boundaries)}")

    # Plot before / after
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(14, 7))
    plot_shapely_geometry(ax0, boundary_utm, edge_color='blue', linewidth=2)
    if not exclusions_utm.is_empty:
        plot_shapely_geometry(ax0, exclusions_utm, edge_color='red', linewidth=1)
    ax0.set_title('Before trimming: blue boundary, red exclusions')
    ax0.axis('equal')

    plot_shapely_geometry(ax1, allowed_area, edge_color='gray', linewidth=2)
    ax1.set_title('After trimming: allowed area (gray)')
    ax1.axis('equal')

    plt.tight_layout()
    out = Path(__file__).parent / 'trimmer_test.png'
    fig.savefig(out, dpi=200)
    print(f"Saved figure to: {out}")
    plt.show()


if __name__ == '__main__':
    main()
