"""
terrain_correction.py
=====================
Sub-grid terrain speed-up factor for wind resource downscaling.

ERA5 (0.25° ≈ 28 km) and other reanalysis grids assign nearly identical
interpolated wind speeds to all sites within the same grid cell.  Real wind
speeds vary significantly at the sub-grid scale due to:

  * Orographic speed-up on ridges and slowdown in valleys
    (Topographic Position Index, TPI)
  * Elevation-driven increase in free-stream wind speed
    (power-law vertical shear relative to cell-mean elevation)
  * Surface roughness differences
    (land-use roughness correction; optional)

This module computes a **multiplicative speed-up factor** (array of shape
(N,)) that can be applied directly to ERA5-interpolated or synthetic wind
speeds to introduce realistic sub-grid variability.

Usage
-----
::

    from terrain_correction import terrain_speedup_factor

    factor = terrain_speedup_factor(site_lats, site_lons, site_elevs)
    ws_corrected = ws * factor[np.newaxis, :]   # broadcast over time axis

References
----------
* Bowen & Mortensen (2004) – Exploring the limits of WAsP: the wind atlas
  method applied to terrain with steep hills.
* Larsén et al. (2013) – Roughness effects on wind power spectra.
"""

from __future__ import annotations

import numpy as np

# ─── Default parameters ───────────────────────────────────────────────────────
# Radius (degrees) for computing the TPI neighbourhood.
# 0.25° ≈ 28 km matches the ERA5 grid cell size so that the correction
# decorrelates within-cell variation.
DEFAULT_TPI_RADIUS_DEG = 0.25

# Weight of the normalised TPI in the speed-up factor.
# Empirically, a unit-standard-deviation elevation departure translates to
# roughly 10-20% wind speed change over complex terrain (Bowen & Mortensen 2004).
DEFAULT_TPI_SCALE = 0.12

# Wind-shear exponent α for the elevation-based height correction.
# IEC 61400-1 onshore default is 0.14; use 0.20 for complex terrain.
DEFAULT_SHEAR_ALPHA = 0.17

# Hard limits: physically unlikely to see more than ×2 or less than ×0.5
# speedup relative to the ERA5 cell mean in typical terrain.
FACTOR_MIN = 0.55
FACTOR_MAX = 1.80


# ─── Public API ───────────────────────────────────────────────────────────────

def terrain_speedup_factor(
    site_lats: np.ndarray,
    site_lons: np.ndarray,
    site_elevs: np.ndarray,
    tpi_radius_deg: float = DEFAULT_TPI_RADIUS_DEG,
    tpi_scale: float = DEFAULT_TPI_SCALE,
    shear_alpha: float = DEFAULT_SHEAR_ALPHA,
    verbose: bool = False,
) -> np.ndarray:
    """
    Compute a multiplicative terrain speed-up factor for each site.

    Two additive-in-log-space components are multiplied together:

    1. **TPI component** – sites elevated above their neighbourhood (ridges)
       receive a speed-up; sites below (valleys/basins) receive a slowdown.
       The normalised TPI is clamped to [-3, +3] standard deviations to
       prevent extreme corrections for isolated outlier elevations.

    2. **Elevation shear component** – each site's elevation is compared to
       the neighbourhood mean elevation (a proxy for the ERA5 terrain height
       at that grid point), and a power-law shear correction is applied.
       This mimics the ERA5 orographic smoothing: high-resolution terrain
       often rises above the coarse-grid representative elevation.

    Parameters
    ----------
    site_lats, site_lons : 1-D float arrays, length N
        WGS-84 latitude / longitude of each site (degrees).
    site_elevs : 1-D float array, length N
        Terrain elevation at each site (metres above sea level).
    tpi_radius_deg : float
        Neighbourhood search radius for TPI (degrees).  Default 0.25°
        matches a single ERA5 grid cell.
    tpi_scale : float
        Speed-up coefficient per normalised TPI unit.  E.g. 0.12 means a
        site 1σ above its neighbourhood mean gets a +12% speed-up.
    shear_alpha : float
        Power-law shear exponent for elevation relative to cell mean.
    verbose : bool
        Print summary statistics if True.

    Returns
    -------
    factor : float32 ndarray, shape (N,)
        Multiplicative speed-up factor; apply as ``ws *= factor``.
    """
    site_lats = np.asarray(site_lats, dtype=float)
    site_lons = np.asarray(site_lons, dtype=float)
    site_elevs = np.asarray(site_elevs, dtype=float)
    N = len(site_lats)

    mean_elev = np.empty(N)
    std_elev = np.empty(N)

    # ── Compute TPI neighbourhood statistics ──────────────────────────────────
    # For each site, find all sites within a square bounding box of
    # ±tpi_radius_deg.  This is a fast proxy for a circular neighbourhood
    # and avoids an expensive pair-wise distance matrix (O(N²) memory).
    for i in range(N):
        mask = (
            (np.abs(site_lats - site_lats[i]) <= tpi_radius_deg) &
            (np.abs(site_lons - site_lons[i]) <= tpi_radius_deg)
        )
        nbr_elevs = site_elevs[mask]
        mean_elev[i] = nbr_elevs.mean()
        std_elev[i] = nbr_elevs.std() if nbr_elevs.std() > 0 else 1.0

    # ── TPI component ─────────────────────────────────────────────────────────
    # Normalised TPI in units of local standard deviation, clamped to [-3, +3]
    tpi_norm = np.clip(
        (site_elevs - mean_elev) / np.maximum(std_elev, 10.0),
        -3.0, 3.0,
    )
    tpi_factor = 1.0 + tpi_scale * tpi_norm

    # ── Elevation shear component ─────────────────────────────────────────────
    # Ratio of site elevation to neighbourhood mean (proxy for ERA5 grid-cell
    # representative elevation).  Guard against near-zero or negative mean.
    safe_mean = np.maximum(mean_elev, 10.0)
    elev_factor = np.where(
        site_elevs > 0.0,
        (site_elevs / safe_mean) ** shear_alpha,
        1.0,
    )

    factor = (tpi_factor * elev_factor).astype(np.float32)
    factor = np.clip(factor, FACTOR_MIN, FACTOR_MAX)

    if verbose:
        print(
            f"[terrain_correction] N={N}  "
            f"factor: min={factor.min():.3f}  max={factor.max():.3f}  "
            f"mean={factor.mean():.3f}  std={factor.std():.3f}"
        )

    return factor
