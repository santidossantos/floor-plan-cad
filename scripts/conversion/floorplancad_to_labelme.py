"""Convierte los planos SVG de FloorPlanCAD en anotaciones LabelMe JSON.

Cada clase del dataset la produce un detector que combina tres estrategias:
cómo se seleccionan los elementos (semantic-id y/o etiqueta de capa de
Inkscape), cómo se agrupan en instancias (instance-id, clustering espacial,
unión global o por elemento) y cómo cada grupo se vuelve un polígono
(envolvente convexa, caja, la geometría unida o el contorno dibujado).

Además, guarda cada PNG normalizado a fondo blanco y líneas oscuras, como los
planos analógicos (ver docs/NORMALIZACION.md).
"""

import argparse
import json
import math
import os
import re
import xml.etree.ElementTree as ET
from collections import defaultdict

import numpy as np
import shapely
from PIL import Image
from shapely.affinity import rotate, scale
from shapely.geometry import LineString, MultiLineString, MultiPoint, Point, Polygon, box
from shapely.ops import polygonize, split, unary_union
from shapely.prepared import prep
from svg.path import parse_path


# ============================================================================
# Configuración
# ============================================================================
# semantic-id de cada clase en los SVG de FloorPlanCAD
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

# Capas de Inkscape que identifican una clase cuando falta el semantic-id
INKSCAPE_LABEL_FALLBACK = {
    "楼梯": "stair",
    "J-家具": "table",
    "A-楼电梯-电梯": "elevator",
}

# Los trazos finos antialiasados casi nunca llegan a alfa 255 y quedarían gris
# claro. Amplificar el alfa los lleva a casi negro sin perder el borde suave.
INK_GAIN = 4

# Espesor de pared cuando no se puede estimar, y tolerancia para unir trazos
# que casi se tocan (imprecisiones del dibujo de ~0.004 unidades)
DEFAULT_WALL_THICKNESS = 2.0
WALL_SNAP_TOLERANCE = 0.02


# ============================================================================
# Utilidades geométricas
# ============================================================================
def svg_to_pixel(x_svg, y_svg, vb_w, vb_h, img_w, img_h):
    """Convierte coordenadas del viewBox del SVG a píxeles."""
    return x_svg * (img_w / vb_w), y_svg * (img_h / vb_h)


def sample_ellipse_points(cx, cy, rx, ry, n=16):
    """Muestrea n puntos sobre una elipse (un círculo si rx == ry)."""
    return [(cx + rx * math.cos(2 * math.pi * i / n),
             cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


def sample_path_points(d_string, samples_per_segment=12):
    """Muestrea puntos de cada segmento del atributo d de un path."""
    pts = []
    try:
        for seg in parse_path(d_string):
            for k in range(samples_per_segment):
                p = seg.point(k / (samples_per_segment - 1))
                pts.append((p.real, p.imag))
    except Exception:
        pass
    return pts


def ellipse_params(element):
    """Devuelve (cx, cy, rx, ry) de un circle o una ellipse."""
    attrs = element["attrs"]
    cx, cy = float(attrs.get("cx", 0)), float(attrs.get("cy", 0))
    if element["type"] == "circle":
        r = float(attrs.get("r", 0))
        return cx, cy, r, r
    rx = float(attrs.get("rx", attrs.get("r", 0)) or 0)
    ry = float(attrs.get("ry", attrs.get("r", 0)) or 0)
    return cx, cy, rx, ry


ROTATE_PATTERN = re.compile(r"rotate\(\s*([^,\s]+)[\s,]+([^,\s]+)[\s,]+([^,\s)]+)\s*\)")


def element_rotation(element):
    """Devuelve (ángulo, cx, cy) del transform="rotate(a, cx, cy)", o None.

    En FloorPlanCAD las elipses siempre traen un transform de esta forma.
    """
    match = ROTATE_PATTERN.fullmatch(element["attrs"].get("transform", "").strip())
    return tuple(float(v) for v in match.groups()) if match else None


def extract_points(element):
    """Extrae los puntos de un elemento SVG (path, circle o ellipse)."""
    if element["type"] == "path":
        return sample_path_points(element["attrs"].get("d", ""))
    try:
        cx, cy, rx, ry = ellipse_params(element)
    except Exception:
        return []
    if rx <= 0 or ry <= 0:
        return []
    points = sample_ellipse_points(cx, cy, rx, ry)
    rotation = element_rotation(element)
    if rotation is None:
        return points
    angle, ox, oy = rotation
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    return [(ox + c * (x - ox) - s * (y - oy), oy + s * (x - ox) + c * (y - oy))
            for x, y in points]


def element_to_polygon(element):
    """Convierte un circle o una ellipse en un polígono de Shapely, o None."""
    try:
        cx, cy, rx, ry = ellipse_params(element)
    except Exception:
        return None
    if rx <= 0 or ry <= 0:
        return None
    if element["type"] == "circle":
        polygon = Point(cx, cy).buffer(rx, quad_segs=16)
    else:
        polygon = scale(Point(cx, cy).buffer(1.0, quad_segs=16), rx, ry, origin=(cx, cy))
    rotation = element_rotation(element)
    return rotate(polygon, rotation[0], origin=rotation[1:]) if rotation else polygon


def buffer_points(points, distance, quad_segs=16):
    """Engrosa la línea que une los puntos, o devuelve None si hay menos de 2."""
    if len(points) < 2:
        return None
    return LineString(points).buffer(distance, quad_segs=quad_segs)


def element_geometry(element, line_buffer):
    """Geometría de un elemento: un path se engrosa; un circle o ellipse se rellena."""
    if element["type"] == "path":
        return buffer_points(extract_points(element), line_buffer, quad_segs=4)
    return element_to_polygon(element)


def is_valid_polygon(geometry):
    """Indica si la geometría es un polígono válido y no vacío."""
    return (geometry is not None
            and geometry.geom_type == "Polygon"
            and geometry.is_valid
            and not geometry.is_empty)


def geometry_parts(geometry):
    """Devuelve las partes de una geometría múltiple, o la geometría sola."""
    return list(geometry.geoms) if hasattr(geometry, "geoms") else [geometry]


def iter_polygons(geometry):
    """Recorre los polígonos válidos del resultado de una unión."""
    return (geom for geom in geometry_parts(geometry) if is_valid_polygon(geom))


def union_polygons(geometries):
    """Une las geometrías válidas y devuelve los polígonos resultantes."""
    return list(iter_polygons(unary_union([g for g in geometries if is_valid_polygon(g)])))


def split_holes(polygon, min_area=1.0, _depth=0):
    """Divide un polígono con agujeros en piezas sin agujeros.

    LabelMe y YOLO solo representan el anillo exterior, así que un polígono con
    agujeros se exporta "relleno" (p. ej. los muros que rodean una habitación
    la cubrirían entera). Se corta en vertical por el centroide de un agujero,
    recursivamente, hasta que ninguna pieza tenga agujeros. La unión de las
    piezas es igual al original.
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
    pieces = [geom for part in (left, right) for geom in iter_polygons(part)]

    if not pieces:
        return [Polygon(polygon.exterior)]

    results = []
    for piece in pieces:
        results.extend(split_holes(piece, min_area, _depth + 1))
    return results


MAX_RING_VERTICES = 100


def split_oversized(polygon, max_vertices=MAX_RING_VERTICES, min_area=1.0, _depth=0):
    """Divide un polígono sin agujeros cuyo anillo tiene demasiados vértices.

    Las redes unidas muy grandes conservan cientos de vértices aun después de
    simplificarlas, y algunos visores truncan las líneas largas y las muestran
    como triángulos espurios. Partir a la mitad por el eje más largo mantiene
    la unión de las piezas igual al polígono original.
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
        for geom in iter_polygons(polygon.intersection(half)):
            if geom.area >= min_area:
                pieces.extend(split_oversized(geom, max_vertices, min_area, _depth + 1))
    return pieces or [polygon]


def simplify_and_split(polygon, tolerance):
    """Simplifica un polígono unido y lo divide en piezas sin agujeros y acotadas.

    Las uniones de bandas engrosadas tienen cientos de vértices redundantes;
    conservarlos hace pesadas las anotaciones y supera el largo de línea que
    admiten algunos visores.
    """
    simplified = polygon.simplify(tolerance, preserve_topology=True)
    if simplified.geom_type != "Polygon" or simplified.is_empty:
        simplified = polygon
    return [bounded_piece
            for piece in split_holes(simplified)
            for bounded_piece in split_oversized(piece)]


# ============================================================================
# Lectura del SVG
# ============================================================================
SUPPORTED_TAGS = ("circle", "ellipse", "path")
INKSCAPE_LABEL_ATTR = "{http://www.inkscape.org/namespaces/inkscape}label"


def find_layer_label(element, parent_map):
    """Devuelve la etiqueta de Inkscape del grupo <g> etiquetado más cercano, o ""."""
    while element in parent_map:
        element = parent_map[element]
        label = element.attrib.get(INKSCAPE_LABEL_ATTR, "")
        if element.tag.split("}")[-1].lower() == "g" and label:
            return label
    return ""


def parse_svg(svg_path):
    """Lee un SVG y devuelve (ancho del viewBox, alto del viewBox, elementos).

    Cada elemento lleva su tipo de etiqueta, semantic-id, instance-id, la
    etiqueta de Inkscape de su grupo etiquetado más cercano y sus atributos.
    """
    root = ET.parse(svg_path).getroot()

    viewbox = root.attrib.get("viewBox")
    if not viewbox:
        raise ValueError(f"SVG missing viewBox: {svg_path}")
    _, _, vb_w, vb_h = map(float, viewbox.split())

    parent_map = {child: parent for parent in root.iter() for child in parent}

    elements = []
    for el in root.iter():
        tag = el.tag.split("}")[-1].lower()
        if tag not in SUPPORTED_TAGS:
            continue
        elements.append({
            "type": tag,
            "semantic_id": el.attrib.get("semantic-id"),
            "instance_id": el.attrib.get("instance-id"),
            "inkscape_label": find_layer_label(el, parent_map),
            "attrs": dict(el.attrib),
        })

    return vb_w, vb_h, elements


# ============================================================================
# Estrategias de selección: qué elementos pertenecen a una clase
# ============================================================================
class SemanticIdSelection:
    """Selecciona los elementos con el semantic-id de una clase."""

    def __init__(self, class_name):
        self.semantic_id = SEMANTIC_IDS[class_name]

    def __call__(self, element):
        return element.get("semantic_id") == self.semantic_id


class InkscapeLabelSelection:
    """Selecciona elementos por la etiqueta de Inkscape de su capa.

    Con `exact` la etiqueta debe coincidir entera con una clave del fallback;
    si no, alcanza con que la contenga. `only_unlabeled` limita la selección a
    elementos sin semantic-id, para no tomar los ya anotados como otra clase.
    """

    def __init__(self, class_name, exact=False, only_unlabeled=True):
        self.label_keys = [key for key, name in INKSCAPE_LABEL_FALLBACK.items()
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
    """Selecciona los elementos que cumplen alguna de las selecciones dadas."""

    def __init__(self, selections):
        self.selections = selections

    def __call__(self, element):
        return any(selection(element) for selection in self.selections)


# ============================================================================
# Estrategias de forma: convierten un grupo de puntos en un polígono
# ============================================================================
def convex_hull_shape(points):
    """Envolvente convexa de los puntos."""
    return MultiPoint(points).convex_hull


def envelope_shape(points):
    """Caja alineada a los ejes que contiene los puntos."""
    return MultiPoint(points).envelope


# ============================================================================
# Paredes: relleno entre caras y cortes en los encuentros (ver docs/PAREDES.md)
# ============================================================================
def wall_line(element):
    """Línea de un path de pared, sin puntos repetidos ni intermedios colineales."""
    pts = extract_points(element)
    pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
    return LineString(pts).simplify(1e-6) if len(pts) >= 2 else None


def estimate_wall_thickness(lines):
    """Espesor de pared del plano.

    Para cada segmento se mide la distancia a la cara paralela más cercana,
    entre 0.5 y 6 (así se ignoran las caras dibujadas con varias líneas). El
    espesor es la mayor de esas distancias que cubre al menos el 5 % de la
    longitud de pared.
    """
    segs = [line.coords for line in lines if len(line.coords) == 2]
    if len(segs) < 2:
        return DEFAULT_WALL_THICKNESS
    a = np.array([s[0] for s in segs])
    b = np.array([s[1] for s in segs])
    length = np.linalg.norm(b - a, axis=1)
    keep = length > 1e-6
    a, b, length = a[keep], b[keep], length[keep]
    u = (b - a) / length[:, None]
    n = np.stack([-u[:, 1], u[:, 0]], axis=1)
    to_a, to_b = a[None] - a[:, None], b[None] - a[:, None]
    dist = np.abs(np.einsum("ik,ijk->ij", n, to_a))
    t0, t1 = np.einsum("ik,ijk->ij", u, to_a), np.einsum("ik,ijk->ij", u, to_b)
    overlap = (np.minimum(length[:, None], np.maximum(t0, t1))
               - np.maximum(0, np.minimum(t0, t1)))
    valid = ((np.abs(u @ u.T) > 0.999) & (dist > 0.5) & (dist <= 6)
             & (overlap > 0.2 * np.minimum(length[:, None], length[None])))
    nearest = np.where(valid, dist, np.inf).min(axis=1)
    found = np.isfinite(nearest)
    if found.sum() < 3:
        return DEFAULT_WALL_THICKNESS
    bins, idx = np.unique(np.round(nearest[found], 1), return_inverse=True)
    weight = np.bincount(idx, weights=length[found])
    return float(max(bins[weight >= 0.05 * weight.sum()]))


def line_ends(line):
    """Extremos de la línea, cada uno con su dirección hacia afuera."""
    c = line.coords
    for end, prev in ((c[0], c[1]), (c[-1], c[-2])):
        p = np.array(end)
        u = p - np.array(prev)
        yield p, u / np.linalg.norm(u)


def end_caps(lines, tree, t):
    """Cierres virtuales entre extremos libres de caras cercanas (pared abierta)."""
    ends = [(i, p, u) for i, line in enumerate(lines) for p, u in line_ends(line)
            if all(j == i for j in tree.query(Point(p), predicate="dwithin", distance=1e-3 * t))]
    caps = []
    for i, p, u in ends:
        best = None
        for j, q, _ in ends:
            d = np.linalg.norm(q - p)
            if j != i and 1e-6 < d <= 1.2 * t and abs((q - p) @ u) / d < 0.75:
                if best is None or d < best[0]:
                    best = (d, q)
        if best is not None:
            caps.append(LineString([p, best[1]]))
    return caps


def is_thin(face, t):
    """Indica si la cara es angosta en su mayor parte (no entra un círculo de radio 0.6 t)."""
    fat = face.buffer(-0.6 * t, quad_segs=4)
    return fat.is_empty or fat.buffer(0.6 * t, quad_segs=4).area < 0.5 * face.area


def wall_region(lines, tree, border, t):
    """Une las caras angostas que encierran las líneas de pared.

    Las caras se arman con las líneas, los cierres virtuales y el borde del
    plano (la mayoría de los planos son recortes y las paredes llegan al borde).
    """
    outline = MultiLineString(lines + end_caps(lines, tree, t) + [border.exterior])
    noded = shapely.unary_union(shapely.snap(outline, outline, WALL_SNAP_TOLERANCE),
                                grid_size=1e-4)
    return unary_union([face for face in polygonize(geometry_parts(noded)) if is_thin(face, t)])


def is_through_face(q, rings, t):
    """Indica si el borde de la pared sigue recto a ambos lados de q (cara pasante de una T)."""
    point = Point(q)
    ring = min(rings, key=lambda r: r.distance(point))
    if ring.distance(point) > 0.02 * t or ring.length < 3 * t:
        return False
    d0, s = ring.project(point), 1.5 * t
    a = np.array(ring.interpolate((d0 + s) % ring.length).coords[0]) - q
    b = np.array(ring.interpolate((d0 - s) % ring.length).coords[0]) - q
    straight = abs(a[0] * b[1] - a[1] * b[0]) < 0.05 * t * s and a @ b < 0
    return straight and min(np.linalg.norm(a), np.linalg.norm(b)) > 0.98 * s


def cut_candidates(lines, region, t):
    """Segmentos que podrían separar dos paredes.

    Son las prolongaciones de cada línea más allá de sus extremos y los tramos
    de línea que quedan dentro de la región (p. ej. la boca dibujada de una T).
    """
    for line in lines:
        for p, u in line_ends(line):
            ext = LineString([p, p + 2.2 * t * u])
            for part in geometry_parts(ext.intersection(region)):
                if (part.geom_type == "LineString" and not part.is_empty
                        and Point(p).distance(Point(part.coords[0])) <= 1e-3 * t):
                    yield part
    rim = region.boundary.buffer(2e-3 * t)
    on_rim = prep(rim)
    for line in lines:
        if not on_rim.contains(line):
            for part in geometry_parts(line.difference(rim)):
                if part.geom_type == "LineString" and not part.is_empty:
                    yield part


def junction_cuts(lines, region, t):
    """Cortes en los encuentros de paredes.

    Un candidato corta si atraviesa la pared (largo de hasta 2.1 t), continúa
    en línea recta un borde de la región y no termina en medio de una cara
    pasante: así, en una T la pared que sigue de largo no se corta.
    """
    inside = prep(region)
    rings = [region.exterior] + list(region.interiors)
    rim = prep(region.boundary.buffer(0.02 * t))
    cuts = []
    for part in cut_candidates(lines, region, t):
        p, q = np.array(part.coords[0]), np.array(part.coords[-1])
        length = np.linalg.norm(q - p)
        if not (1e-3 * t < length <= 2.1 * t):
            continue
        if not inside.contains(part.interpolate(0.5, normalized=True)):
            continue
        u = (q - p) / length
        if not (rim.contains(Point(p - 0.5 * t * u)) or rim.contains(Point(q + 0.5 * t * u))):
            continue
        if is_through_face(p, rings, t) or is_through_face(q, rings, t):
            continue
        cuts.append(shapely.snap(LineString([p, q]), region.boundary, 5e-3 * t))
    return cuts


def is_junction_piece(piece, t):
    """Pieza del tamaño de un encuentro: lado mayor <= 1.6 t y área < 1.25 t²."""
    xs, ys = piece.minimum_rotated_rectangle.exterior.coords.xy
    sides = [math.hypot(xs[j + 1] - xs[j], ys[j + 1] - ys[j]) for j in range(2)]
    return max(sides) <= 1.6 * t and piece.area < 1.25 * t * t


def merge_junctions(pieces, t):
    """Une cada encuentro (pieza chica) a la pieza vecina de mayor área."""
    tree = shapely.STRtree(pieces)
    parent = list(range(len(pieces)))

    def root(i):
        while parent[i] != i:
            i = parent[i]
        return i

    for i in sorted(range(len(pieces)), key=lambda i: pieces[i].area):
        if not is_junction_piece(pieces[i], t):
            continue
        neighbors = [j for j in tree.query(pieces[i], predicate="intersects")
                     if j != i and pieces[i].intersection(pieces[j]).length > 1e-6]
        if neighbors:
            parent[root(i)] = root(max(neighbors, key=lambda j: pieces[j].area))

    groups = defaultdict(list)
    for i, piece in enumerate(pieces):
        groups[root(i)].append(piece)
    return [unary_union(group) for group in groups.values()]


# ============================================================================
# Contornos de sanitarios: siguen el trazo dibujado en vez de la envolvente
# ============================================================================
def symbol_strokes(elements):
    """Trazos de los elementos: la línea de cada path y el borde de cada circle o ellipse."""
    strokes = []
    for element in elements:
        if element["type"] == "path":
            points = extract_points(element)
            if len(points) >= 2:
                strokes.append(LineString(points))
        elif (polygon := element_to_polygon(element)) is not None:
            strokes.append(polygon.exterior)
    return strokes


def without_stray_lines(strokes):
    """Quita las rectas más largas que la diagonal de la caja del resto del símbolo.

    Son bordes de mesada o ejes que comparten instance-id con el símbolo y
    estirarían su envolvente.
    """
    kept = []
    for i, stroke in enumerate(strokes):
        others = strokes[:i] + strokes[i + 1:]
        straight = math.dist(stroke.coords[0], stroke.coords[-1]) >= 0.999 * stroke.length
        if straight and others:
            x0, y0, x1, y1 = shapely.total_bounds(others)
            if stroke.length > math.hypot(x1 - x0, y1 - y0):
                continue
        kept.append(stroke)
    return kept


def connected_strokes(strokes, candidates, tree, touch, growth):
    """Candidatos conectados en cadena a los trazos, sin salir de su caja agrandada en `growth`."""
    x0, y0, x1, y1 = shapely.total_bounds(strokes)
    margin = growth * max(x1 - x0, y1 - y0)
    limit = box(x0 - margin, y0 - margin, x1 + margin, y1 + margin)
    added, frontier = set(), strokes
    while frontier:
        found = {int(j) for j in tree.query(frontier, predicate="dwithin", distance=touch)[1]
                 if int(j) not in added and limit.contains(candidates[j])}
        added |= found
        frontier = [candidates[j] for j in found]
    return [candidates[j] for j in sorted(added)]


def enclosed_region(strokes, gap, opening):
    """Mayor región encerrada por los trazos, cerrando huecos de hasta 2 * gap.

    Los trazos se engrosan, se rellenan los huecos que encierran y se erosionan;
    la erosión extra seguida de dilatación (`opening`) quita astillas finas.
    """
    bands = unary_union([stroke.buffer(gap, quad_segs=4) for stroke in strokes])
    filled = unary_union([Polygon(band.exterior) for band in iter_polygons(bands)])
    region = filled.buffer(-(gap + opening), quad_segs=4).buffer(opening, quad_segs=4)
    return max(iter_polygons(region), key=lambda part: part.area, default=None)


# ============================================================================
# Detectores
# ============================================================================
def group_by_instance_id(elements):
    """Agrupa los elementos por instance-id, conservando su orden."""
    groups = defaultdict(list)
    for element in elements:
        groups[element.get("instance_id") or "unknown"].append(element)
    return groups


def collect_points(elements):
    """Concatena los puntos de todos los elementos."""
    points = []
    for element in elements:
        points.extend(extract_points(element))
    return points


class SymbolDetector:
    """Detector base: selecciona los elementos de la clase y arma polígonos etiquetados.

    Las subclases solo deciden cómo agrupar los elementos seleccionados y cómo
    convertirlos en polígonos (`build_polygons`).
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

    def build_polygons(self, selected):
        """Devuelve los polígonos candidatos de los elementos seleccionados."""
        raise NotImplementedError


class InstanceGroupDetector(SymbolDetector):
    """Una forma por grupo de instance-id, armada con todos los puntos del grupo.

    Sirve para símbolos cuyos trazos comparten instance-id (puertas, ventanas,
    muebles, sanitarios). La forma es la envolvente convexa por defecto, o la
    caja alineada a los ejes para clases dibujadas como rectángulos (bath,
    wardrobe).
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
    """Agrupa por instance-id y subdivide cada grupo por cercanía espacial.

    Algunos planos reusan un instance-id para dos muebles separados (p. ej.
    muebles de TV); una sola envolvente cubriría los dos y el espacio entre
    ellos. Cada grupo se divide en clusters espaciales: los de tamaño parecido
    al mayor pasan a ser símbolos separados, y los fragmentos chicos se
    asignan al más cercano de ellos.
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
            band = buffer_points(points, self.CLUSTER_BUFFER)
            if band is not None:
                element_geoms.append((band, points))

        if not element_geoms:
            return []

        merged = unary_union([geometry for geometry, _ in element_geoms])
        components = geometry_parts(merged)

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
    """Un contorno relleno por grupo de instance-id, que sigue formas cóncavas.

    Se usa para muebles rectangulares o en L (sofás): la envolvente convexa de
    un símbolo en L rellena por error el hueco de la L. En cambio, los trazos
    se engrosan y se unen, se rellena la región encerrada y el resultado se
    erosiona con el mismo margen para que se ajuste al contorno dibujado.
    """

    STROKE_BUFFER = 0.5
    SIMPLIFY_TOLERANCE = 0.3

    def build_polygons(self, selected):
        polygons = []
        for group in group_by_instance_id(selected).values():
            polygons.extend(self._outline_group(group))
        return polygons

    def _outline_group(self, group):
        strokes = [buffer_points(extract_points(element), self.STROKE_BUFFER)
                   for element in group]
        strokes = [stroke for stroke in strokes if stroke is not None]
        if not strokes:
            return []

        filled = unary_union([Polygon(band.exterior)
                              for band in iter_polygons(unary_union(strokes))])
        footprint = filled.buffer(-self.STROKE_BUFFER)
        if footprint.is_empty or footprint.area < 0.5 * filled.area:
            # Los trazos abiertos colapsan al erosionarlos; se usa la banda rellena.
            footprint = filled

        return [piece.simplify(self.SIMPLIFY_TOLERANCE, preserve_topology=True)
                for piece in iter_polygons(footprint)]


class OutlineDetector(SymbolDetector):
    """Una forma por grupo de instance-id que sigue el contorno dibujado.

    Se usa para sanitarios (sink, urinal, squat_toilet), donde la envolvente
    convexa falla de tres maneras: rectas del grupo que no son el símbolo
    (bordes de mesada, ejes) la estiran; parte del contorno viene sin
    semantic-id, como curvas explotadas en segmentos cortos; y rellena las
    concavidades. Por eso se quitan esas rectas, se suman los segmentos cortos
    sin etiqueta del mismo color conectados al símbolo, y se usa la región
    encerrada por los trazos si cubre casi toda la envolvente. Si no la cubre,
    el símbolo está abierto (p. ej. contra la pared) y queda la envolvente.
    """

    GAP = 0.25
    OPENING = 0.1
    TOUCH = 0.02
    GROWTH = 0.3
    LOOSE_MAX_LENGTH = 0.5
    MIN_FILL = 0.8
    SIMPLIFY_TOLERANCE = 0.02

    def detect(self, elements):
        # Los trazos sin etiqueta del plano pueden completar el contorno
        self.elements = elements
        return super().detect(elements)

    def build_polygons(self, selected):
        groups = group_by_instance_id(selected).values()
        colors = {element["attrs"].get("stroke") for group in groups for element in group}
        loose, loose_colors = [], []
        for element in self.elements:
            color = element["attrs"].get("stroke")
            if element["semantic_id"] is None and element["type"] == "path" and color in colors:
                for line in symbol_strokes([element]):
                    if line.length <= self.LOOSE_MAX_LENGTH:
                        loose.append(line)
                        loose_colors.append(color)

        polygons = []
        for group in groups:
            strokes = without_stray_lines(symbol_strokes(group))
            if not strokes:
                continue
            group_colors = {element["attrs"].get("stroke") for element in group}
            candidates = [line for line, color in zip(loose, loose_colors) if color in group_colors]
            if candidates:
                strokes += connected_strokes(strokes, candidates, shapely.STRtree(candidates),
                                             self.TOUCH, self.GROWTH)
            hull = unary_union(strokes).convex_hull
            region = enclosed_region(strokes, self.GAP, self.OPENING)
            shape = region if region is not None and region.area >= self.MIN_FILL * hull.area else hull
            polygons.append(shape.simplify(self.SIMPLIFY_TOLERANCE))
        return polygons


class PerElementEnvelopeDetector(SymbolDetector):
    """Una caja alineada a los ejes por elemento, sin agrupar.

    Se usa para wall_move: sus paths forman contornos continuos que abarcan
    habitaciones enteras, así que no sirve agrupar por instance-id ni por
    cercanía espacial.
    """

    LINE_BUFFER = 0.5

    def build_polygons(self, selected):
        bands = [buffer_points(extract_points(element), self.LINE_BUFFER)
                 for element in selected]
        return [band.envelope for band in bands if band is not None]


class BandClusterDetector(SymbolDetector):
    """Clustering espacial que conserva la geometría unida de cada cluster.

    Sirve para elementos lineales largos y finos (muros cortina, barandas)
    cuyos trazos no comparten un instance-id útil. Cada elemento se engrosa
    como una banda fina y las bandas que se superponen forman clusters. Se
    exporta la geometría del cluster: una caja estaría mal, porque un tramo en
    L o diagonal produce una caja que cubre casi todo el plano.
    """

    SIMPLIFY_TOLERANCE = 0.3

    def __init__(self, label, selection, line_buffer):
        super().__init__(label, selection)
        self.line_buffer = line_buffer

    def build_polygons(self, selected):
        bands = [buffer_points(extract_points(element), self.line_buffer)
                 for element in selected]
        polygons = []
        for cluster in union_polygons(bands):
            polygons.extend(simplify_and_split(cluster, self.SIMPLIFY_TOLERANCE))
        return polygons


class WallDetector(SymbolDetector):
    """Un polígono por pared, con el criterio de "pared pasante".

    Las paredes se dibujan como sus dos caras más los cierres. Se rellena el
    área angosta entre las caras y se corta en los encuentros prolongando las
    caras: en una T la pared que sigue de largo queda entera y la que llega
    termina en su cara; en una L la esquina queda en la pared de mayor área.
    """

    SIMPLIFY_TOLERANCE = 0.05

    def __init__(self, label, selection, border):
        super().__init__(label, selection)
        self.border = border

    def build_polygons(self, selected):
        lines = [line for line in (wall_line(e) for e in selected if e["type"] == "path")
                 if line is not None]
        if not lines:
            return []
        t = estimate_wall_thickness(lines)
        tree = shapely.STRtree(lines)
        solids = [s for s in (element_to_polygon(e) for e in selected if e["type"] != "path")
                  if is_valid_polygon(s)]
        region = unary_union([wall_region(lines, tree, self.border, t)] + solids)

        pieces = []
        for poly in iter_polygons(region):
            near = [lines[i] for i in tree.query(poly, predicate="dwithin", distance=1e-2 * t)]
            cuts = junction_cuts(near, poly, t)
            parts = geometry_parts(split(poly, MultiLineString(cuts))) if cuts else [poly]
            pieces.extend(part for part in parts if is_valid_polygon(part))
        if not pieces:
            return []

        polygons = []
        for wall in merge_junctions(pieces, t):
            for part in iter_polygons(wall):
                if part.area >= 0.1 * t * t:
                    polygons.extend(simplify_and_split(part, self.SIMPLIFY_TOLERANCE))
        return polygons


class ClusterBBoxDetector(SymbolDetector):
    """Clustering espacial con una caja alineada a los ejes por cluster.

    Sirve para símbolos rectangulares compactos dibujados con muchos trazos
    sueltos (escaleras, ascensores): los trazos se engrosan y se unen en
    clusters, y cada cluster se exporta como su caja.
    """

    ELEMENT_BUFFER = 1.0

    def build_polygons(self, selected):
        geometries = []
        for element in selected:
            geometry = element_geometry(element, self.ELEMENT_BUFFER)
            # Los círculos y elipses también se engrosan, como los trazos
            if element["type"] != "path" and is_valid_polygon(geometry):
                geometry = geometry.buffer(self.ELEMENT_BUFFER)
            geometries.append(geometry)
        return [cluster.envelope for cluster in union_polygons(geometries)]


def build_detectors(border):
    """Arma el detector de cada clase del dataset para un plano de borde `border`.

    El orden define el orden de las formas en el JSON de salida.
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
        WallDetector("wall", SemanticIdSelection("wall"), border),
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
        OutlineDetector("sink", SemanticIdSelection("sink")),
        OutlineDetector("urinal", SemanticIdSelection("urinal")),
        OutlineDetector("squat_toilet", SemanticIdSelection("squat_toilet")),
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
# Salida LabelMe
# ============================================================================
def polygon_to_labelme_shape(polygon, label, vb_w, vb_h, img_w, img_h):
    """Convierte un polígono de Shapely en una forma de LabelMe."""
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
    """Escribe las formas en un JSON con formato LabelMe."""
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
# Pipeline principal
# ============================================================================
def process_files(input_dir, output_dir):
    """Procesa cada par SVG/PNG de input_dir y escribe el JSON LabelMe y el PNG normalizado."""
    # Guardar en la misma carpeta sobrescribiría los PNG originales
    if os.path.abspath(input_dir) == os.path.abspath(output_dir):
        raise ValueError("--output debe ser distinta de --input")

    svgs = {os.path.splitext(f)[0]: os.path.join(input_dir, f)
            for f in os.listdir(input_dir) if f.lower().endswith(".svg")}
    pngs = {os.path.splitext(f)[0]: os.path.join(input_dir, f)
            for f in os.listdir(input_dir) if f.lower().endswith(".png")}

    os.makedirs(output_dir, exist_ok=True)

    for name, svg_path in svgs.items():
        if name not in pngs:
            continue

        img_w, img_h = Image.open(pngs[name]).size
        vb_w, vb_h, elements = parse_svg(svg_path)

        detections = [detection
                      for detector in build_detectors(box(0, 0, vb_w, vb_h))
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
    parser.add_argument("--input", nargs="+", required=True,
                        help="Input folders with SVG/PNG pairs (e.g. train-00 train-01 test-00)")
    parser.add_argument("--output", required=True,
                        help="Output folder; each input folder is written to <output>/<folder name>")
    args = parser.parse_args()

    # Cada carpeta va a su propia subcarpeta, porque hay planos con el mismo nombre en distintas carpetas
    names = [os.path.basename(os.path.normpath(folder)) for folder in args.input]
    if len(set(names)) != len(names):
        raise ValueError("Las carpetas de --input deben tener nombres distintos")

    for folder, name in zip(args.input, names):
        process_files(folder, os.path.join(args.output, name))


if __name__ == "__main__":
    main()
