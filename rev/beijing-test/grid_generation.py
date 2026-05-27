"""
grid_generation.py
==================
Step 1 – Generate a 4 km² (2 km × 2 km) grid over Beijing from a GeoJSON boundary.

The pipeline:
  1. Load the GeoJSON polygon.
  2. Reproject to equal-area CRS (EPSG:32650 – WGS 84 / UTM zone 50N).
  3. Build a regular 2 000 m × 2 000 m grid covering the bounding box.
  4. Clip grid cells whose **centroid** falls inside the boundary polygon.
  5. Return centroids in WGS-84 lon/lat for downstream use.

Dependencies: geopandas, shapely, numpy
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import MultiPolygon, Point, Polygon, box


# ── CRS constants ──────────────────────────────────────────────────────────────
WGS84 = "EPSG:4326"
UTM50N = "EPSG:32650"   # WGS 84 / UTM zone 50N – covers Beijing, equal-area units in metres

# Default 2 km × 2 km = 4 km² cell
DEFAULT_CELL_M = 2_000


# ── Core functions ─────────────────────────────────────────────────────────────

def load_boundary(geojson_path: str | Path) -> gpd.GeoDataFrame:
    """Load the boundary GeoJSON and return a GeoDataFrame in WGS-84."""
    gdf = gpd.read_file(str(geojson_path))
    if gdf.crs is None:
        gdf = gdf.set_crs(WGS84)
    return gdf.to_crs(WGS84)


def reproject_to_utm(gdf: gpd.GeoDataFrame, crs: str = UTM50N) -> gpd.GeoDataFrame:
    """Reproject a GeoDataFrame to an equal-area CRS (default: UTM zone 50N)."""
    return gdf.to_crs(crs)


def build_grid_cells(
    boundary_utm: gpd.GeoDataFrame,
    cell_size_m: float = DEFAULT_CELL_M,
) -> gpd.GeoDataFrame:
    """
    Build rectangular grid cells covering the bounding box of *boundary_utm*.

    Parameters
    ----------
    boundary_utm : GeoDataFrame
        Boundary in UTM (metres) CRS.
    cell_size_m : float
        Side length of each square cell in metres.

    Returns
    -------
    GeoDataFrame
        Grid cells (Polygon geometries) in the same UTM CRS.
    """
    minx, miny, maxx, maxy = boundary_utm.total_bounds

    # Snap grid origin to a round multiple of cell_size_m for reproducibility.
    origin_x = np.floor(minx / cell_size_m) * cell_size_m
    origin_y = np.floor(miny / cell_size_m) * cell_size_m

    cols = np.arange(origin_x, maxx + cell_size_m, cell_size_m)
    rows = np.arange(origin_y, maxy + cell_size_m, cell_size_m)

    cells = []
    for x0 in cols:
        for y0 in rows:
            cells.append(box(x0, y0, x0 + cell_size_m, y0 + cell_size_m))

    return gpd.GeoDataFrame({"geometry": cells}, crs=boundary_utm.crs)


def clip_grid_to_boundary(
    grid_utm: gpd.GeoDataFrame,
    boundary_utm: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    Keep only grid cells whose **centroid** falls inside the boundary polygon.

    Using centroid containment (instead of intersection) ensures each retained
    cell is uniquely associated with the boundary and avoids tiny slivers at
    edges that would produce unrealistically small resource cells.

    Returns
    -------
    GeoDataFrame with a reset integer index (= resource gid sequence start).
    """
    union_boundary = boundary_utm.geometry.union_all()
    centroids = grid_utm.geometry.centroid
    mask = centroids.within(union_boundary)
    clipped = grid_utm[mask].copy()
    clipped = clipped.reset_index(drop=True)
    return clipped


def extract_site_meta(
    grid_utm: gpd.GeoDataFrame,
    boundary_name: str = "Beijing",
    elevation_fn: Optional[callable] = None,
    dem_tif: Optional[str | Path] = None,
) -> pd.DataFrame:
    """
    Extract site metadata (lat, lon, gid, …) from clipped UTM grid cells.

    Parameters
    ----------
    grid_utm : GeoDataFrame
        Clipped grid in UTM CRS.
    boundary_name : str
        Used to fill 'state' / 'county' metadata fields.
    elevation_fn : callable, optional
        ``elevation_fn(lat, lon) -> float`` (metres).  Ignored when *dem_tif*
        is provided.  When both are *None* the built-in sigmoid approximation
        for Beijing is used.
    dem_tif : path-like, optional
        Path to a GeoTIFF DEM (e.g. SRTM 30 m, Copernicus GLO-30).  When
        provided, site elevations are sampled directly from the raster using
        ``rasterio``; ``elevation_fn`` is ignored.  The DEM must cover the
        study area and may be in any CRS (will be reprojected on the fly).

    Returns
    -------
    DataFrame with columns:
        gid, latitude, longitude, country, state, county,
        timezone, elevation, offshore
    """
    # Compute centroids in WGS-84
    centroids_wgs84 = (
        grid_utm.geometry.centroid
        .to_frame("geometry")
        .set_crs(grid_utm.crs)
        .to_crs(WGS84)
    )

    lons = centroids_wgs84.geometry.x.values
    lats = centroids_wgs84.geometry.y.values
    n = len(lats)

    if dem_tif is not None:
        elevations = sample_dem_elevations(lats, lons, dem_tif)
        print(f"[grid_generation] DEM elevations: "
              f"min={elevations.min():.0f} m  max={elevations.max():.0f} m  "
              f"std={elevations.std():.0f} m  (n={n} sites)")
    else:
        if elevation_fn is None:
            elevation_fn = _default_beijing_elevation
        elevations = np.array([elevation_fn(lats[i], lons[i]) for i in range(n)])

    meta = pd.DataFrame({
        "gid":       np.arange(n, dtype=np.int32),
        "latitude":  lats,
        "longitude": lons,
        "country":   "China",
        "state":     boundary_name,
        "county":    boundary_name,
        "timezone":  8,                   # UTC+8
        "elevation": elevations.astype(np.float32),
        "offshore":  np.zeros(n, dtype=np.uint8),
    })
    return meta


def sample_dem_elevations(
    lats: np.ndarray,
    lons: np.ndarray,
    dem_tif: str | Path,
    nodata_fill: float = 0.0,
) -> np.ndarray:
    """
    Sample terrain elevation (metres) at arbitrary (lat, lon) points from a
    GeoTIFF DEM using bilinear interpolation.

    Supported DEM formats include SRTM 1-arc-second (30 m), SRTM 3-arc-second
    (90 m), Copernicus DEM GLO-30, ASTER GDEM v3, or any single-band GeoTIFF.
    The DEM CRS is detected automatically from the file; coordinates are
    reprojected on the fly if needed.

    Parameters
    ----------
    lats, lons : 1-D float arrays
        WGS-84 latitude / longitude of each sample point.
    dem_tif : path-like
        Path to the DEM GeoTIFF (single band, elevation in metres).
    nodata_fill : float
        Replacement value for no-data pixels (default 0.0).

    Returns
    -------
    elevations : float32 ndarray, shape (N,)
    """
    try:
        import rasterio
        from rasterio.crs import CRS as RioCRS
        from rasterio.warp import transform as rio_transform
    except ImportError as exc:
        raise ImportError(
            "rasterio is required for DEM sampling.  "
            "Install it with: pip install rasterio"
        ) from exc

    dem_tif = Path(dem_tif)
    if not dem_tif.exists():
        raise FileNotFoundError(f"DEM file not found: {dem_tif}")

    with rasterio.open(str(dem_tif)) as src:
        dem_crs = src.crs
        wgs84 = RioCRS.from_epsg(4326)

        # Reproject sample coordinates to DEM CRS if necessary
        if dem_crs != wgs84:
            xs, ys = rio_transform(wgs84, dem_crs,
                                   list(lons.astype(float)),
                                   list(lats.astype(float)))
            xs = np.asarray(xs)
            ys = np.asarray(ys)
        else:
            xs = lons.astype(float)
            ys = lats.astype(float)

        # rasterio.sample expects (col, row) order ↔ (x, y)
        coords = list(zip(xs, ys))
        elevations = np.array(
            [v[0] for v in src.sample(coords, indexes=1)],
            dtype=np.float32,
        )

    # Replace nodata / NaN values
    nodata_mask = ~np.isfinite(elevations)
    if src.nodata is not None:
        nodata_mask |= (elevations == src.nodata)
    elevations[nodata_mask] = nodata_fill

    return elevations


def _default_beijing_elevation(lat: float, lon: float) -> float:
    """
    Approximate terrain elevation (metres) for Beijing based on lat/lon.

    Model: mountains are mainly in the north-west (Yanshan + Taihang foothills).
    A sigmoid function transitions from plains (~50 m) to mountains (~1 200 m).
    This is a synthetic stand-in; replace with a real DEM GeoTIFF in production
    (pass dem_tif to generate_grid / extract_site_meta).
    """
    # Latitude: above ~40.5°N starts rising toward the mountains
    lat_factor = 1 / (1 + np.exp(-4 * (lat - 40.5)))
    # Longitude: west of ~116° is more mountainous
    lon_factor = 1 / (1 + np.exp(3 * (lon - 116.5)))
    elev = 50 + 1150 * lat_factor * lon_factor
    return float(elev)


# ── Output helpers ─────────────────────────────────────────────────────────────

def save_grid_geojson(
    grid_utm: gpd.GeoDataFrame,
    output_path: str | Path,
) -> Path:
    """Save the UTM grid cells to a GeoJSON file (reprojected to WGS-84)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    grid_wgs84 = grid_utm.to_crs(WGS84)
    grid_wgs84.to_file(str(output_path), driver="GeoJSON")
    return output_path


def save_site_meta_csv(meta: pd.DataFrame, output_path: str | Path) -> Path:
    """Save site metadata to CSV (for inspection / downstream use)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    meta.to_csv(str(output_path), index=False)
    return output_path


# ── Top-level pipeline entry point ────────────────────────────────────────────

def generate_grid(
    geojson_path: str | Path,
    output_dir: str | Path,
    cell_size_m: float = DEFAULT_CELL_M,
    boundary_name: str = "Beijing",
    dem_tif: Optional[str | Path] = None,
) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """
    Full grid-generation pipeline.

    Parameters
    ----------
    geojson_path : path-like
        Path to the boundary GeoJSON file.
    output_dir : path-like
        Directory where ``grid_cells.geojson`` and ``site_meta.csv`` are written.
    cell_size_m : float
        Grid cell side length in metres (default 2 000 → 4 km²).
    boundary_name : str
        Region name embedded in the metadata.
    dem_tif : path-like, optional
        Path to a single-band DEM GeoTIFF for real elevation sampling.
        When *None*, a synthetic sigmoid model for Beijing terrain is used.

    Returns
    -------
    grid_utm : GeoDataFrame
        Clipped grid cells in UTM CRS.
    site_meta : DataFrame
        Per-site metadata table (gid, lat, lon, …).
    """
    output_dir = Path(output_dir)

    boundary_wgs84 = load_boundary(geojson_path)
    boundary_utm = reproject_to_utm(boundary_wgs84)
    grid_utm = build_grid_cells(boundary_utm, cell_size_m=cell_size_m)
    grid_utm = clip_grid_to_boundary(grid_utm, boundary_utm)
    site_meta = extract_site_meta(grid_utm, boundary_name=boundary_name,
                                  dem_tif=dem_tif)

    # Add gid to grid GeoDataFrame for QGIS inspection
    grid_utm = grid_utm.copy()
    grid_utm["gid"] = site_meta["gid"].values
    grid_utm["latitude"] = site_meta["latitude"].values
    grid_utm["longitude"] = site_meta["longitude"].values
    grid_utm["elevation"] = site_meta["elevation"].values

    save_grid_geojson(grid_utm, output_dir / "grid_cells.geojson")
    save_site_meta_csv(site_meta, output_dir / "site_meta.csv")

    print(f"[grid_generation] {len(site_meta)} sites generated")
    print(f"  Cell size  : {cell_size_m / 1000:.1f} km × {cell_size_m / 1000:.1f} km")
    print(f"  Lat range  : {site_meta['latitude'].min():.4f} – {site_meta['latitude'].max():.4f}")
    print(f"  Lon range  : {site_meta['longitude'].min():.4f} – {site_meta['longitude'].max():.4f}")
    print(f"  Saved to   : {output_dir}")

    return grid_utm, site_meta


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate 4 km² grid from a GeoJSON boundary."
    )
    parser.add_argument("geojson", help="Path to the boundary GeoJSON file.")
    parser.add_argument(
        "--output-dir", default="./output", help="Output directory (default: ./output)"
    )
    parser.add_argument(
        "--cell-size", type=float, default=2000,
        help="Grid cell side length in metres (default: 2000)"
    )
    parser.add_argument(
        "--name", default="Beijing",
        help="Region name for metadata (default: Beijing)"
    )
    args = parser.parse_args()

    generate_grid(args.geojson, args.output_dir, args.cell_size, args.name)
