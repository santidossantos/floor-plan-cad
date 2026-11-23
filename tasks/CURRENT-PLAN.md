# Plan: evaluacion-test-floorplancad-igual-bldar

**Pregunta:** ¿cuánto de la diferencia entre el mAP50-Seg del test de FloorPlanCAD (0.82) y el de BLD-AR (0.32), en las 6 clases mapeadas, viene de que se calculan distinto?

## Decisiones
- Corrida 01 sobre el test de FloorPlanCAD: 1 566 planos de hasta 1 000 px, así que cada uno entra en un solo tile.
- Clases: las 6 de `docs/MAPEO_CLASES.md` (wall, single_door, window, sliding_door, stair, elevator). Las otras 24 son zonas ignoradas, como en BLD-AR.
- Cálculo de BLD-AR: los mismos parámetros que `evaluate_bldar.ipynb` (tiles de 1024, solapamiento 0.2, confianza 0.05, unión de SAHI forzada y COCOeval).
- Referencia: `model.val` de Ultralytics, corrido en el mismo notebook para que los dos cálculos usen el mismo entorno.
- Solo AP-Seg, que es lo que pide la verificación.
- Tabla resumen con la media de las 6 clases y la parte de la diferencia que viene del cálculo. El valor de BLD-AR (0.324 y 0.140) se toma de `docs/HISTORICO.md`.
- Visualización: un plano del test y uno de BLD-AR, con etiqueta y predicción lado a lado y máscaras rellenas por clase (wall incluida).
- Sin prueba local del modelo, porque no hay GPU ni librerías. Localmente se probó el armado de etiquetas COCO: da las mismas instancias por clase que Ultralytics en el test.

## Pasos
- [x] Acordar con el usuario las zonas ignoradas, la referencia y la visualización
- [x] Crear `scripts/evaluation/compare_evaluation_methods.ipynb` con la corrida 01
- [ ] El usuario lo corre en el servidor
- [ ] Anotar en `docs/EVALUACION.md` el AP50-Seg y el AP50-95-Seg por clase con los dos cálculos
- [ ] Aprobación del script resultante por el usuario.
