"""Convierte carpetas anotadas en LabelMe en un dataset YOLO-seg.

Todas las carpetas de --input se juntan y se dividen al azar en
train/val/test (80/10/10 por defecto). Los archivos se prefijan con el nombre
de su carpeta para evitar choques entre planos con el mismo nombre.
"""

import argparse
import json
import os
import random
import shutil

import shapely
import yaml
from shapely.geometry import Polygon, box

RANDOM_SEED = 42

VAL_FRACTION = 0.1
TEST_FRACTION = 0.1

# El id de cada clase es su posición en la lista, sin importar qué clases traiga la entrada
CLASSES = [
    "TV_cabinet", "airconditioner", "bath", "bath_tub", "bay_window", "bed",
    "bedside_cupboard", "blind_window", "chair", "curtwall", "double_door",
    "elevator", "escalator", "gas_stove", "opening_symbol", "railing",
    "refrigerator", "single_door", "sink", "sliding_door", "sofa",
    "squat_toilet", "stair", "table", "toilet", "urinal", "wall", "wardrobe",
    "washing_machine", "window",
]
CLASS_IDS = {label: i for i, label in enumerate(CLASSES)}

EXCLUDED_CLASSES = {"fire_door", "wall_move", "revolving_door", "parking", "cinema_chair"}

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")


# ----------------------------------------------------------------------------
# Lectura de anotaciones
# ----------------------------------------------------------------------------
def list_annotation_bases(folder):
    """Devuelve, ordenados, los nombres base de los JSON LabelMe de una carpeta."""
    return sorted(os.path.splitext(f)[0] for f in os.listdir(folder) if f.endswith(".json"))


def load_labelme_json(json_path):
    with open(json_path, "r") as f:
        return json.load(f)


# ----------------------------------------------------------------------------
# Conversión de anotaciones
# ----------------------------------------------------------------------------
def clip_to_image(points, width, height):
    """Recorta el polígono al borde de la imagen; puede quedar en varias partes."""
    if all(0 <= x <= width and 0 <= y <= height for x, y in points):
        return [points]
    clipped = shapely.make_valid(Polygon(points)).intersection(box(0, 0, width, height))
    return [list(part.exterior.coords) for part in shapely.get_parts(clipped)
            if part.geom_type == "Polygon"]


def normalize_polygon(points, width, height):
    """Convierte puntos absolutos en coordenadas YOLO-seg normalizadas."""
    return [v for x, y in points for v in (x / width, y / height)]


def convert_annotation(json_path, label_path):
    """Escribe un JSON LabelMe como .txt YOLO-seg, sin formas duplicadas."""
    data = load_labelme_json(json_path)
    width, height = data["imageWidth"], data["imageHeight"]

    lines = []
    for shape in data.get("shapes", []):
        if shape["label"] in EXCLUDED_CLASSES:
            continue
        class_id = CLASS_IDS[shape["label"]]
        for points in clip_to_image(shape["points"], width, height):
            coords = normalize_polygon(points, width, height)
            lines.append(f"{class_id} " + " ".join(f"{p:.6f}" for p in coords))

    # Ultralytics descarta con un aviso los polígonos repetidos (misma línea)
    with open(label_path, "w") as f:
        f.write("\n".join(dict.fromkeys(lines)))


# ----------------------------------------------------------------------------
# Exportación de muestras
# ----------------------------------------------------------------------------
def find_image(folder, base):
    """Devuelve la ruta de la imagen de una anotación, o None."""
    for ext in IMAGE_EXTENSIONS:
        image_path = os.path.join(folder, base + ext)
        if os.path.exists(image_path):
            return image_path
    return None


def export_sample(folder, base, split_name, output_folder):
    """Exporta un par anotación+imagen a un split del dataset.

    El nombre de salida lleva como prefijo el nombre de la carpeta de origen,
    para que los planos con el mismo nombre en distintas carpetas no se pisen.
    """
    out_base = f"{os.path.basename(os.path.normpath(folder))}_{base}"

    label_path = os.path.join(output_folder, "labels", split_name, out_base + ".txt")
    convert_annotation(os.path.join(folder, base + ".json"), label_path)

    image_path = find_image(folder, base)
    ext = os.path.splitext(image_path)[1]
    shutil.copy(image_path, os.path.join(output_folder, "images", split_name, out_base + ext))


# ----------------------------------------------------------------------------
# División train / val / test
# ----------------------------------------------------------------------------
def split_dataset(items, val_fraction, test_fraction):
    """Divide los planos al azar en train/val/test según las fracciones dadas."""
    # Semilla propia: el split no depende del estado global de random
    items = sorted(items)
    random.Random(RANDOM_SEED).shuffle(items)

    val_count = round(len(items) * val_fraction)
    test_count = round(len(items) * test_fraction)

    test = items[:test_count]
    val = items[test_count:test_count + val_count]
    train = items[test_count + val_count:]
    return train, val, test


# ----------------------------------------------------------------------------
# YAML del dataset
# ----------------------------------------------------------------------------
def write_dataset_yaml(output_folder, has_test):
    yaml_data = {
        "train": "images/train",
        "val": "images/val",
    }
    if has_test:
        yaml_data["test"] = "images/test"
    yaml_data["names"] = dict(enumerate(CLASSES))

    # Ultralytics HUB exige que el YAML se llame como su carpeta
    folder_name = os.path.basename(os.path.normpath(output_folder))
    yaml_path = os.path.join(output_folder, f"{folder_name}.yaml")
    with open(yaml_path, "w") as f:
        yaml.dump(yaml_data, f, sort_keys=False)

    print(f"\n📘 Dataset YAML written to {yaml_path}\n")


# ----------------------------------------------------------------------------
# Pipeline
# ----------------------------------------------------------------------------
def build_yolo_dataset(input_folders, output_folder, val_fraction, test_fraction):
    # Se valida antes de escribir, para no dejar --output a medio generar
    if val_fraction + test_fraction >= 1.0:
        raise ValueError("--val-frac + --test-frac debe ser menor que 1.0")
    missing = [folder for folder in input_folders if not os.path.isdir(folder)]
    if missing:
        raise ValueError(f"No existen las carpetas de --input: {missing}")
    # Una carpeta ya usada mezclaría archivos de corridas anteriores
    if os.path.isdir(output_folder) and os.listdir(output_folder):
        raise ValueError(f"--output debe estar vacía: {output_folder}")

    items = [(folder, base)
             for folder in input_folders
             for base in list_annotation_bases(folder)]
    without_image = [os.path.join(folder, base + ".json")
                     for folder, base in items if find_image(folder, base) is None]
    if without_image:
        raise ValueError(f"JSON sin imagen: {without_image}")

    for split_name in ("train", "val", "test"):
        os.makedirs(os.path.join(output_folder, "images", split_name), exist_ok=True)
        os.makedirs(os.path.join(output_folder, "labels", split_name), exist_ok=True)

    train_set, val_set, test_set = split_dataset(items, val_fraction, test_fraction)

    print(f"\n📂 Split ({len(items)} drawings):")
    for name, split in [("Train", train_set), ("Val", val_set), ("Test", test_set)]:
        print(f"   {name}: {len(split)} drawings ({len(split) / len(items):.0%})")

    for split, split_name in [(train_set, "train"), (val_set, "val"), (test_set, "test")]:
        for folder, base in split:
            export_sample(folder, base, split_name, output_folder)

    write_dataset_yaml(output_folder, has_test=len(test_set) > 0)
    print("\n✔ YOLO dataset generated")


def main():
    parser = argparse.ArgumentParser(description="Convert LabelMe folders to a YOLO-seg dataset")
    parser.add_argument("--input", nargs="+", required=True,
                        help="LabelMe folders to pool and split (e.g. floor-plan-cad-labelme/train-00 "
                             "floor-plan-cad-labelme/train-01 floor-plan-cad-labelme/test-00)")
    parser.add_argument("--output", required=True, help="Output folder for the YOLO dataset")
    parser.add_argument("--val-frac", type=float, default=VAL_FRACTION,
                        help=f"Fraction of drawings for validation (default: {VAL_FRACTION})")
    parser.add_argument("--test-frac", type=float, default=TEST_FRACTION,
                        help=f"Fraction of drawings for test (default: {TEST_FRACTION})")
    args = parser.parse_args()

    build_yolo_dataset(args.input, args.output, args.val_frac, args.test_frac)


if __name__ == "__main__":
    main()
