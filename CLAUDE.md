# Tesis: transferencia de datos sintéticos a planos analógicos

## Objetivo
Evaluar si un modelo de detección y segmentación (YOLO) entrenado con planos sintéticos vectoriales rinde bien sobre planos analógicos reales (manchados, desgastados, con ruido o distintos tonos).

- **Entrenamiento:** FloorPlanCAD → `datasets/FloorPlanCAD` (paper: `datasets/FloorPlanCAD/FloorPlanCAD.pdf`)
- **Evaluación:** BLD-AR → `datasets/BLD-AR` (ya en formato LabelMe)
- **Referencia:** SAHI (https://github.com/obss/sahi)

`datasets/` está ignorada por git.

## En cada sesión
1. Al iniciar: leer `tasks/PROGRESS.md`, `tasks/tasks.json` y `git log --oneline -10`.
2. Cuando el usuario pida implementar una tarea de `tasks.json`, crear `tasks/CURRENT-PLAN.md` con el plan de **esa** tarea. Trabajar una sola tarea por vez.
3. Al terminar: poner `"passes": true`, eliminar `tasks/CURRENT-PLAN.md`, agregar una fila a la tabla de `tasks/PROGRESS.md` (Fecha | Título | Hecho | Notas; cada celda de 2 o 3 renglones como máximo; sin columna Siguiente, porque lo da `tasks.json`) y avisar al usuario.
4. En `tasks.json`, nunca marcar `passes: true` sin cumplir su `verificacion`, ni borrar tareas o cambiar su `verificacion` para darlas por cumplidas. Otros cambios (pasos, tareas nuevas) se proponen al usuario antes de aplicarlos.

## Forma de trabajo
- Pasos pequeños.
- Ante cualquier ambigüedad, preguntar. No inferir nada sin evidencia.
- **Nunca ejecutar localmente** scripts de entrenamiento ni de evaluación: el usuario los corre en un servidor remoto. Excepción: se pueden correr con un subconjunto pequeño de datos para testear el código implementado.
- **Nunca hacer commit ni push**: el usuario se encarga de git.
- En `tasks/`, nombrar siempre los archivos `CURRENT-PLAN.md` (plan de la tarea en curso; solo existe mientras hay una) y `PROGRESS.md` (progreso).

## Convenciones
- **Reproducibilidad:** versiones fijas de `ultralytics` y `sahi` en `requirements.txt`. Fijar esas versiones al utilizar las librerías en cualquier script o jupyter notebook; semilla aleatoria fija en los `.py`.
- **Código:** simple y estructurado, sin complejidad innecesaria. Comentarios en español.
- **Notebooks:** un título principal; primera celda de código `!nvidia-smi`; cada celda de código precedida por una celda markdown de una línea que describa lo que hace.
- **Documentación:** en español, mínima, en `.md` organizados por carpetas. Documentar hallazgos importantes de manera concisa. Los `.md` de `docs/` se nombran en mayúsculas (p. ej. `docs/NORMALIZACION.md`).

## Estructura
```
scripts/conversion/     # svg_to_json.py, labelme_to_yolo.py
scripts/evaluation/     # inferencia con SAHI
model-training/         # notebook de entrenamiento del modelo de segmentación
runs/                   # resultados de los entrenamientos
tasks/                  # tasks.json, PROGRESS.md y CURRENT-PLAN.md (solo durante una tarea)
docs/                   # mapeo de clases y hallazgos
```
