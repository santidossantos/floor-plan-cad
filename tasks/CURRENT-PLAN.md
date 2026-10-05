# Plan: notebook-entrenamiento

Notebook que entrena YOLO26-seg sobre FloorPlanCAD (`imgsz=720`, `batch=4`) y evalúa sobre su split de test.

## Pasos
1. [x] Definir con el usuario ubicación (`scripts/model-training/`), modelo (`yolo26m-seg`) y prueba local (no: solo validar estructura).
2. [x] Proponer augmentations para la transferencia a planos analógicos y que el usuario las apruebe (aprobadas; albumentations==2.0.8 en `docs/VERSIONES.md`).
3. [x] Crear el notebook respetando el formato de `CLAUDE.md` (semilla fija, versiones de `docs/VERSIONES.md`).
4. [x] Agregar la sección de evaluación sobre test con tabla de mAP50 y mAP50-95 (box y seg).
5. [x] Validar la estructura del notebook (sin prueba local, por decisión del usuario).
6. [x] Agregar a `CLAUDE.md` la regla del histórico de entrenamientos en `runs/`.
7. [ ] Tras la corrida en el servidor: analizar resultados y crear el `.md` histórico en `runs/` (solo métricas de test, más el modelo y el imgsz de cada entrenamiento).
8. [x] Aprobación del script resultante por el usuario.
