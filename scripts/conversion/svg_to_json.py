"""Convierte los planos SVG de FloorPlanCAD en anotaciones LabelMe JSON.

Cada clase del dataset la produce un detector que combina tres estrategias:
cómo se seleccionan los elementos (semantic-id y/o etiqueta de capa de
Inkscape), cómo se agrupan en instancias (instance-id, clustering espacial,
unión global o por elemento) y cómo cada grupo se vuelve un polígono
(envolvente convexa, caja o la geometría unida).

Además, guarda cada PNG normalizado a fondo blanco y líneas oscuras, como los
planos analógicos (ver docs/NORMALIZACION.md).
"""

import argparse
import json
import math
import os
import xml.etree.ElementTree as ET
from collections import defaultdict

from PIL import Image
from shapely.affinity import scale
from shapely.geometry import LineString, MultiPoint, Point, Polygon, box
from shapely.ops import unary_union
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
    "墙体": "wall",
    "WALL": "wall",
    "楼梯": "stair",
    "J-家具": "table",
    "A-楼电梯-电梯": "elevator",
}

# Los trazos finos antialiasados casi nunca llegan a alfa 255 y quedarían gris
# claro. Amplificar el alfa los lleva a casi negro sin perder el borde suave.
INK_GAIN = 4


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


def extract_points(element):
    """Extrae los puntos de un elemento SVG (path, circle o ellipse)."""
    if element["type"] == "path":
        return sample_path_points(element["attrs"].get("d", ""))
    try:
        cx, cy, rx, ry = ellipse_params(element)
    except Exception:
        return []
    return sample_ellipse_points(cx, cy, rx, ry) if rx > 0 and ry > 0 else []


def element_to_polygon(element):
    """Convierte un circle o una ellipse en un polígono de Shapely, o None."""
    try:
        cx, cy, rx, ry = ellipse_params(element)
    except Exception:
        return None
    if rx <= 0 or ry <= 0:
        return None
    if element["type"] == "circle":
        return Point(cx, cy).buffer(rx, quad_segs=16)
    return scale(Point(cx, cy).buffer(1.0, quad_segs=16), rx, ry, origin=(cx, cy))


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


class MergedUnionDetector(SymbolDetector):
    """Une todos los elementos de la clase en polígonos sin agujeros.

    Se usa para muros: los segmentos que se tocan se funden en muros continuos
    con unary_union. Los muros unidos suelen encerrar habitaciones como anillos
    interiores; split_holes evita que el anillo exterior exportado las rellene.
    """

    LINE_BUFFER = 0.5
    # Los muros son bandas finas (~1 unidad de ancho), así que toleran menos
    # simplificación que las bandas más anchas de curtwall y railing.
    SIMPLIFY_TOLERANCE = 0.1

    def build_polygons(self, selected):
        geometries = [element_geometry(element, self.LINE_BUFFER) for element in selected]
        polygons = []
        for merged_polygon in union_polygons(geometries):
            polygons.extend(simplify_and_split(merged_polygon, self.SIMPLIFY_TOLERANCE))
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


def build_detectors():
    """Arma el detector de cada clase del dataset.

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
