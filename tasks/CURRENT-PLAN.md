# Plan: determinar-costo-calculo-sahi-floorplancad-vs-bldar

**Pregunta:** ¿cuánto de la diferencia entre el mAP50-Seg del conjunto de test de FloorPlanCAD (0.82) y el de BLD-AR (0.32), en las 6 clases mapeadas, viene de que se calculan distinto? Y, de eso, ¿cuánto aporta la unión de SAHI?

## Decisiones
- Corrida `01-YOLO26l-SEG-1024` sobre el conjunto de test de FloorPlanCAD: 1 566 planos de hasta 1 000 px, así que cada uno entra en un solo tile.
- Clases: las 6 de `docs/MAPEO_CLASES.md`. Las otras 24 son zonas ignoradas, como en BLD-AR.
- Tres cálculos:
  - el del conjunto de test de FloorPlanCAD (`model.val`);
  - el de BLD-AR (`evaluate_bldar.ipynb`);
  - el de BLD-AR sin la unión.
- Sin la unión se usa `get_prediction` de SAHI. En SAHI 0.12.8, un plano de un solo tile da la misma inferencia que `get_sliced_prediction`, pero sin la unión.
- Ya medido: el cálculo explica el 4 % de la caída del mAP50-Seg, y wall baja de 0.828 a 0.664 con el cálculo de BLD-AR.
- La unión en BLD-AR (multi-tile) queda para `union-paredes-entre-tiles`.
- Resultados y hallazgos en `docs/DIAGNOSTICO_MALA_TRANSFERENCIA.md`; el método queda en `docs/EVALUACION.md`.

## Pasos
- [x] Acordar con el usuario las zonas ignoradas, la referencia y la visualización
- [x] Crear `scripts/evaluation/compare_evaluation_methods.ipynb` con la corrida `01-YOLO26l-SEG-1024`
- [x] El usuario lo corre en el servidor
- [x] Anotar el resultado de los dos cálculos
- [x] Mover el diagnóstico y lo de SAHI de `docs/EVALUACION.md` a `docs/DIAGNOSTICO_MALA_TRANSFERENCIA.md`
- [x] Agregar al notebook el cálculo de BLD-AR sin la unión de SAHI
- [x] El usuario lo vuelve a correr en el servidor
- [x] Anotar en `docs/DIAGNOSTICO_MALA_TRANSFERENCIA.md` el AP50-Seg y el AP50-95-Seg por clase con los tres cálculos
- [ ] Aprobación del script resultante por el usuario.
