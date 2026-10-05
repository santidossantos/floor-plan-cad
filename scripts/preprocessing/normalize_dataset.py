"""Normalize a FloorPlanCAD YOLO dataset to white background / dark lines.

FloorPlanCAD PNGs are RGBA with a transparent background, which loads as black
in RGB — the opposite polarity of real analog plans (BLD-AR: white background,
dark lines). A model trained on the black-background renders does not transfer
to analog plans: inverting the polarity alone collapses the test Box mAP50-95
from 0.517 to 0.038 (see POLARITY-FINDING.md).

This rebuilds a YOLO dataset with every image converted to white background /
dark lines, using the alpha channel as a color-agnostic stroke mask so that
bright line colors (e.g. cyan) do not wash out into faint grays. Annotations
are copied unchanged, since inverting pixels does not move coordinates.
"""

import argparse
import glob
import os
import shutil

import numpy as np
import yaml
from PIL import Image

SPLITS = ("train", "val", "test")
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")

# Thin anti-aliased strokes rarely reach full opacity (they cover part of a
# pixel), so a plain 255-alpha leaves them faint gray. Amplifying the stroke
# signal before inverting drives real strokes to near-black while keeping a
# soft anti-aliased edge and leaving the background white.
INK_GAIN = 4


def normalize_image(image):
    """Return a white-background / dark-line RGB copy of a FloorPlanCAD image.

    The stroke signal comes from the alpha channel when present (color-agnostic,
    so bright line colors like cyan do not wash out); otherwise it falls back to
    the luminance of the black-background render. Either way, amplified by
    INK_GAIN: background -> 255 (white), stroke -> near-black.
    """
    if image.mode == "RGBA":
        stroke = np.asarray(image.getchannel("A"), dtype=np.int16)
    else:
        stroke = np.asarray(image.convert("L"), dtype=np.int16)
    ink = 255 - np.clip(stroke * INK_GAIN, 0, 255)
    return Image.fromarray(ink.astype("uint8")).convert("RGB")


def normalize_split_images(images_dir, output_dir):
    """Normalize every image in a split, saving lossless PNGs with the same stem."""
    os.makedirs(output_dir, exist_ok=True)
    count = 0
    for name in sorted(os.listdir(images_dir)):
        if name.lower().endswith(IMAGE_EXTENSIONS):
            normalized = normalize_image(Image.open(os.path.join(images_dir, name)))
            normalized.save(os.path.join(output_dir, os.path.splitext(name)[0] + ".png"))
            count += 1
    return count


def copy_dataset_yaml(input_root, output_root):
    """Copy the dataset YAML, renamed after the output folder (HUB convention)."""
    source_yaml = glob.glob(os.path.join(input_root, "*.yaml"))[0]
    with open(source_yaml) as f:
        config = yaml.safe_load(f)
    folder_name = os.path.basename(os.path.normpath(output_root))
    with open(os.path.join(output_root, f"{folder_name}.yaml"), "w") as f:
        yaml.dump(config, f, sort_keys=False)


def build_normalized_dataset(input_root, output_root):
    for split in SPLITS:
        images_dir = os.path.join(input_root, "images", split)
        if not os.path.isdir(images_dir):
            continue

        count = normalize_split_images(images_dir, os.path.join(output_root, "images", split))

        labels_dir = os.path.join(input_root, "labels", split)
        if os.path.isdir(labels_dir):
            shutil.copytree(labels_dir, os.path.join(output_root, "labels", split), dirs_exist_ok=True)

        print(f"   {split}: {count} images normalized")

    copy_dataset_yaml(input_root, output_root)
    print(f"\n✔ Normalized dataset written to {output_root}")


def main():
    parser = argparse.ArgumentParser(
        description="Normalize a FloorPlanCAD YOLO dataset to white background / dark lines")
    parser.add_argument("--input", required=True, help="Source YOLO dataset root")
    parser.add_argument("--output", required=True, help="Output folder for the normalized dataset")
    args = parser.parse_args()

    build_normalized_dataset(args.input, args.output)


if __name__ == "__main__":
    main()
