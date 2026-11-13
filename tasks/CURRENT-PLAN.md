# Plan: evaluacion-test-floorplancad-igual-bldar

**Pregunta:** ¿cuánto de la diferencia entre el AP50 de seg de pared del test de FloorPlanCAD (0.82) y el de BLD-AR (0.12) viene de que se calculan distinto?

## Variantes
Las tres evalúan el test completo de FloorPlanCAD con la corrida 00 y el cálculo de BLD-AR (COCOeval, confianza 0.05). Cada plano mide ~1 000 px y entra en un solo tile.
1. **Tal cual:** como en BLD-AR, con la unión de predicciones de SAHI.
2. **Sin unir predicciones:** la diferencia con (1) da cuánto cuesta la unión.
3. **Sin unir y con las máscaras a 1/4 de la imagen, como Ultralytics:** la diferencia con (2) da cuánto cuesta la resolución.

## Pasos
- [x] Acordar con el usuario qué clases se evalúan: las 7 mapeadas a BLD-AR, más una columna de referencia con el cálculo de Ultralytics (model.val) en el mismo notebook
- [x] Crear el notebook en scripts/evaluation/, con las tres variantes y una nota que explique qué intenta explicar cada una
- [x] Probarlo localmente con pocos planos
- [ ] El usuario lo corre en el servidor
- [ ] Anotar el resultado en docs/EVALUACION.md
- [ ] Aprobación del script resultante por el usuario.
