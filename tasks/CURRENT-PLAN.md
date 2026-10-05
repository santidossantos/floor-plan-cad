# Plan: svg-paredes

Generar un polígono por pared en `floorplancad_to_labelme.py`, en lugar de los polígonos actuales.

## Pasos
1. [x] Analizar cómo se representan las paredes en los SVG (paths, instance-id, capas) y cómo se anotan en BLD-AR.
2. [x] Proponer al usuario un criterio para determinar dónde corta cada pared (aprobado: pared pasante; wall solo por semantic-id 1).
3. [x] Implementar el criterio aprobado (`WallDetector`; decisión en `docs/PAREDES.md`).
4. [ ] Comparar visualmente las anotaciones de wall antes y después sobre una muestra de planos (6 comparaciones listas; falta tu revisión).
5. [ ] Aprobación del script resultante por el usuario.
