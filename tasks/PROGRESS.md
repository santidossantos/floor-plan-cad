# Progreso

| Fecha | Título | Hecho | Notas |
|---|---|---|---|
| 2026-10-05 | normalize-evaluar | Normalización integrada en `floorplancad_to_labelme.py`; se eliminó `normalize_dataset.py`. Decisión en `docs/NORMALIZACION.md`. | Probado con 9 planos: genera los mismos JSON y PNG que antes generaban `floorplancad_to_labelme.py` + `normalize_dataset.py`. |
| 2026-10-05 | svg-simplificar | `floorplancad_to_labelme.py` de 900 a 763 líneas: sin código muerto ni duplicados; comentarios en español. `--input` acepta varias carpetas. | Probado con 110 planos: genera los mismos JSON y PNG que la versión anterior. El dataset solo tiene `path`, `circle` y `ellipse`. |
| 2026-10-05 | renombrar-scripts | `svg_to_json.py` → `floorplancad_to_labelme.py` y `labelme_to_yolo.py` → `floorplancad_labeled_to_yolo.py`. Referencias actualizadas. | Pipeline probado con 8 planos con los nombres nuevos. |
| 2026-10-05 | svg-paredes | wall: un polígono por pared ("pared pasante"), relleno entre caras y cortes en los encuentros; solo semantic-id 1. Decisión en `docs/PAREDES.md`. | 110 planos: 2 329 → 1 015 paredes, demás clases idénticas. ~0.09 s por plano. |
