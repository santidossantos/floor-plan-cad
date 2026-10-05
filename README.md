# FloorPlanCAD → YOLO

Pipeline para convertir los planos de **FloorPlanCAD** (SVG) en un dataset de segmentación YOLO.

## 📦 Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 📁 Datos

Coloca los datasets en `datasets/` (ignorado por git):

```
datasets/
└── FloorPlanCAD/
    ├── train-00/
    ├── train-01/
    └── test-00/
```

## 🚀 Pipeline

### 1. SVG → LabelMe

Genera las anotaciones LabelMe JSON a partir de cada par SVG/PNG y guarda cada PNG con fondo blanco y líneas oscuras, como en los planos analógicos (ver `docs/NORMALIZACION.md`).

```bash
for split in train-00 train-01 test-00; do
  python scripts/conversion/svg_to_json.py \
    --input  datasets/FloorPlanCAD/$split \
    --output datasets/labeled/$split
done
```

### 2. LabelMe → YOLO-seg

Junta las carpetas y las divide en train/val/test (80/10/10).

```bash
python scripts/conversion/labelme_to_yolo.py \
  --dataset datasets/labeled/train-00 datasets/labeled/train-01 datasets/labeled/test-00 \
  --output  datasets/yolo
```
