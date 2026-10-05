# Tesis: transferencia de datos sintéticos a planos analógicos

## Objetivo
Evaluar si un modelo de detección y segmentación (YOLO) entrenado con planos sintéticos vectoriales rinde bien sobre planos analógicos reales (manchados, desgastados, con ruido o distintos tonos).

- **Entrenamiento:** FloorPlanCAD → `datasets/FloorPlanCAD` (paper: `datasets/FloorPlanCAD/FloorPlanCAD.pdf`)
- **Evaluación:** BLD-AR → `datasets/BLD-AR` (ya en formato LabelMe)
- **Referencia:** SAHI (https://github.com/obss/sahi)

`datasets/` está ignorada por git.

## En cada sesión
1. Al iniciar: leer `tasks/PROGRESS.md`, `tasks/tasks.json` y `git log --oneline -10`.
2. Cuando el usuario pida implementar una tarea de `tasks.json`, poner su `"status": "in progress"` y crear `tasks/CURRENT-PLAN.md` con el plan de **esa** tarea. Trabajar una sola tarea por vez.
3. Al terminar: poner `"status": "done"`, eliminar `tasks/CURRENT-PLAN.md`, agregar una fila a la tabla de `tasks/PROGRESS.md` (Fecha | Título | Hecho | Notas; cada celda de 2 o 3 renglones como máximo; sin columna Siguiente, porque lo da `tasks.json`) y avisar al usuario.
4. En `tasks.json`, el campo `status` vale `not started`, `in progress` o `done`. Nunca marcar `done` sin cumplir su `verificacion`, ni borrar tareas o cambiar su `verificacion` para darlas por cumplidas. Otros cambios (pasos, tareas nuevas) se proponen al usuario antes de aplicarlos.

## Forma de trabajo
- Pasos pequeños.
- Ante cualquier ambigüedad, preguntar. No inferir nada sin evidencia.
- **Nunca ejecutar localmente** scripts de entrenamiento ni de evaluación: el usuario los corre en un servidor remoto. Excepción: se pueden correr con un subconjunto pequeño de datos para testear el código implementado.
- **Nunca hacer commit ni push**: el usuario se encarga de git.
- En `tasks/`, nombrar siempre los archivos `CURRENT-PLAN.md` (plan de la tarea en curso; solo existe mientras hay una) y `PROGRESS.md` (progreso).
- En `CURRENT-PLAN.md`, presentar los pasos como una lista bajo un título `Pasos`, con `[x]` (hecho) o `[ ]` (pendiente) y una línea por paso. Si la tarea crea o modifica un script, el último paso del plan es siempre `[ ] Aprobación del script resultante por el usuario.`

## Convenciones
- **Reproducibilidad:** usar las versiones de `ultralytics`, `sahi` y `albumentations` de `docs/VERSIONES.md` al instalar esas librerías en cualquier script o jupyter notebook; semilla aleatoria fija en los `.py`.
- **Código:** simple y estructurado, sin complejidad innecesaria. Comentarios en español, solo donde aclaran algo que el código no dice. No agregar código, salidas ni archivos que la tarea no pida; si algo parece útil, proponerlo antes.
- **Nombres de archivos:** los scripts y notebooks se nombran por lo que hacen, sin nombres de tecnologías ni versiones de librerías (p. ej. `train_segmentation_model.ipynb`, no `train_yolo26_seg.ipynb`).
- **Entrenamientos:** cuando el usuario deje una corrida en `runs/` (con su `.csv` y `best.pt`), analizar los resultados y agregar una fila a `runs/HISTORICO.md`: tabla legible con el modelo, el `imgsz` y solo métricas sobre el test de FloorPlanCAD (mAP50 y mAP50-95 de box y seg).
- **Notebooks:** un título principal; primera celda de código `!nvidia-smi`; cada celda de código, salvo `!nvidia-smi` y la instalación de librerías, precedida por una celda markdown de una línea que describa lo que hace.
- **Documentación:** en español, mínima, en `.md` organizados por carpetas. Documentar hallazgos importantes de manera concisa. Los `.md` de `docs/` se nombran en mayúsculas (p. ej. `docs/NORMALIZACION.md`).

## Estructura
```
scripts/conversion/     # floorplancad_to_labelme.py, floorplancad_labeled_to_yolo.py
scripts/evaluation/     # inferencia con SAHI
scripts/model-training/ # notebook de entrenamiento del modelo de segmentación
runs/                   # resultados de los entrenamientos e HISTORICO.md
tasks/                  # tasks.json, PROGRESS.md y CURRENT-PLAN.md (solo durante una tarea)
docs/                   # mapeo de clases y hallazgos
docs/VERSIONES.md       # versiones de ultralytics, sahi y albumentations
```
