"""Boundary trimming utilities for FLORIS layout optimization.

This module isolates the region trimming logic so it can be tested and
reused independently from the optimization script.
"""

import json
from pathlib import Path

try:
    from pyproj import Transformer
    PYPROJ_AVAILABLE = True
except ImportError:
    PYPROJ_AVAILABLE = False

try:
    from shapely.geometry import shape, Polygon, MultiPolygon, GeometryCollection
    from shapely.ops import unary_union, transform as shapely_transform
    from shapely import wkb as shapely_wkb
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

try:
    import osmium
    OSMIUM_AVAILABLE = True
except ImportError:
    OSMIUM_AVAILABLE = False

try:
    from osgeo import ogr
    OGR_AVAILABLE = True
except ImportError:
    OGR_AVAILABLE = False

if not PYPROJ_AVAILABLE or not SHAPELY_AVAILABLE:
    raise ImportError('boundary_trimmer requires pyproj and shapely')

EXCLUSION_LANDUSE = {
    'residential',
    'industrial',
    'commercial',
    'retail',
    'construction',
}

EXCLUSION_AMENITY = {
    'school',
    'college',
    'university',
    'kindergarten',
    'childcare',
    'clinic',
    'hospital',
    'library',
}

EXCLUSION_BUILDING = {
    'school',
    'industrial',
    'commercial',
    'residential',
    'retail',
    'apartments',
    'house',
}

# Natural / typically uninhabited landuses to consider (e.g., water, forest)
EXCLUSION_NATURAL = {
    'water',
    'wetland',
    'forest',
    'quarry',
    'farmland',
    'grass',
    'scrub',
}


def load_geojson_boundary(geojson_path: Path):
    """Load GeoJSON boundary geometry as a Shapely object."""
    with open(geojson_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if data.get('type') == 'FeatureCollection':
        geoms = [shape(feature['geometry']) for feature in data.get('features', []) if feature.get('geometry')]
    elif data.get('type') in {'Feature', 'Polygon', 'MultiPolygon'}:
        geometry = data.get('geometry') if data.get('type') == 'Feature' else data
        geoms = [shape(geometry)]
    else:
        raise ValueError('Unsupported GeoJSON type. Expected FeatureCollection, Feature, Polygon, or MultiPolygon.')

    if not geoms:
        raise ValueError('GeoJSON contains no geometries.')

    boundary = unary_union(geoms)
    if boundary.is_empty:
        raise ValueError('Boundary geometry is empty.')

    return boundary


def get_utm_transformer(reference_geometry):
    """Create a pyproj Transformer for the UTM zone of the reference geometry."""
    lon, lat = reference_geometry.centroid.x, reference_geometry.centroid.y
    zone = int((lon + 180) / 6) + 1
    epsg_code = 32600 + zone if lat >= 0 else 32700 + zone
    target_crs = f"EPSG:{epsg_code}"
    transformer = Transformer.from_crs('EPSG:4326', target_crs, always_xy=True)
    return transformer, target_crs


def transform_geometry(geometry, transformer):
    return shapely_transform(transformer.transform, geometry)


def is_exclusion_tag(tags: dict) -> bool:
    """Return True if the feature tags indicate an exclusion area."""
    landuse = tags.get('landuse', '')
    amenity = tags.get('amenity', '')
    building = tags.get('building', '')

    if landuse in EXCLUSION_LANDUSE:
        return True
    if amenity in EXCLUSION_AMENITY:
        return True
    if building in EXCLUSION_BUILDING:
        return True

    return False


def is_human_tag(tags: dict) -> bool:
    """Return True if tags indicate a human-occupied area (schools, residential, industrial...)."""
    landuse = tags.get('landuse', '')
    amenity = tags.get('amenity', '')
    building = tags.get('building', '')

    if landuse in EXCLUSION_LANDUSE:
        return True
    if amenity in EXCLUSION_AMENITY:
        return True
    if building in EXCLUSION_BUILDING:
        return True
    return False


def _load_osm_exclusions_osmium(osm_path: Path):
    class ExclusionHandler(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.wkb_factory = osmium.geom.WKBFactory()
            self.human_geoms = []
            self.unhuman_geoms = []

        def area(self, area):
            tags = {k.lower(): v.lower() for k, v in area.tags.items()}
            if not is_exclusion_tag(tags):
                return
            try:
                wkb = self.wkb_factory.create_multipolygon(area)
                geom = shapely_wkb.loads(wkb)
            except Exception:
                return
            if geom.is_empty:
                return
            if is_human_tag(tags):
                self.human_geoms.append(geom)
            else:
                self.unhuman_geoms.append(geom)

    handler = ExclusionHandler()
    handler.apply_file(str(osm_path), locations=True)
    human = unary_union(handler.human_geoms) if handler.human_geoms else GeometryCollection()
    unhuman = unary_union(handler.unhuman_geoms) if handler.unhuman_geoms else GeometryCollection()
    return human, unhuman


def _load_osm_exclusions_ogr(osm_path: Path):
    datasource = ogr.Open(str(osm_path))
    if datasource is None:
        raise RuntimeError(f'Unable to open OSM file: {osm_path}')

    human_geoms = []
    unhuman_geoms = []
    for layer_index in range(datasource.GetLayerCount()):
        layer = datasource.GetLayer(layer_index)
        layer.ResetReading()
        for feature in layer:
            tags = {}
            for field_index in range(feature.GetFieldCount()):
                field_def = feature.GetFieldDefnRef(field_index)
                if field_def is None:
                    continue
                field_name = field_def.GetNameRef().lower()
                field_value = feature.GetField(field_index)
                if field_value is not None:
                    tags[field_name] = str(field_value).lower()
            if not is_exclusion_tag(tags):
                continue
            geometry = feature.GetGeometryRef()
            if geometry is None:
                continue
            try:
                shapely_geom = shape(json.loads(geometry.ExportToJson()))
            except Exception:
                continue
            if shapely_geom.is_empty:
                continue
            if is_human_tag(tags):
                human_geoms.append(shapely_geom)
            else:
                unhuman_geoms.append(shapely_geom)

    human = unary_union(human_geoms) if human_geoms else GeometryCollection()
    unhuman = unary_union(unhuman_geoms) if unhuman_geoms else GeometryCollection()
    return human, unhuman


def load_osm_exclusions(osm_path: Path):
    """Return a tuple (human_geom, unhuman_geom) in lat/lon coordinates."""
    if OSMIUM_AVAILABLE:
        try:
            return _load_osm_exclusions_osmium(osm_path)
        except Exception:
            pass

    if OGR_AVAILABLE:
        return _load_osm_exclusions_ogr(osm_path)

    raise RuntimeError('No available OSM parser found. Install osmium or gdal/ogr.')


def shapely_geometry_to_floris_boundaries(geometry):
    """Convert a Shapely Polygon/MultiPolygon into FLORIS boundary coordinate lists."""
    boundaries = []

    def append_polygon(polygon):
        coords = list(polygon.exterior.coords)
        if len(coords) >= 4:
            boundaries.append(coords)

    if isinstance(geometry, Polygon):
        append_polygon(geometry)
    elif isinstance(geometry, MultiPolygon):
        for polygon in geometry.geoms:
            append_polygon(polygon)
    elif isinstance(geometry, GeometryCollection):
        for geom in geometry.geoms:
            if isinstance(geom, (Polygon, MultiPolygon)):
                boundaries.extend(shapely_geometry_to_floris_boundaries(geom))

    return boundaries


def get_allowed_area(geojson_path: Path, osm_path: Path, buffer_human_m: float = 1000.0, buffer_unhuman_m: float = 500.0):
    """Compute the allowed installation area after excluding OSM-defined forbidden regions.

    Args:
        geojson_path: Path to GeoJSON boundary (lon/lat)
        osm_path: Path to OSM PBF file (lon/lat)
        buffer_human_m: buffer distance in meters for human-occupied areas
        buffer_unhuman_m: buffer distance in meters for uninhabited/natural areas

    Returns:
        (boundary_utm, exclusions_utm, allowed_area, allowed_boundaries, target_crs)
    """
    boundary_ll = load_geojson_boundary(geojson_path)
    human_ll, unhuman_ll = load_osm_exclusions(osm_path)

    transformer, target_crs = get_utm_transformer(boundary_ll)
    boundary_utm = transform_geometry(boundary_ll, transformer)

    human_utm = transform_geometry(human_ll, transformer) if not human_ll.is_empty else GeometryCollection()
    unhuman_utm = transform_geometry(unhuman_ll, transformer) if not unhuman_ll.is_empty else GeometryCollection()

    # Apply buffers in meters to each class
    human_buf = human_utm.buffer(buffer_human_m) if not human_utm.is_empty else GeometryCollection()
    unhuman_buf = unhuman_utm.buffer(buffer_unhuman_m) if not unhuman_utm.is_empty else GeometryCollection()

    # Union of all exclusions after buffering
    exclusions_utm = unary_union([geom for geom in [human_buf, unhuman_buf] if not geom.is_empty])

    allowed_area = boundary_utm.difference(exclusions_utm) if not exclusions_utm.is_empty else boundary_utm
    allowed_boundaries = shapely_geometry_to_floris_boundaries(allowed_area)

    return boundary_utm, exclusions_utm, allowed_area, allowed_boundaries, target_crs


def plot_shapely_geometry(ax, geometry, edge_color='k', face_color='none', alpha=1.0, linewidth=1.5):
    """Plot a Shapely Polygon or MultiPolygon on the given matplotlib axes."""
    if isinstance(geometry, Polygon):
        polygons = [geometry]
    elif isinstance(geometry, MultiPolygon):
        polygons = list(geometry.geoms)
    else:
        polygons = []

    for polygon in polygons:
        x, y = polygon.exterior.xy
        ax.plot(x, y, color=edge_color, alpha=alpha, linewidth=linewidth)
        for interior in polygon.interiors:
            xi, yi = interior.xy
            ax.plot(xi, yi, color=edge_color, alpha=alpha * 0.7, linewidth=linewidth, linestyle='--')
