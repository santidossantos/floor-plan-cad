# Plan actual

Entrenar YOLO26 con FloorPlanCAD y medir cuánto transfiere a BLD-AR.

## Etapas (en orden)
1. **Scripts** (`normalize-evaluar`, `svg-simplificar`, `labelme-simplificar`): dejar el pipeline SVG → YOLO simple, comentado en español y reproducible.
2. **Reproducibilidad** (`versiones-fijas`): fijar `ultralytics` y `sahi`.
3. **Mapeo de clases** (`mapeo-clases`): tabla BLD-AR ↔ FloorPlanCAD. Condiciona las clases que exporta `labelme_to_yolo.py`.
4. **Entrenamiento** (`augmentations-propuesta`, `notebook-entrenamiento`): necesita las etapas 2 y 3.
5. **Evaluación** (`evaluacion-sahi`): inferencia por tiles sobre BLD-AR. Necesita el mapeo y un modelo entrenado.
6. **README** (`readme-actualizar`): reflejar los cambios finales del pipeline.

Las tareas con `requiere_servidor: true` se dan por cumplidas cuando el usuario confirma que corrieron en el servidor.
