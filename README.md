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

Genera las anotaciones LabelMe JSON a partir de cada par SVG/PNG y guarda cada PNG con fondo blanco y líneas oscuras, como en los planos analógicos (ver `docs/NORMALIZACION.md`). Cada carpeta de entrada se escribe en `datasets/floor-plan-cad-labelme/<carpeta>`.

```bash
python scripts/conversion/floorplancad_to_labelme.py \
  --input  datasets/FloorPlanCAD/train-00 datasets/FloorPlanCAD/train-01 datasets/FloorPlanCAD/test-00 \
  --output datasets/floor-plan-cad-labelme
```

### 2. LabelMe → YOLO-seg

Junta las carpetas y las divide al azar en train/val/test (80/10/10). La carpeta de `--output` debe estar vacía o no existir.

```bash
python scripts/conversion/floorplancad_labeled_to_yolo.py \
  --input  datasets/floor-plan-cad-labelme/train-00 datasets/floor-plan-cad-labelme/train-01 datasets/floor-plan-cad-labelme/test-00 \
  --output datasets/floor-plan-cad-yolo
```

## 🔍 Ver anotaciones con LabelMe

[LabelMe](https://github.com/wkentaro/labelme) abre una carpeta y carga el JSON de cada imagen que tenga el mismo nombre.Se ejecuta desde el virtual env. En Linux hay que exportar `QT_QPA_PLATFORM=wayland`.

```bash
export QT_QPA_PLATFORM=wayland
labelme datasets/floor-plan-cad-labelme/train-00
```
