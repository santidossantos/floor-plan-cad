# Plan: svg-simplificar

Evaluar si `scripts/conversion/svg_to_json.py` se puede simplificar.

## Pasos
1. [x] Guardar copia del script actual y su salida sobre una muestra de SVG (referencia).
2. [x] Identificar código muerto, duplicado o abstracciones innecesarias.
3. [x] Proponer cambios al usuario (aprobados: código muerto, duplicados, ABC).
4. [x] Aplicar los cambios aprobados y traducir comentarios al español.
5. [x] Verificar: salida LabelMe idéntica a la de referencia (110 planos, JSON y PNG byte a byte).
6. [x] `--input` acepta varias carpetas; README sin el `for`.
7. [ ] Aprobación del script resultante por el usuario.
