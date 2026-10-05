# Progreso

| Fecha | Título | Hecho | Notas |
|---|---|---|---|
| 2026-10-05 | normalize-evaluar | Normalización integrada en `floorplancad_to_labelme.py`; se eliminó `normalize_dataset.py`. Decisión en `docs/NORMALIZACION.md`. | Probado con 9 planos: genera los mismos JSON y PNG que antes generaban `floorplancad_to_labelme.py` + `normalize_dataset.py`. |
| 2026-10-05 | svg-simplificar | `floorplancad_to_labelme.py` de 900 a 763 líneas: sin código muerto ni duplicados; comentarios en español. `--input` acepta varias carpetas. | Probado con 110 planos: genera los mismos JSON y PNG que la versión anterior. El dataset solo tiene `path`, `circle` y `ellipse`. |
| 2026-10-05 | renombrar-scripts | `svg_to_json.py` → `floorplancad_to_labelme.py` y `labelme_to_yolo.py` → `floorplancad_labeled_to_yolo.py`. Referencias actualizadas. | Pipeline probado con 8 planos con los nombres nuevos. |
| 2026-10-05 | svg-paredes | wall: un polígono por pared ("pared pasante"), relleno entre caras y cortes en los encuentros; solo semantic-id 1. Decisión en `docs/PAREDES.md`. | 110 planos: 2 329 → 1 015 paredes, demás clases idénticas. ~0.09 s por plano. |
| 2026-10-05 | svg-elipses-rotadas | Se aplica el `rotate(a, cx, cy)` de las elipses al muestrear puntos y al armar polígonos. | 80 planos: cambian 54 de 243 sink y 1 de 71 table; el resto, idéntico. |
| 2026-10-05 | labelme-simplificar | Semilla local en `split_dataset`; error si falta una carpeta de `--dataset` o si `--output` no está vacía; comentarios en español. | El único uso de aleatoriedad es el shuffle del split. Dos ejecuciones dan archivos idénticos, también a la versión anterior. |
| 2026-10-05 | versiones-fijas | Se fijan las versiones que utilizarán los Notebooks que contengan Ultralytics y/o Sahi en `docs/VERSIONES.md`
| 2026-10-05 | convert-to-yolo | Conversor a YOLO: ids de clase fijos, polígonos recortados al borde, duplicados por línea idéntica, validación antes de escribir y `--input`. README actualizado. | Split 80/10/10 sin cambios; solo cambian las 11 591 formas que salían de la imagen. |
