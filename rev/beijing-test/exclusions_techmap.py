"""
exclusions_techmap.py
=====================
Step 5 – Build a reV-compatible exclusions HDF5 and techmap dataset.

The default path is OSM-driven exclusions synthesized from a Beijing .osm.pbf
file. Excluded areas are inferred from common siting constraints:

- built-up landuse polygons (residential/commercial/industrial/...)
- water/wetland polygons
- protected-area polygons
- buffered transport corridors (highway/railway/aeroway)

When no OSM file is provided (or no valid features are found), the module
falls back to a placeholder exclusion layer where all cells are included.

The raster is aligned to the same WGS-84 bounding box as the site grid,
at a configurable pixel resolution (default 500 m, matching WTK techmap
conventions – each resource cell covers ~4 pixels per side for a 2 km grid).

You can still replace this logic with project-specific exclusion rasters by
customizing ``build_exclusion_layer()``.

HDF5 output schema
------------------
  /latitude   – float64 (rows, cols)  – pixel centre latitudes
  /longitude  – float64 (rows, cols)  – pixel centre longitudes
  /<excl_key> – uint8   (1, rows, cols) – 0 = excluded, 100 = fully included
  /<tm_key>   – int32   (rows, cols)  – resource gid (-1 = no data)
    attrs:
      distance_threshold  – float
      src_res_fpath       – str
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Optional

import h5py
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree
from shapely import contains_xy, make_valid, unary_union


# ─── Defaults ─────────────────────────────────────────────────────────────────
DEFAULT_PIXEL_M = 500        # exclusion raster pixel size in metres
DEFAULT_EXCL_KEY = "beijing_osm_exclusions"
DEFAULT_TM_KEY = "techmap_beijing"
SLOPE_EXCL_KEY = "slope_exclusion"
ELEV_EXCL_KEY = "elevation_exclusion"
UTM50N_EPSG = "EPSG:32650"

# Wind turbine siting thresholds (commonly used in Chinese wind energy planning)
SLOPE_THRESHOLD_DEG = 30.0   # steeper than this → excluded (°)
ELEV_THRESHOLD_M = 3000.0    # above this → excluded (m) — Beijing max ~2300 m

DEFAULT_OSM_POLYGON_LAYERS = {
    "landuse": {"residential", "industrial", "commercial", "retail", "construction"},
    "natural": {"water", "wetland"},
    "boundary": {"protected_area"},
}

DEFAULT_BUFFER_M = {
    "major_highway": 120.0,
    "minor_highway": 45.0,
    "railway": 80.0,
    "aeroway": 150.0,
}


# ─── Grid helpers ─────────────────────────────────────────────────────────────

def _build_pixel_grid(
    site_meta: pd.DataFrame,
    pixel_m: float,
    padding_m: float = 4_000,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Build a regular pixel grid in WGS-84 that covers all sites with padding.

    Grid construction and distance calculations are done in UTM-50N metres,
    then transformed back to latitude/longitude for HDF5 output.

    Returns
    -------
    lat_grid, lon_grid, x_grid, y_grid : 2D float64 arrays of shape (rows, cols)
    """
    lonlat_to_utm = Transformer.from_crs("EPSG:4326", UTM50N_EPSG, always_xy=True)
    utm_to_lonlat = Transformer.from_crs(UTM50N_EPSG, "EPSG:4326", always_xy=True)

    site_lons = site_meta["longitude"].to_numpy(dtype=float)
    site_lats = site_meta["latitude"].to_numpy(dtype=float)
    site_x, site_y = lonlat_to_utm.transform(site_lons, site_lats)

    minx, miny = float(np.min(site_x)), float(np.min(site_y))
    maxx, maxy = float(np.max(site_x)), float(np.max(site_y))
    minx -= padding_m
    miny -= padding_m
    maxx += padding_m
    maxy += padding_m

    xs = np.arange(minx + pixel_m / 2, maxx, pixel_m)
    ys = np.arange(miny + pixel_m / 2, maxy, pixel_m)
    xx, yy = np.meshgrid(xs, ys)

    flat_lons, flat_lats = utm_to_lonlat.transform(xx.ravel(), yy.ravel())
    lons = np.asarray(flat_lons, dtype=np.float64).reshape(xx.shape)
    lats = np.asarray(flat_lats, dtype=np.float64).reshape(xx.shape)
    return lats, lons, xx.astype(np.float64), yy.astype(np.float64)


# ─── Exclusion layer builder ──────────────────────────────────────────────────

def build_exclusion_layer(
    lat_grid: np.ndarray,
    lon_grid: np.ndarray,
    x_grid: np.ndarray,
    y_grid: np.ndarray,
    osm_pbf: Optional[str | Path] = None,
) -> np.ndarray:
    """
    Build a uint8 exclusion raster of shape (1, rows, cols).

    Convention (matches reV):
      0   – fully excluded
      100 – fully included

    If *osm_pbf* is not provided or no valid features are found, this
    function falls back to the previous placeholder behavior (all included).
    """
    import geopandas as gpd

    rows, cols = lat_grid.shape
    excl = np.full((1, rows, cols), 100, dtype=np.uint8)

    if osm_pbf is None:
        return excl

    osm_pbf = Path(osm_pbf)
    if not osm_pbf.exists():
        warnings.warn(
            f"OSM PBF not found: {osm_pbf}; using placeholder exclusions.",
            stacklevel=3,
        )
        return excl

    bbox = (
        float(np.min(lon_grid)),
        float(np.min(lat_grid)),
        float(np.max(lon_grid)),
        float(np.max(lat_grid)),
    )

    polygon_cols = ["landuse", "natural", "water", "boundary", "aeroway", "geometry"]
    line_cols = ["highway", "railway", "aeroway", "geometry"]

    try:
        # Some OSM extracts contain occasional unclosed polygon rings.
        # GDAL/pyogrio can still read them, but emits a noisy RuntimeWarning.
        # We silence only this known warning and clean geometries downstream.
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"Non closed ring detected.*",
                category=RuntimeWarning,
            )
            polys = gpd.read_file(
                str(osm_pbf),
                layer="multipolygons",
                bbox=bbox,
                columns=polygon_cols,
                engine="pyogrio",
            )
            lines = gpd.read_file(
                str(osm_pbf),
                layer="lines",
                bbox=bbox,
                columns=line_cols,
                engine="pyogrio",
            )
    except Exception as exc:
        warnings.warn(
            f"Failed to read OSM PBF ({exc}); using placeholder exclusions.",
            stacklevel=3,
        )
        return excl

    geoms = []

    def _clean_geom_list(geom_iterable):
        cleaned = []
        for g in geom_iterable:
            if g is None or g.is_empty:
                continue
            try:
                g2 = make_valid(g)
            except Exception:
                continue
            if g2 is not None and not g2.is_empty:
                cleaned.append(g2)
        return cleaned

    if not polys.empty:
        # Built-up / water / protected areas are excluded by default.
        landuse = polys.get("landuse", pd.Series(index=polys.index, dtype=object)).fillna("")
        natural = polys.get("natural", pd.Series(index=polys.index, dtype=object)).fillna("")
        water = polys.get("water", pd.Series(index=polys.index, dtype=object)).fillna("")
        boundary = polys.get("boundary", pd.Series(index=polys.index, dtype=object)).fillna("")
        aeroway = polys.get("aeroway", pd.Series(index=polys.index, dtype=object)).fillna("")

        poly_mask = (
            landuse.isin(DEFAULT_OSM_POLYGON_LAYERS["landuse"])
            | natural.isin(DEFAULT_OSM_POLYGON_LAYERS["natural"])
            | water.ne("")
            | boundary.isin(DEFAULT_OSM_POLYGON_LAYERS["boundary"])
            | aeroway.ne("")
        )
        selected_polys = polys.loc[poly_mask]
        if not selected_polys.empty:
            selected_polys = selected_polys.to_crs(UTM50N_EPSG)
            geoms.extend(_clean_geom_list(selected_polys.geometry))

    if not lines.empty:
        lines = lines.to_crs(UTM50N_EPSG)
        highway = lines.get("highway", pd.Series(index=lines.index, dtype=object)).fillna("")
        railway = lines.get("railway", pd.Series(index=lines.index, dtype=object)).fillna("")
        aeroway = lines.get("aeroway", pd.Series(index=lines.index, dtype=object)).fillna("")

        major_hwy = lines.loc[highway.isin({"motorway", "trunk", "primary"})]
        minor_hwy = lines.loc[highway.ne("") & ~highway.isin({"motorway", "trunk", "primary"})]
        rail = lines.loc[railway.ne("")]
        air = lines.loc[aeroway.ne("")]

        for subset, dist in (
            (major_hwy, DEFAULT_BUFFER_M["major_highway"]),
            (minor_hwy, DEFAULT_BUFFER_M["minor_highway"]),
            (rail, DEFAULT_BUFFER_M["railway"]),
            (air, DEFAULT_BUFFER_M["aeroway"]),
        ):
            if not subset.empty:
                geoms.extend(_clean_geom_list(subset.geometry.buffer(dist)))

    if not geoms:
        warnings.warn(
            "No OSM features matched exclusion rules; using placeholder exclusions.",
            stacklevel=3,
        )
        return excl

    exclusion_geom = make_valid(unary_union(geoms))
    if exclusion_geom.is_empty:
        return excl

    excluded = contains_xy(exclusion_geom, x_grid.ravel(), y_grid.ravel())
    excl.reshape(-1)[excluded] = 0
    return excl


def build_techmap(
    x_grid: np.ndarray,
    y_grid: np.ndarray,
    site_meta: pd.DataFrame,
    distance_threshold_m: float = 6_000.0,
) -> tuple[np.ndarray, float]:
    """
    Build a techmap (int32) of shape (rows, cols) mapping each raster pixel
    to its nearest resource gid.

    Pixels farther than *distance_threshold_m* from all sites are set to -1.

    Parameters
    ----------
    x_grid, y_grid : 2D arrays in UTM metres
    site_meta : DataFrame with latitude, longitude, gid columns
    distance_threshold_m : float
        Pixels beyond this distance in metres from the nearest site get gid
        = -1. Default 6000 m.

    Returns
    -------
    techmap : int32 (rows, cols)
    actual_threshold : float  (stored as HDF5 attribute)
    """
    lonlat_to_utm = Transformer.from_crs("EPSG:4326", UTM50N_EPSG, always_xy=True)

    rows, cols = x_grid.shape

    site_lons = site_meta["longitude"].to_numpy(dtype=float)
    site_lats = site_meta["latitude"].to_numpy(dtype=float)
    site_x, site_y = lonlat_to_utm.transform(site_lons, site_lats)
    gids = site_meta["gid"].values if "gid" in site_meta.columns else np.arange(len(site_meta))

    # Build KD-tree in UTM metres for better distance behavior.
    tree = cKDTree(np.column_stack([site_x, site_y]))

    pixel_coords = np.column_stack([x_grid.ravel(), y_grid.ravel()])
    dists, idxs = tree.query(pixel_coords, workers=-1)

    techmap = gids[idxs].astype(np.int32)
    techmap[dists > distance_threshold_m] = -1

    techmap = techmap.reshape(rows, cols)

    # Compute a representative threshold for the attrs (mean nearest-site dist)
    near = dists[dists < distance_threshold_m]
    actual_threshold = float(np.median(near)) if len(near) else distance_threshold_m
    return techmap, actual_threshold


# ─── Writer ───────────────────────────────────────────────────────────────────

# ─── Terrain exclusion layers ─────────────────────────────────────────────────

def build_terrain_exclusion_layers(
    lat_grid: np.ndarray,
    lon_grid: np.ndarray,
    x_grid: np.ndarray,
    y_grid: np.ndarray,
    dem_tif: str | Path,
    slope_threshold_deg: float = SLOPE_THRESHOLD_DEG,
    elev_threshold_m: float = ELEV_THRESHOLD_M,
) -> dict[str, np.ndarray]:
    """
    Build slope- and elevation-based exclusion rasters from a DEM GeoTIFF.

    Terrain factors commonly used in Chinese wind energy siting:

    * **Slope exclusion** – pixels with terrain slope > *slope_threshold_deg*
      (default 30°) are excluded.  Steep terrain increases civil/logistics
      costs and complicates turbine foundations.

    * **Elevation exclusion** – pixels above *elev_threshold_m* (default
      3 000 m) are excluded.  Beijing's highest peaks are ~2 300 m; a 3 000 m
      ceiling keeps the threshold non-binding for plains while still excluding
      extreme altitudes in other regions.

    Methodology
    -----------
    1. Resample the DEM to the exclusion raster pixel grid (bilinear, via
       ``rasterio.warp.reproject``).
    2. Compute slope in degrees from the resampled UTM-grid DEM using
       central-difference finite differences over the pixel spacing.
    3. Threshold each component; encode as uint8 (0 = excluded, 100 = included)
       matching reV exclusion conventions.

    Parameters
    ----------
    lat_grid, lon_grid : 2-D float64 arrays
        Pixel centre coordinates in WGS-84.
    x_grid, y_grid : 2-D float64 arrays
        Pixel centre coordinates in UTM metres (EPSG:32650).
    dem_tif : path-like
        Single-band DEM GeoTIFF (elevation in metres).
    slope_threshold_deg : float
        Maximum allowed slope in degrees.
    elev_threshold_m : float
        Maximum allowed elevation in metres.

    Returns
    -------
    dict with keys:
        ``slope_exclusion``     : uint8 (1, rows, cols)
        ``elevation_exclusion`` : uint8 (1, rows, cols)
    """
    try:
        import rasterio
        from rasterio.crs import CRS as RioCRS
        from rasterio.transform import from_bounds
        from rasterio.warp import reproject as rio_reproject
        from rasterio.warp import Resampling
    except ImportError as exc:
        raise ImportError(
            "rasterio is required for terrain exclusion layers.  "
            "Install it with: pip install rasterio"
        ) from exc

    dem_tif = Path(dem_tif)
    if not dem_tif.exists():
        raise FileNotFoundError(f"DEM file not found: {dem_tif}")

    rows, cols = lat_grid.shape
    utm_crs = RioCRS.from_epsg(32650)

    # ── Build target affine transform for the exclusion pixel grid ────────────
    pixel_w = float(x_grid[0, 1] - x_grid[0, 0]) if cols > 1 else 500.0
    pixel_h = float(y_grid[1, 0] - y_grid[0, 0]) if rows > 1 else 500.0
    left   = float(x_grid[0, 0]) - pixel_w / 2
    bottom = float(y_grid[0, 0]) - abs(pixel_h) / 2
    right  = float(x_grid[0, -1]) + pixel_w / 2
    top    = float(y_grid[-1, 0]) + abs(pixel_h) / 2

    dst_transform = from_bounds(left, bottom, right, top, cols, rows)

    # ── Resample DEM to exclusion grid in UTM ─────────────────────────────────
    dem_utm = np.empty((rows, cols), dtype=np.float32)
    with rasterio.open(str(dem_tif)) as src:
        rio_reproject(
            source=rasterio.band(src, 1),
            destination=dem_utm,
            dst_transform=dst_transform,
            dst_crs=utm_crs,
            resampling=Resampling.bilinear,
        )
    # Fill any no-data holes with the median (conservative)
    nodata_mask = ~np.isfinite(dem_utm)
    if nodata_mask.any():
        dem_utm[nodata_mask] = float(np.nanmedian(dem_utm))

    # ── Slope calculation (central-difference finite differences) ─────────────
    # dz/dx and dz/dy in metres; pixel spacing already in metres (UTM)
    dzdx = np.gradient(dem_utm, pixel_w, axis=1)
    dzdy = np.gradient(dem_utm, abs(pixel_h), axis=0)
    slope_rad = np.arctan(np.sqrt(dzdx ** 2 + dzdy ** 2))
    slope_deg = np.degrees(slope_rad)

    # ── Encode as reV uint8 exclusions (0=excluded, 100=included) ─────────────
    slope_excl = np.where(slope_deg > slope_threshold_deg, 0, 100).astype(np.uint8)
    elev_excl  = np.where(dem_utm   > elev_threshold_m,   0, 100).astype(np.uint8)

    n_slope_excl = int((slope_excl == 0).sum())
    n_elev_excl  = int((elev_excl  == 0).sum())
    total_px = rows * cols
    print(f"[exclusions_techmap] Terrain layers ({rows}×{cols} pixels):")
    print(f"  Slope  >  {slope_threshold_deg}°  excluded: {n_slope_excl} px "
          f"({100 * n_slope_excl / total_px:.1f}%)")
    print(f"  Elevation > {elev_threshold_m:.0f} m  excluded: {n_elev_excl} px "
          f"({100 * n_elev_excl / total_px:.1f}%)")

    return {
        SLOPE_EXCL_KEY: slope_excl[np.newaxis, :, :],
        ELEV_EXCL_KEY:  elev_excl[np.newaxis, :, :],
    }


# ─── Writer ───────────────────────────────────────────────────────────────────

def write_exclusions_h5(
    output_path: str | Path,
    lat_grid: np.ndarray,
    lon_grid: np.ndarray,
    excl_layer: np.ndarray,
    techmap: np.ndarray,
    distance_threshold: float,
    resource_fpath: str,
    excl_key: str = DEFAULT_EXCL_KEY,
    tm_key: str = DEFAULT_TM_KEY,
    extra_layers: Optional[dict[str, np.ndarray]] = None,
    overwrite: bool = False,
) -> Path:
    """Write the exclusions + techmap HDF5 file.

    Parameters
    ----------
    extra_layers : dict, optional
        Additional uint8 datasets to embed, keyed by dataset name.
        Use this to pass terrain layers (``slope_exclusion``,
        ``elevation_exclusion``) produced by
        :func:`build_terrain_exclusion_layers`.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"{output_path} exists. Pass overwrite=True to replace."
        )

    rows, cols = lat_grid.shape
    print(f"[exclusions_techmap] Writing {output_path} …")
    print(f"  Raster size     : {rows} × {cols} pixels")
    print(f"  Excl key        : {excl_key}")
    print(f"  Techmap key     : {tm_key}")
    if extra_layers:
        print(f"  Extra layers    : {list(extra_layers.keys())}")

    with h5py.File(str(output_path), "w") as f:
        f.create_dataset("latitude", data=lat_grid,
                         compression="gzip", compression_opts=4)
        f.create_dataset("longitude", data=lon_grid,
                         compression="gzip", compression_opts=4)
        f.create_dataset(excl_key, data=excl_layer,
                         compression="gzip", compression_opts=4)
        if extra_layers:
            for layer_name, layer_data in extra_layers.items():
                ds = f.create_dataset(layer_name, data=layer_data,
                                      compression="gzip", compression_opts=4)
                ds.attrs["no_go_threshold"] = 0
                ds.attrs["description"] = layer_name.replace("_", " ").title()
        tm_ds = f.create_dataset(tm_key, data=techmap,
                                  compression="gzip", compression_opts=4)
        tm_ds.attrs["distance_threshold"] = distance_threshold
        tm_ds.attrs["src_res_fpath"] = str(resource_fpath)

    file_mb = output_path.stat().st_size / 1_048_576
    print(f"  Done. File size : {file_mb:.1f} MB → {output_path}")
    return output_path


# ─── Top-level pipeline entry point ──────────────────────────────────────────

def build_exclusions_and_techmap(
    site_meta: pd.DataFrame,
    resource_fpath: str | Path,
    output_dir: str | Path,
    osm_pbf: Optional[str | Path] = None,
    dem_tif: Optional[str | Path] = None,
    slope_threshold_deg: float = SLOPE_THRESHOLD_DEG,
    elev_threshold_m: float = ELEV_THRESHOLD_M,
    pixel_m: float = DEFAULT_PIXEL_M,
    excl_key: str = DEFAULT_EXCL_KEY,
    tm_key: str = DEFAULT_TM_KEY,
    overwrite: bool = False,
) -> Path:
    """
    Full pipeline: build raster grid, exclusion layer, techmap, and write HDF5.

    Parameters
    ----------
    site_meta : DataFrame
    resource_fpath : path-like
        Path to the wind resource HDF5 (stored in techmap attrs).
    output_dir : path-like
        Directory for the output ``beijing_exclusions.h5`` file.
    osm_pbf : path-like, optional
        OSM .pbf used to synthesize exclusions from polygons/lines.
    dem_tif : path-like, optional
        Single-band DEM GeoTIFF (elevation in metres).  When provided, two
        additional exclusion layers are added to the HDF5:

        * ``slope_exclusion``     – pixels with slope > *slope_threshold_deg*
          are excluded (value = 0); others get value = 100.
        * ``elevation_exclusion`` – pixels above *elev_threshold_m* are
          excluded.

        Both layers follow the reV convention (uint8, shape ``(1, rows, cols)``).
    slope_threshold_deg : float
        Slope exclusion threshold in degrees (default 30°).
    elev_threshold_m : float
        Elevation exclusion ceiling in metres (default 3 000 m).
    pixel_m : float
        Exclusion raster pixel size in metres.
    excl_key : str
        Dataset name for the OSM exclusion layer inside the HDF5.
    tm_key : str
        Dataset name for the techmap inside the HDF5.
    overwrite : bool

    Returns
    -------
    Path to the written HDF5 file.
    """
    output_path = Path(output_dir) / "beijing_exclusions.h5"

    lat_grid, lon_grid, x_grid, y_grid = _build_pixel_grid(site_meta, pixel_m)
    excl_layer = build_exclusion_layer(lat_grid, lon_grid, x_grid, y_grid, osm_pbf=osm_pbf)
    techmap, dist_thresh = build_techmap(x_grid, y_grid, site_meta)

    # ── Terrain exclusion layers (optional) ───────────────────────────────────
    extra_layers: Optional[dict] = None
    if dem_tif is not None:
        print(f"[exclusions_techmap] Building terrain exclusion layers from DEM: {dem_tif}")
        extra_layers = build_terrain_exclusion_layers(
            lat_grid, lon_grid, x_grid, y_grid,
            dem_tif=dem_tif,
            slope_threshold_deg=slope_threshold_deg,
            elev_threshold_m=elev_threshold_m,
        )
    else:
        print("[exclusions_techmap] No DEM provided; skipping terrain exclusion layers.")

    write_exclusions_h5(
        output_path,
        lat_grid, lon_grid,
        excl_layer, techmap,
        distance_threshold=dist_thresh,
        resource_fpath=str(resource_fpath),
        excl_key=excl_key,
        tm_key=tm_key,
        extra_layers=extra_layers,
        overwrite=overwrite,
    )
    return output_path


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Build Beijing exclusions + techmap HDF5."
    )
    parser.add_argument("site_meta_csv",   help="CSV from grid_generation.py")
    parser.add_argument("resource_h5",     help="Wind resource HDF5 path")
    parser.add_argument("--output-dir",    default="./output")
    parser.add_argument("--osm-pbf",       default=None,
                        help="Optional OSM .pbf file used to synthesize exclusions.")
    parser.add_argument("--dem-tif",       default=None,
                        help="Optional DEM GeoTIFF for slope/elevation exclusion layers.")
    parser.add_argument("--slope-threshold", type=float, default=SLOPE_THRESHOLD_DEG,
                        help=f"Slope exclusion threshold in degrees (default {SLOPE_THRESHOLD_DEG}).")
    parser.add_argument("--elev-threshold",  type=float, default=ELEV_THRESHOLD_M,
                        help=f"Elevation exclusion ceiling in metres (default {ELEV_THRESHOLD_M}).")
    parser.add_argument("--pixel-m",       type=float, default=500)
    parser.add_argument("--excl-key",      default=DEFAULT_EXCL_KEY)
    parser.add_argument("--tm-key",        default=DEFAULT_TM_KEY)
    parser.add_argument("--overwrite",     action="store_true")
    args = parser.parse_args()

    meta = pd.read_csv(args.site_meta_csv)
    build_exclusions_and_techmap(
        meta, args.resource_h5, args.output_dir,
        osm_pbf=args.osm_pbf,
        dem_tif=args.dem_tif,
        slope_threshold_deg=args.slope_threshold,
        elev_threshold_m=args.elev_threshold,
        pixel_m=args.pixel_m,
        excl_key=args.excl_key,
        tm_key=args.tm_key,
        overwrite=args.overwrite,
    )
