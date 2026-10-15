# Plan: evaluacion-bldar-corridas

Métricas en BLD-AR de las 5 corridas, con `scripts/evaluation/evaluate_segmentation_model.ipynb`.

## Pasos
1. [x] El usuario corre la evaluación de 00, 01, 02 y 03 en el servidor y deja el notebook en cada corrida de `runs/`.
2. [x] Revisar que cada notebook use los pesos de su corrida y el código aprobado.
3. [x] Analizar los resultados, incluidas las tablas por clase.
4. [x] Completar las columnas de BLD-AR de 00, 01, 02 y 03 en `runs/HISTORICO.md`.
5. [x] Documentar en `runs/HISTORICO.md` las augmentations de yolo26m-seg-bldar-1024.
6. [ ] Evaluar yolo26m-seg-640, después de resolver el problema de `docs/EVALUACION.md`.
