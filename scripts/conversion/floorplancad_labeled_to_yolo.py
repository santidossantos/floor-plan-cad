"""Convert LabelMe-annotated folders into a YOLO-seg dataset.

All --dataset folders are pooled and split randomly into train/val/test
(80/10/10 by default). Files sharing a name across folders are prefixed with
their folder name to avoid collisions.
"""

import argparse
import json
import os
import random
import shutil

import yaml

RANDOM_SEED = 42

VAL_FRACTION = 0.1
TEST_FRACTION = 0.1

EXCLUDED_CLASSES = {"fire_door", "wall_move", "revolving_door", "parking", "cinema_chair"}

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")

# Ultralytics drops segments that are equal after rounding to 5 decimals;
# deduplicating with the same key avoids its training-time warnings.
DEDUP_DECIMALS = 5


# ----------------------------------------------------------------------------
# Annotation discovery
# ----------------------------------------------------------------------------
def list_annotation_bases(folder):
    """Return the sorted base names of all LabelMe JSON files in a folder."""
    if not os.path.exists(folder):
        return []
    return sorted(os.path.splitext(f)[0] for f in os.listdir(folder) if f.endswith(".json"))


def load_labelme_json(json_path):
    with open(json_path, "r") as f:
        return json.load(f)


def build_class_map(folders):
    """Scan every annotation and map each non-excluded label to a class id."""
    classes = set()
    for folder in folders:
        for base in list_annotation_bases(folder):
            data = load_labelme_json(os.path.join(folder, base + ".json"))
            for shape in data.get("shapes", []):
                if shape["label"] not in EXCLUDED_CLASSES:
                    classes.add(shape["label"])
    return {label: i for i, label in enumerate(sorted(classes))}


# ----------------------------------------------------------------------------
# Annotation conversion
# ----------------------------------------------------------------------------
def normalize_polygon(points, width, height):
    """Convert absolute polygon points to normalized YOLO-seg coordinates."""
    normalized = []
    for x, y in points:
        normalized.extend([
            max(0.0, min(1.0, x / width)),
            max(0.0, min(1.0, y / height)),
        ])
    return normalized


def dedup_key(line):
    """Key that treats two label lines as equal after coordinate rounding."""
    class_id, *coords = line.split()
    return " ".join([class_id] + [f"{round(float(v), DEDUP_DECIMALS)}" for v in coords])


def convert_annotation(json_path, label_path, class_map):
    """Write one LabelMe JSON as a YOLO-seg .txt file, skipping duplicates."""
    data = load_labelme_json(json_path)
    width, height = data["imageWidth"], data["imageHeight"]

    lines, seen = [], set()
    for shape in data.get("shapes", []):
        if shape["label"] in EXCLUDED_CLASSES:
            continue
        class_id = class_map[shape["label"]]
        coords = normalize_polygon(shape["points"], width, height)
        line = f"{class_id} " + " ".join(f"{p:.6f}" for p in coords)
        key = dedup_key(line)
        if key not in seen:
            seen.add(key)
            lines.append(line)

    with open(label_path, "w") as f:
        f.write("\n".join(lines))


# ----------------------------------------------------------------------------
# Sample export
# ----------------------------------------------------------------------------
def find_image(folder, base):
    """Return the path of the image paired with an annotation, or None."""
    for ext in IMAGE_EXTENSIONS:
        image_path = os.path.join(folder, base + ext)
        if os.path.exists(image_path):
            return image_path
    return None


def export_sample(folder, base, split_name, output_folder, class_map):
    """Export one annotation+image pair into a dataset split.

    The output name is prefixed with the source folder name so that files
    sharing a base name across folders do not overwrite each other.
    """
    out_base = f"{os.path.basename(os.path.normpath(folder))}_{base}"

    label_path = os.path.join(output_folder, "labels", split_name, out_base + ".txt")
    convert_annotation(os.path.join(folder, base + ".json"), label_path, class_map)

    image_path = find_image(folder, base)
    if image_path:
        ext = os.path.splitext(image_path)[1]
        shutil.copy(image_path, os.path.join(output_folder, "images", split_name, out_base + ext))


# ----------------------------------------------------------------------------
# Train / val / test split
# ----------------------------------------------------------------------------
def split_dataset(items, val_fraction, test_fraction):
    """Split drawings randomly into train/val/test by the given fractions."""
    if val_fraction + test_fraction >= 1.0:
        raise ValueError("--val-frac + --test-frac must be smaller than 1.0")

    items = sorted(items)
    random.shuffle(items)

    val_count = round(len(items) * val_fraction)
    test_count = round(len(items) * test_fraction)

    test = items[:test_count]
    val = items[test_count:test_count + val_count]
    train = items[test_count + val_count:]
    return train, val, test


# ----------------------------------------------------------------------------
# Dataset YAML
# ----------------------------------------------------------------------------
def write_dataset_yaml(output_folder, class_map, has_test):
    yaml_data = {
        "train": "images/train",
        "val": "images/val",
    }
    if has_test:
        yaml_data["test"] = "images/test"
    yaml_data["names"] = {class_id: label for label, class_id in class_map.items()}

    # Ultralytics HUB requires the YAML to be named after its folder.
    folder_name = os.path.basename(os.path.normpath(output_folder))
    yaml_path = os.path.join(output_folder, f"{folder_name}.yaml")
    with open(yaml_path, "w") as f:
        yaml.dump(yaml_data, f, sort_keys=False)

    print(f"\n📘 Dataset YAML written to {yaml_path}\n")


# ----------------------------------------------------------------------------
# Pipeline
# ----------------------------------------------------------------------------
def build_yolo_dataset(dataset_folders, output_folder, val_fraction, test_fraction):
    for split_name in ("train", "val", "test"):
        os.makedirs(os.path.join(output_folder, "images", split_name), exist_ok=True)
        os.makedirs(os.path.join(output_folder, "labels", split_name), exist_ok=True)

    class_map = build_class_map(dataset_folders)
    print("\n📌 Detected classes:")
    for label, class_id in class_map.items():
        print(f"   {class_id}: {label}")

    items = [(folder, base)
             for folder in dataset_folders
             for base in list_annotation_bases(folder)]
    train_set, val_set, test_set = split_dataset(items, val_fraction, test_fraction)

    print(f"\n📂 Split ({len(items)} drawings):")
    for name, split in [("Train", train_set), ("Val", val_set), ("Test", test_set)]:
        print(f"   {name}: {len(split)} drawings ({len(split) / len(items):.0%})")

    for split, split_name in [(train_set, "train"), (val_set, "val"), (test_set, "test")]:
        for folder, base in split:
            export_sample(folder, base, split_name, output_folder, class_map)

    write_dataset_yaml(output_folder, class_map, has_test=len(test_set) > 0)
    print("\n✔ YOLO dataset generated")


def main():
    parser = argparse.ArgumentParser(description="Convert LabelMe folders to a YOLO-seg dataset")
    parser.add_argument("--dataset", nargs="+", required=True,
                        help="LabelMe folders to pool and split (e.g. labeled-train-00 "
                             "labeled-train-01 labeled-test-00)")
    parser.add_argument("--output", required=True, help="Output folder for the YOLO dataset")
    parser.add_argument("--val-frac", type=float, default=VAL_FRACTION,
                        help=f"Fraction of drawings for validation (default: {VAL_FRACTION})")
    parser.add_argument("--test-frac", type=float, default=TEST_FRACTION,
                        help=f"Fraction of drawings for test (default: {TEST_FRACTION})")
    args = parser.parse_args()

    random.seed(RANDOM_SEED)
    build_yolo_dataset(args.dataset, args.output, args.val_frac, args.test_frac)


if __name__ == "__main__":
    main()
