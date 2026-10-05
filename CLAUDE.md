# Tesis: transferencia de datos sintéticos a planos analógicos

## Objetivo
Evaluar si un modelo de detección y segmentación (YOLO) entrenado con planos sintéticos vectoriales rinde bien sobre planos analógicos reales (manchados, desgastados, con ruido o distintos tonos).

- **Entrenamiento:** FloorPlanCAD → `datasets/FloorPlanCAD` (paper: `datasets/FloorPlanCAD/FloorPlanCAD.pdf`)
- **Evaluación:** BLD-AR → `datasets/BLD-AR` (ya en formato LabelMe)
- **Referencia:** SAHI (https://github.com/obss/sahi)

`datasets/` está ignorada por git.

## Protocolo de sesión
1. Al iniciar: leer `tasks/progress.md`, `tasks/tasks.json` y `git log --oneline -10`.
2. Tomar **una sola** tarea con `"passes": false` (respetar el orden de `tasks/plan.md`).
3. Al terminar: poner `"passes": true`, agregar una entrada en `tasks/progress.md` y hacer commit.
4. En `tasks.json` solo se modifica el campo `passes`. No borrar ni reescribir tareas; si hace falta una nueva, agregarla y avisar.

## Forma de trabajo
- Pasos pequeños.
- Ante cualquier ambigüedad, preguntar. No inferir nada sin evidencia.
- **Nunca ejecutar localmente** scripts de entrenamiento ni de evaluación: el usuario los corre en un servidor remoto.

## Convenciones
- **Reproducibilidad:** versiones fijas de `ultralytics` y `sahi` en `requirements.txt`; semilla aleatoria fija en los `.py`.
- **Código:** simple y estructurado, sin complejidad innecesaria. Comentarios en español.
- **Notebooks:** un título principal; primera celda de código `!nvidia-smi`; cada celda de código precedida por una celda markdown de una línea que describa lo que hace.
- **Documentación:** en español, mínima, en `.md` organizados por carpetas. Las decisiones van en `docs/decisiones/`.

## Estructura
```
scripts/conversion/     # svg_to_json.py, labelme_to_yolo.py
scripts/preprocessing/  # normalize_dataset.py
scripts/evaluation/     # inferencia con SAHI
trainings/              # notebooks de entrenamiento
tasks/                  # plan.md, tasks.json, progress.md
docs/                   # mapeo de clases y decisiones
```
