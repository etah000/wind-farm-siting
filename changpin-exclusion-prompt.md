## Plan: Changpin OSM Exclusion and Multi-Polygon Layout Optimization

TL;DR: 修改 `wind/scripts/changpin_gridded_layout_optimization.py`，使其自动从 `data/beijing-260416.osm.pbf` 提取不适宜区域并从 `data/changpin.geojson` 定义的边界中扣除这些区域，然后将清理后的允许区域（可能由多个多边形组成）传给 `LayoutOptimizationGridded`。

**Steps**
1. Update `wind/scripts/changpin_gridded_layout_optimization.py` imports: add `shapely.geometry.shape`, `shapely.geometry.Point`, `shapely.ops.unary_union`, `shapely.ops.polygonize`, `pyproj.Transformer`, and conditional `osmium` / `osgeo` support.
2. Add helper functions in `changpin_gridded_layout_optimization.py`:
   - `load_geojson_boundary(path)`: load all GeoJSON features and return a shapely boundary geometry.
   - `get_utm_transformer(geometry)`: determine UTM zone by the boundary centroid and create a `pyproj` transformer.
   - `extract_osm_exclusion_geometry(pbf_path)`: parse the OSM PBF to collect polygons/multipolygons with unsuitable tags such as `landuse=residential`, `landuse=industrial`, `landuse=commercial`, `amenity=school`, `building=school`, `building=industrial`, and possibly `building=residential`.
   - `slice_holes_to_polygons(geometry)`: convert a shapely Polygon/MultiPolygon with interior rings into a list of hole-free polygons using `polygonize` on exterior and interior boundaries.
   - `geometry_to_floris_boundaries(geometry, transformer)`: transform shapely polygons into FLORIS coordinate lists.
3. In the script main flow:
   - Load `data/changpin.geojson` boundary geometry.
   - Load `data/beijing-260416.osm.pbf` and extract unsuitable area geometry.
   - Clip exclusions to the boundary with `intersection` and compute `allowed_area = boundary - exclusions`.
   - Convert `allowed_area` into a list of FLORIS-compatible polygon boundaries.
   - Use that list as `boundaries` in `LayoutOptimizationGridded`.
4. Update printing/logging and plotting to support multiple polygons:
   - Print number of allowed polygons and total vertices.
   - Plot each allowed polygon outline.
   - Optionally plot excluded areas in a different color for verification.
5. Update export metadata to include `allowed_polygon_count`, `exclude_area_m2`, and `boundary_type`.

**Relevant files**
- `wind/scripts/changpin_gridded_layout_optimization.py` — main modification target.

**Verification**
1. Run `wind/scripts/changpin_gridded_layout_optimization.py` after modifications.
2. Confirm the script loads `data/changpin.geojson` and `data/beijing-260416.osm.pbf`, prints allowed polygon counts, and successfully runs `LayoutOptimizationGridded`.
3. Verify the plot shows the allowed area and turbine positions.
4. Check the exported `changpin_optimization_results.json` metadata for polygon counts and coordinate extents.

**Decisions**
- The script will perform automatic OSM-based exclusion using the PBF file rather than relying only on a pre-cleaned GeoJSON.
- The cleaned allowed region will be represented as multiple separate polygons because FLORIS gridded optimization supports disjoint regions but does not support holes directly.

**Further Considerations**
1. If `osmium` is unavailable, implement a fallback using `osgeo.ogr`.
2. If the exclusion difference produces polygons with holes, convert those into hole-free polygons before passing them to FLORIS.
3. Keep the original `convert_geojson_for_floris.py` logic untouched unless reuse is needed later.