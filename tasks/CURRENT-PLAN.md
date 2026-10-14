# Plan: crear-script-evaluacion-sahi

Inferencia por tiles con SAHI sobre BLD-AR y cálculo de métricas con el mapeo de `docs/MAPEO_CLASES.md`.

## Pasos
1. [x] Revisar qué soporta SAHI 0.12.8 con los modelos de segmentación de Ultralytics 8.4.173.
2. [x] Medir la escala de los planos de BLD-AR frente a la de FloorPlanCAD, para elegir el tamaño de tile.
3. [x] Definir con el usuario tamaño de tile, solapamiento, métricas y qué hacer con las regiones de clases excluidas.
4. [x] Implementar la evaluación en `scripts/evaluation/` aplicando el mapeo de clases.
5. [x] Testear localmente con un subconjunto chico de BLD-AR.
6. [x] Agregar una celda para revisar a ojo las predicciones de un plano, sin wall.
7. [x] Aprobación del script resultante por el usuario.
