# Plan: labelme-simplificar

Evaluar si `scripts/conversion/floorplancad_labeled_to_yolo.py` se puede simplificar y confirmar el manejo de la semilla aleatoria.

## Pasos
1. [x] Confirmar que `RANDOM_SEED` cubre todo uso de aleatoriedad (único uso: `random.shuffle` en `split_dataset`).
2. [x] Proponer simplificaciones al usuario (aprobadas: semilla local, error si falta una carpeta, error si --output no está vacía).
3. [x] Aplicar los cambios aprobados y traducir comentarios al español.
4. [x] Verificar: dos ejecuciones con las mismas entradas producen el mismo split.
5. [ ] Aprobación del script resultante por el usuario.
