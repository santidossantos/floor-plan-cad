"""Convert FloorPlanCAD SVG drawings into LabelMe-format JSON annotations.

Each dataset class is produced by a detector built from three interchangeable
strategies: how elements are selected (semantic id and/or Inkscape layer
label), how they are grouped into symbol instances (instance-id, spatial
clustering, global union or per element), and how each group becomes a
polygon (convex hull, bounding box or the merged geometry itself).

Además, guarda cada PNG normalizado a fondo blanco y líneas oscuras, como los
planos analógicos (ver docs/NORMALIZACION.md).
"""

import argparse
import json
import math
import os
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from collections import defaultdict

from PIL import Image
from shapely.affinity import scale
from shapely.geometry import LineString, MultiPoint, Point, Polygon, box
from shapely.ops import unary_union
from svg.path import parse_path


# ============================================================================
# Configuration
# ============================================================================
SEMANTIC_IDS = {
    "wall": "1",
    "curtwall": "2",
    "single_door": "3",
    "double_door": "4",
    "sliding_door": "5",
    "wall_move": "6",
    "revolving_door": "7",
    "fire_door": "8",
    "window": "9",
    "bay_window": "10",
    "blind_window": "11",
    "opening_symbol": "12",
    "sofa": "13",
    "bed": "14",
    "chair": "15",
    "table": "16",
    "TV_cabinet": "17",
    "wardrobe": "18",
    "bedside_cupboards": "19",
    "refrigerator": "20",
    "airconditioner": "21",
    "gas_stove": "22",
    "sink": "23",
    "bath": "24",
    "bath_tub": "25",
    "washing_machine": "26",
    "squat_toilet": "27",
    "urinal": "28",
    "toilet": "29",
    "stair": "30",
    "elevator": "31",
    "escalator": "32",
    "railing": "33",
    "cinema_chair": "34",
    "parking": "35",
}

INKSCAPE_LABEL_FALLBACK = {
    "地饰": ("floor_finish", "structure"),
    "家具": ("furniture", "furneture"),
    "装施家具": ("built_in_furniture", "furneture"),
    "墙体": ("wall", "wall"),
    "WALL": ("wall", "wall"),
    "WINDOW": ("window", "window"),
    "门": ("door", "door"),
    "窗": ("window", "window"),
    "楼梯": ("stair", "stair"),
    "卫生器具": ("sanitary_fixture", "furneture"),
    "轴线": ("axis", "reference"),
    "尺寸标注": ("dimension", "annotation"),
    "房间名称": ("room_name", "annotation"),
    "结构": ("structure", "structure"),
    "电器设备": ("electrical_equipment", "equipment"),
    "采暖设备": ("heating_equipment", "equipment"),
    "给排水设备": ("plumbing_equipment", "equipment"),
    "空调设备": ("air_conditioning", "equipment"),
    "家具布置": ("furniture_layout", "furneture"),
    "J-家具": ("table", "furneture"),
    "A-楼电梯-电梯": ("elevator", "equipment"),
}

# Los trazos finos antialiasados casi nunca llegan a alfa 255 y quedarían gris
# claro. Amplificar el alfa los lleva a casi negro sin perder el borde suave.
INK_GAIN = 4


# ============================================================================
# Geometry utilities
# ============================================================================
def svg_to_pixel(x_svg, y_svg, vb_w, vb_h, img_w, img_h):
    """Convert SVG viewBox coordinates to pixel coordinates."""
    return x_svg * (img_w / vb_w), y_svg * (img_h / vb_h)


def sample_circle_points(cx, cy, r, n=16):
    """Sample n points around a circle."""
    return [(cx + r * math.cos(2 * math.pi * i / n),
             cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def sample_path_points(d_string, samples_per_segment=12):
    """Extract sampled points from an SVG path d attribute."""
    pts = []
    try:
        path = parse_path(d_string)
        for seg in path:
            for k in range(samples_per_segment):
                t = k / (samples_per_segment - 1) if samples_per_segment > 1 else 0
                p = seg.point(t)
                pts.append((p.real, p.imag))
    except Exception:
        pass
    return pts


def extract_points(element):
    """Extract all coordinate points from a supported SVG element."""
    el_type = element["type"]
    attrs = element["attrs"]

    try:
        if el_type == "circle":
            cx, cy = float(attrs.get("cx", 0)), float(attrs.get("cy", 0))
            r = float(attrs.get("r", 0))
            return sample_circle_points(cx, cy, r) if r > 0 else []

        if el_type == "ellipse":
            cx, cy = float(attrs.get("cx", 0)), float(attrs.get("cy", 0))
            rx = float(attrs.get("rx", attrs.get("r", 0)) or 0)
            ry = float(attrs.get("ry", attrs.get("r", 0)) or 0)
            if rx > 0 and ry > 0:
                return [(cx + rx * math.cos(2 * math.pi * i / 16),
                         cy + ry * math.sin(2 * math.pi * i / 16)) for i in range(16)]
            return []

        if el_type == "rect":
            x, y = float(attrs.get("x", 0)), float(attrs.get("y", 0))
            w, h = float(attrs.get("width", 0)), float(attrs.get("height", 0))
            return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)] if w > 0 and h > 0 else []

        if el_type in ("polygon", "polyline"):
            pts_raw = attrs.get("points", "").strip()
            if pts_raw:
                parts = pts_raw.replace(",", " ").split()
                if len(parts) % 2 == 0:
                    return [(float(parts[i]), float(parts[i + 1])) for i in range(0, len(parts), 2)]
            return []

        if el_type == "line":
            return [(float(attrs.get("x1", 0)), float(attrs.get("y1", 0))),
                    (float(attrs.get("x2", 0)), float(attrs.get("y2", 0)))]

        if el_type == "path":
            d = attrs.get("d", "")
            return sample_path_points(d) if d else []

    except Exception:
        pass

    return []


def element_to_polygon(element):
    """Convert an SVG element to a Shapely polygon, or None if not possible."""
    el_type = element["type"]
    attrs = element["attrs"]

    try:
        if el_type == "circle":
            cx, cy = float(attrs.get("cx", 0)), float(attrs.get("cy", 0))
            r = float(attrs.get("r", 0))
            return Point(cx, cy).buffer(r, resolution=16) if r > 0 else None

        if el_type == "ellipse":
            cx, cy = float(attrs.get("cx", 0)), float(attrs.get("cy", 0))
            rx = float(attrs.get("rx", attrs.get("r", 0)) or 0)
            ry = float(attrs.get("ry", attrs.get("r", 0)) or 0)
            if rx > 0 and ry > 0:
                base = Point(cx, cy).buffer(1.0, resolution=16)
                return scale(base, rx, ry, origin=(cx, cy))
            return None

        if el_type == "rect":
            x, y = float(attrs.get("x", 0)), float(attrs.get("y", 0))
            w, h = float(attrs.get("width", 0)), float(attrs.get("height", 0))
            if w > 0 and h > 0:
                return Polygon([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])
            return None

        if el_type in ("polygon", "polyline"):
            pts_raw = attrs.get("points", "").strip()
            if pts_raw:
                parts = pts_raw.replace(",", " ").split()
                if len(parts) % 2 == 0:
                    pts = [(float(parts[i]), float(parts[i + 1])) for i in range(0, len(parts), 2)]
                    if len(pts) >= 3:
                        if el_type == "polyline" and pts[0] != pts[-1]:
                            pts.append(pts[0])
                        return Polygon(pts)
            return None

        if el_type == "line":
            line = LineString([(float(attrs.get("x1", 0)), float(attrs.get("y1", 0))),
                               (float(attrs.get("x2", 0)), float(attrs.get("y2", 0)))])
            return line.buffer(0.5, resolution=8)

        if el_type == "path":
            pts = sample_path_points(attrs.get("d", ""))
            if len(pts) >= 3:
                if pts[0] != pts[-1]:
                    pts.append(pts[0])
                return Polygon(pts)
            return None

    except Exception:
        pass

    return None


def element_to_line(element):
    """Convert a path or line element to a LineString, or None for other types."""
    attrs = element["attrs"]

    if element["type"] == "path":
        points = sample_path_points(attrs.get("d", ""))
        return LineString(points) if len(points) >= 2 else None

    if element["type"] == "line":
        return LineString([(float(attrs.get("x1", 0)), float(attrs.get("y1", 0))),
                           (float(attrs.get("x2", 0)), float(attrs.get("y2", 0)))])

    return None


def split_holes(polygon, min_area=1.0, _depth=0):
    """Split a polygon with interior rings (holes) into hole-free pieces.

    LabelMe/YOLO only represent the exterior ring, so a polygon with holes is
    exported "filled" (e.g. walls enclosing a room would cover the whole
    room). The polygon is cut vertically through a hole centroid, recursively,
    until no piece has holes. The union of the pieces equals the original.
    """
    if polygon.is_empty or polygon.area < min_area:
        return []
    if not polygon.interiors or _depth > 32:
        return [polygon]

    minx, miny, maxx, maxy = polygon.bounds
    cut_x = polygon.interiors[0].centroid.x
    if not (minx < cut_x < maxx):
        cut_x = (minx + maxx) / 2.0

    left = polygon.intersection(box(minx - 1, miny - 1, cut_x, maxy + 1))
    right = polygon.intersection(box(cut_x, miny - 1, maxx + 1, maxy + 1))

    pieces = []
    for part in (left, right):
        geoms = part.geoms if hasattr(part, "geoms") else [part]
        for geom in geoms:
            if geom.geom_type == "Polygon" and geom.is_valid and not geom.is_empty:
                pieces.append(geom)

    if not pieces:
        return [Polygon(polygon.exterior)]

    results = []
    for piece in pieces:
        results.extend(split_holes(piece, min_area, _depth + 1))
    return results


def is_valid_polygon(geometry):
    """Check that a geometry is a usable, non-degenerate polygon."""
    return (geometry is not None
            and geometry.geom_type == "Polygon"
            and geometry.is_valid
            and not geometry.is_empty)


MAX_RING_VERTICES = 100


def split_oversized(polygon, max_vertices=MAX_RING_VERTICES, min_area=1.0, _depth=0):
    """Split a hole-free polygon with an oversized ring into smaller pieces.

    Very large merged networks can keep hundreds of vertices even after
    simplification, and some annotation viewers truncate long polygon lines,
    rendering them as bogus triangles. Halving along the longer axis keeps
    the union of the pieces identical to the original polygon.
    """
    if len(polygon.exterior.coords) <= max_vertices or _depth > 16:
        return [polygon]

    minx, miny, maxx, maxy = polygon.bounds
    if maxx - minx >= maxy - miny:
        mid = (minx + maxx) / 2.0
        halves = (box(minx - 1, miny - 1, mid, maxy + 1),
                  box(mid, miny - 1, maxx + 1, maxy + 1))
    else:
        mid = (miny + maxy) / 2.0
        halves = (box(minx - 1, miny - 1, maxx + 1, mid),
                  box(minx - 1, mid, maxx + 1, maxy + 1))

    pieces = []
    for half in halves:
        part = polygon.intersection(half)
        geoms = part.geoms if hasattr(part, "geoms") else [part]
        for geom in geoms:
            if (geom.geom_type == "Polygon" and geom.is_valid
                    and not geom.is_empty and geom.area >= min_area):
                pieces.extend(split_oversized(geom, max_vertices, min_area, _depth + 1))
    return pieces or [polygon]


def simplify_and_split(polygon, tolerance):
    """Simplify a merged polygon and split it into hole-free, bounded pieces.

    Buffered unions carry hundreds of redundant vertices; keeping them makes
    annotations heavy and overflows line-length limits in some viewers.
    """
    simplified = polygon.simplify(tolerance, preserve_topology=True)
    if simplified.geom_type != "Polygon" or simplified.is_empty:
        simplified = polygon
    return [bounded_piece
            for piece in split_holes(simplified)
            for bounded_piece in split_oversized(piece)]


def iter_polygons(geometry):
    """Yield the individual valid polygons of a union result."""
    geoms = geometry.geoms if hasattr(geometry, "geoms") else [geometry]
    for geom in geoms:
        if is_valid_polygon(geom):
            yield geom


# ============================================================================
# SVG parsing
# ============================================================================
SUPPORTED_TAGS = ("circle", "ellipse", "rect", "polygon", "polyline", "line", "path")


def parse_svg(svg_path):
    """Parse an SVG file into (viewbox_width, viewbox_height, elements).

    Each element carries its tag type, semantic-id, instance-id, the Inkscape
    label of its nearest labeled parent group, and its raw attributes.
    """
    tree = ET.parse(svg_path)
    root = tree.getroot()

    viewbox = root.attrib.get("viewBox")
    if not viewbox:
        raise ValueError(f"SVG missing viewBox: {svg_path}")

    _, _, vb_w, vb_h = map(float, viewbox.split())

    parent_map = {child: parent for parent in root.iter() for child in parent}
    inkscape_ns = "{http://www.inkscape.org/namespaces/inkscape}"

    elements = []
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue

        tag = el.tag.split("}")[-1].lower()
        if tag not in SUPPORTED_TAGS:
            continue

        inkscape_label = ""
        current = el
        while current in parent_map:
            parent = parent_map[current]
            parent_tag = parent.tag.split("}")[-1].lower() if isinstance(parent.tag, str) else ""
            if parent_tag == "g":
                label = parent.attrib.get(f"{inkscape_ns}label", "")
                if label:
                    inkscape_label = label
                    break
            current = parent

        elements.append({
            "type": tag,
            "semantic_id": el.attrib.get("semantic-id") or el.attrib.get("semantic_id"),
            "instance_id": el.attrib.get("instance-id") or el.attrib.get("instance_id"),
            "inkscape_label": inkscape_label,
            "attrs": dict(el.attrib),
        })

    return vb_w, vb_h, elements


# ============================================================================
# Selection strategies: which elements belong to a dataset class
# ============================================================================
class SemanticIdSelection:
    """Select elements annotated with the semantic id of a dataset class."""

    def __init__(self, class_name):
        self.semantic_id = SEMANTIC_IDS[class_name]

    def __call__(self, element):
        return element.get("semantic_id") == self.semantic_id


class InkscapeLabelSelection:
    """Select elements by the Inkscape label of their parent layer.

    With `exact` the whole label must match a fallback key; otherwise a
    substring match is used. `only_unlabeled` restricts the match to elements
    without a semantic id, so elements already annotated as another class are
    not picked up again.
    """

    def __init__(self, class_name, exact=False, only_unlabeled=True):
        self.label_keys = [key for key, (name, _) in INKSCAPE_LABEL_FALLBACK.items()
                           if name == class_name]
        self.exact = exact
        self.only_unlabeled = only_unlabeled

    def __call__(self, element):
        if self.only_unlabeled and element.get("semantic_id") is not None:
            return False
        label = element.get("inkscape_label", "")
        if self.exact:
            return label in self.label_keys
        return any(key in label for key in self.label_keys)


class CompositeSelection:
    """Select elements matching any of the given selection strategies."""

    def __init__(self, selections):
        self.selections = selections

    def __call__(self, element):
        return any(selection(element) for selection in self.selections)


# ============================================================================
# Shape strategies: turn a group of points into one polygon
# ============================================================================
def convex_hull_shape(points):
    return MultiPoint(points).convex_hull


def envelope_shape(points):
    return MultiPoint(points).envelope


# ============================================================================
# Detectors
# ============================================================================
def group_by_instance_id(elements):
    """Group elements by instance id, preserving element order."""
    groups = defaultdict(list)
    for element in elements:
        groups[element.get("instance_id") or "unknown"].append(element)
    return groups


def collect_points(elements):
    """Concatenate the coordinate points of all elements."""
    points = []
    for element in elements:
        points.extend(extract_points(element))
    return points


class SymbolDetector(ABC):
    """Base detector: select the class elements, then build labeled polygons.

    `detect` is a template method; subclasses only decide how the selected
    elements are grouped and turned into polygons.
    """

    def __init__(self, label, selection):
        self.label = label
        self.selection = selection

    def detect(self, elements):
        selected = [element for element in elements if self.selection(element)]
        return [
            {"polygon": polygon, "label": self.label}
            for polygon in self.build_polygons(selected)
            if is_valid_polygon(polygon)
        ]

    @abstractmethod
    def build_polygons(self, selected):
        """Return candidate polygons for the selected elements."""


class InstanceGroupDetector(SymbolDetector):
    """One shape per instance-id group, built from all points in the group.

    Fits symbols whose strokes share an instance id (doors, windows,
    furniture, sanitary fixtures). The shape strategy is the convex hull by
    default, or the axis-aligned envelope for classes drawn as clean
    rectangles (bath, wardrobe).
    """

    MIN_POINTS = 3

    def __init__(self, label, selection, shape_fn=convex_hull_shape):
        super().__init__(label, selection)
        self.shape_fn = shape_fn

    def build_polygons(self, selected):
        polygons = []
        for group in group_by_instance_id(selected).values():
            points = collect_points(group)
            if len(points) >= self.MIN_POINTS:
                polygons.append(self.shape_fn(points))
        return polygons


class SplitInstanceGroupDetector(SymbolDetector):
    """Instance-id grouping with spatial sub-clustering inside each group.

    Some drawings reuse one instance id for two separate pieces of furniture
    (e.g. TV cabinets); a single hull would cover both plus the gap between
    them. Each group is clustered spatially; clusters of size comparable to
    the largest one become separate symbols, and small leftover fragments are
    assigned to the nearest of those cores.
    """

    CLUSTER_BUFFER = 0.8
    CORE_AREA_RATIO = 0.5
    MIN_POINTS = 3

    def build_polygons(self, selected):
        polygons = []
        for group in group_by_instance_id(selected).values():
            polygons.extend(self._split_group(group))
        return polygons

    def _split_group(self, group):
        element_geoms = []
        for element in group:
            points = extract_points(element)
            if len(points) >= 2:
                element_geoms.append((LineString(points).buffer(self.CLUSTER_BUFFER), points))
            elif len(points) == 1:
                element_geoms.append((Point(points[0]).buffer(self.CLUSTER_BUFFER), points))

        if not element_geoms:
            return []

        merged = unary_union([geometry for geometry, _ in element_geoms])
        components = list(merged.geoms) if hasattr(merged, "geoms") else [merged]

        largest_area = max(component.convex_hull.area for component in components)
        cores = [component for component in components
                 if component.convex_hull.area >= self.CORE_AREA_RATIO * largest_area]

        core_points = [[] for _ in cores]
        for geometry, points in element_geoms:
            distances = [core.distance(geometry) for core in cores]
            core_points[distances.index(min(distances))].extend(points)

        return [convex_hull_shape(points) for points in core_points
                if len(points) >= self.MIN_POINTS]


class FilledOutlineDetector(SymbolDetector):
    """One filled outline per instance-id group, following concave shapes.

    Used for furniture that is rectangular or L-shaped (sofas): the convex
    hull of an L-shaped symbol wrongly fills the notch of the L. Instead, the
    strokes are buffered and merged, the enclosed region is filled, and the
    result is eroded back by the same buffer so it hugs the drawn outline.
    """

    STROKE_BUFFER = 0.5
    SIMPLIFY_TOLERANCE = 0.3

    def build_polygons(self, selected):
        polygons = []
        for group in group_by_instance_id(selected).values():
            polygons.extend(self._outline_group(group))
        return polygons

    def _outline_group(self, group):
        strokes = []
        for element in group:
            points = extract_points(element)
            if len(points) >= 2:
                strokes.append(LineString(points).buffer(self.STROKE_BUFFER))
            elif len(points) == 1:
                strokes.append(Point(points[0]).buffer(self.STROKE_BUFFER))
        if not strokes:
            return []

        filled = unary_union([Polygon(band.exterior)
                              for band in iter_polygons(unary_union(strokes))])
        footprint = filled.buffer(-self.STROKE_BUFFER)
        if footprint.is_empty or footprint.area < 0.5 * filled.area:
            # Open stroke sets collapse when eroded; keep the filled band then.
            footprint = filled

        return [piece.simplify(self.SIMPLIFY_TOLERANCE, preserve_topology=True)
                for piece in iter_polygons(footprint)]


class PerElementEnvelopeDetector(SymbolDetector):
    """One axis-aligned box per element, with no grouping at all.

    Used for wall_move: its paths form continuous outlines spanning entire
    rooms, so neither instance-id grouping nor spatial clustering works.
    """

    LINE_BUFFER = 0.5

    def build_polygons(self, selected):
        polygons = []
        for element in selected:
            points = extract_points(element)
            if len(points) >= 2:
                line = LineString(points)
                if not line.is_empty:
                    polygons.append(line.buffer(self.LINE_BUFFER).envelope)
        return polygons


class BandClusterDetector(SymbolDetector):
    """Spatial clustering that keeps each cluster's actual merged geometry.

    Fits long thin linear elements (curtain walls, railings) whose strokes
    share no usable instance id. Each element is buffered into a thin band
    and overlapping bands are merged into clusters. The cluster geometry
    itself is exported: a bounding box would be wrong here, since an L-shaped
    or diagonal run produces a box covering most of the drawing.
    """

    SIMPLIFY_TOLERANCE = 0.3

    def __init__(self, label, selection, line_buffer):
        super().__init__(label, selection)
        self.line_buffer = line_buffer

    def build_polygons(self, selected):
        bands = []
        for element in selected:
            points = extract_points(element)
            if len(points) >= 2:
                line = LineString(points)
                if not line.is_empty:
                    bands.append(line.buffer(self.line_buffer))

        if not bands:
            return []

        polygons = []
        for cluster in iter_polygons(unary_union(bands)):
            polygons.extend(simplify_and_split(cluster, self.SIMPLIFY_TOLERANCE))
        return polygons


class MergedUnionDetector(SymbolDetector):
    """Merge every element of the class into unified hole-free polygons.

    Used for walls: touching segments are fused into continuous wall shapes
    via unary_union. Merged walls often enclose rooms as interior rings;
    split_holes keeps the exported exterior ring from filling those rooms.
    """

    LINE_BUFFER = 0.5
    BUFFER_RESOLUTION = 4
    # Walls are thin bands (~1 unit wide), so they tolerate less
    # simplification than the wider curtwall/railing bands.
    SIMPLIFY_TOLERANCE = 0.1

    def build_polygons(self, selected):
        geometries = []
        for element in selected:
            geometry = self._element_geometry(element)
            if geometry is not None and geometry.is_valid and not geometry.is_empty:
                geometries.append(geometry)

        if not geometries:
            return []

        polygons = []
        for merged_polygon in iter_polygons(unary_union(geometries)):
            polygons.extend(simplify_and_split(merged_polygon, self.SIMPLIFY_TOLERANCE))
        return polygons

    def _element_geometry(self, element):
        try:
            line = element_to_line(element)
            if line is not None:
                return line.buffer(self.LINE_BUFFER, resolution=self.BUFFER_RESOLUTION)
            return element_to_polygon(element)
        except Exception:
            return None


class ClusterBBoxDetector(SymbolDetector):
    """Spatial clustering with one axis-aligned bounding box per cluster.

    Fits compact rectangular symbols drawn as many disconnected strokes
    (stairs, elevators): the strokes are buffered and merged into clusters,
    and each cluster is exported as its bounding box.
    """

    ELEMENT_BUFFER = 1.0
    BUFFER_RESOLUTION = 4

    def build_polygons(self, selected):
        geometries = []
        for element in selected:
            geometry = self._element_geometry(element)
            if geometry is not None and geometry.is_valid and not geometry.is_empty:
                geometries.append(geometry)

        if not geometries:
            return []

        return [cluster.envelope for cluster in iter_polygons(unary_union(geometries))]

    def _element_geometry(self, element):
        try:
            line = element_to_line(element)
            if line is not None:
                return line.buffer(self.ELEMENT_BUFFER, resolution=self.BUFFER_RESOLUTION)
            polygon = element_to_polygon(element)
            if polygon is None or not polygon.is_valid or polygon.is_empty:
                return None
            return polygon.buffer(self.ELEMENT_BUFFER)
        except Exception:
            return None


def build_detectors():
    """Build the detector for every dataset class.

    The order defines the order of shapes in the output JSON.
    """
    return [
        InstanceGroupDetector("toilet", SemanticIdSelection("toilet")),
        InstanceGroupDetector("single_door", SemanticIdSelection("single_door")),
        InstanceGroupDetector("double_door", SemanticIdSelection("double_door")),
        InstanceGroupDetector("sliding_door", SemanticIdSelection("sliding_door")),
        PerElementEnvelopeDetector("wall_move", SemanticIdSelection("wall_move")),
        InstanceGroupDetector("revolving_door", SemanticIdSelection("revolving_door")),
        InstanceGroupDetector("fire_door", SemanticIdSelection("fire_door")),
        InstanceGroupDetector("window", SemanticIdSelection("window")),
        InstanceGroupDetector("bay_window", SemanticIdSelection("bay_window")),
        InstanceGroupDetector("blind_window", SemanticIdSelection("blind_window")),
        InstanceGroupDetector("opening_symbol", SemanticIdSelection("opening_symbol")),
        BandClusterDetector("curtwall", SemanticIdSelection("curtwall"), line_buffer=1.5),
        MergedUnionDetector("wall", CompositeSelection([
            SemanticIdSelection("wall"),
            InkscapeLabelSelection("wall"),
        ])),
        InstanceGroupDetector("table", CompositeSelection([
            SemanticIdSelection("table"),
            InkscapeLabelSelection("table", only_unlabeled=False),
        ])),
        ClusterBBoxDetector("stair", CompositeSelection([
            SemanticIdSelection("stair"),
            InkscapeLabelSelection("stair"),
        ])),
        ClusterBBoxDetector("elevator",
                            InkscapeLabelSelection("elevator", exact=True, only_unlabeled=False)),
        InstanceGroupDetector("escalator", SemanticIdSelection("escalator")),
        InstanceGroupDetector("airconditioner", SemanticIdSelection("airconditioner")),
        InstanceGroupDetector("sink", SemanticIdSelection("sink")),
        InstanceGroupDetector("urinal", SemanticIdSelection("urinal")),
        InstanceGroupDetector("squat_toilet", SemanticIdSelection("squat_toilet")),
        InstanceGroupDetector("wardrobe", SemanticIdSelection("wardrobe"),
                              shape_fn=envelope_shape),
        InstanceGroupDetector("gas_stove", SemanticIdSelection("gas_stove")),
        InstanceGroupDetector("bedside_cupboard", SemanticIdSelection("bedside_cupboards")),
        FilledOutlineDetector("sofa", SemanticIdSelection("sofa")),
        InstanceGroupDetector("chair", SemanticIdSelection("chair")),
        InstanceGroupDetector("bath_tub", SemanticIdSelection("bath_tub")),
        SplitInstanceGroupDetector("TV_cabinet", SemanticIdSelection("TV_cabinet")),
        InstanceGroupDetector("bed", SemanticIdSelection("bed")),
        InstanceGroupDetector("bath", SemanticIdSelection("bath"), shape_fn=envelope_shape),
        InstanceGroupDetector("refrigerator", SemanticIdSelection("refrigerator")),
        InstanceGroupDetector("washing_machine", SemanticIdSelection("washing_machine")),
        InstanceGroupDetector("cinema_chair", SemanticIdSelection("cinema_chair")),
        InstanceGroupDetector("parking", SemanticIdSelection("parking")),
        BandClusterDetector("railing", SemanticIdSelection("railing"), line_buffer=1.0),
    ]


# ============================================================================
# LabelMe output
# ============================================================================
def polygon_to_labelme_shape(polygon, label, vb_w, vb_h, img_w, img_h):
    """Convert a Shapely polygon to a LabelMe shape dict."""
    points = [
        list(svg_to_pixel(x, y, vb_w, vb_h, img_w, img_h))
        for x, y in polygon.exterior.coords
    ]
    return {
        "label": label,
        "points": points,
        "shape_type": "polygon",
        "flags": {},
    }


def write_labelme_json(path, image_name, img_w, img_h, shapes):
    """Write shapes to a LabelMe-format JSON file."""
    data = {
        "version": "5.0.1",
        "flags": {},
        "shapes": shapes,
        "imagePath": image_name,
        "imageData": None,
        "imageWidth": img_w,
        "imageHeight": img_h,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ============================================================================
# Normalización de imagen
# ============================================================================
def normalize_image(image):
    """Devuelve una copia RGB con fondo blanco y líneas oscuras.

    Los PNG de FloorPlanCAD son RGBA con fondo transparente, que en RGB se lee
    negro. El trazo se toma del canal alfa porque no depende del color: en RGB,
    los trazos negros se pierden sobre el fondo negro.
    """
    ink = image.getchannel("A").point(lambda alpha: 255 - min(alpha * INK_GAIN, 255))
    return ink.convert("RGB")


# ============================================================================
# Main pipeline
# ============================================================================
def process_files(input_dir, output_dir):
    """Process all SVG/PNG pairs in input_dir and write LabelMe JSON to output_dir."""
    # Guardar en la misma carpeta sobrescribiría los PNG originales
    if os.path.abspath(input_dir) == os.path.abspath(output_dir):
        raise ValueError("--output debe ser distinta de --input")

    svgs = {os.path.splitext(f)[0]: os.path.join(input_dir, f)
            for f in os.listdir(input_dir) if f.lower().endswith(".svg")}
    pngs = {os.path.splitext(f)[0]: os.path.join(input_dir, f)
            for f in os.listdir(input_dir) if f.lower().endswith(".png")}

    os.makedirs(output_dir, exist_ok=True)
    detectors = build_detectors()

    for name, svg_path in svgs.items():
        if name not in pngs:
            continue

        img_w, img_h = Image.open(pngs[name]).size
        vb_w, vb_h, elements = parse_svg(svg_path)

        detections = [detection
                      for detector in detectors
                      for detection in detector.detect(elements)]

        shapes = [
            polygon_to_labelme_shape(d["polygon"], d["label"], vb_w, vb_h, img_w, img_h)
            for d in detections
        ]

        out_path = os.path.join(output_dir, f"{name}.json")
        write_labelme_json(out_path, os.path.basename(pngs[name]), img_w, img_h, shapes)

        out_png_path = os.path.join(output_dir, os.path.basename(pngs[name]))
        normalize_image(Image.open(pngs[name])).save(out_png_path)

        print(f"{name}: {len(shapes)} shapes -> {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Convert SVG floor plans to LabelMe JSON")
    parser.add_argument("--input", required=True, help="Input directory with SVG/PNG pairs")
    parser.add_argument("--output", required=True, help="Output directory for JSON files")
    args = parser.parse_args()

    process_files(args.input, args.output)


if __name__ == "__main__":
    main()
