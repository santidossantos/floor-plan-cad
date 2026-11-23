# Evaluación en BLD-AR

**Decisión:** `scripts/evaluation/evaluate_bldar.ipynb` corta cada plano de BLD-AR en tiles de 1024 px con SAHI. Es el tamaño en el que los muros de BLD-AR quedan con el grosor que ve el modelo en FloorPlanCAD con imgsz 1024 (mediana de ~19 px contra ~18 px).

## Cómo se calcula el AP-Seg

Una predicción coincide con una etiqueta si son de la misma clase y sus máscaras se superponen lo suficiente: el área en común dividida por el área que cubren entre las dos (IoU) tiene que llegar al umbral.
- Cada etiqueta coincide con una sola predicción. Una predicción sin pareja cuenta como error, y una etiqueta sin pareja, como objeto no encontrado.
- Con las predicciones ordenadas por confianza se arma la curva de precisión y recall; el AP-Seg es el área bajo esa curva.
- AP50-Seg usa el umbral 0.5 y AP50-95-Seg promedia los umbrales 0.50, 0.55, …, 0.95. El mAP-Seg promedia el AP-Seg de las clases.
- El AP-Box se calcula igual, con las cajas en lugar de las máscaras.

| | Test de FloorPlanCAD | BLD-AR |
|---|---|---|
| Dónde se calcula | `model.val` de Ultralytics, en los notebooks de entrenamiento | COCOeval de pycocotools, en `evaluate_bldar.ipynb` |
| Imagen | Plano entero, a imgsz | Tiles de 1024 px; después se unen las predicciones de los tiles |
| Resolución de las máscaras al compararlas | 1/4 de imgsz (256 px con imgsz 1024) | La del plano original |
| Confianza mínima | 0.001 | 0.05 |
| Máximo de predicciones | 300 por imagen | 100 por plano y clase, las de más confianza |
| Orden para emparejar | De mayor a menor IoU | De mayor a menor confianza |
| Zonas ignoradas | Ninguna | Las clases de BLD-AR sin mapear: no cuenta lo predicho sobre ellas (área en común sobre el área de la predicción ≥ umbral) |
| Clases en el mAP-Box y el mAP-Seg | Las 30 | Las 6 mapeadas |

**Consistencia**
- Entre el test de FloorPlanCAD y BLD-AR cambia más que el conjunto: también la herramienta, la resolución de las máscaras, el máximo de predicciones y la confianza mínima. Parte de la diferencia de AP-Box y AP-Seg entre los dos conjuntos puede venir del cálculo; no se midió cuánto.
- En `docs/HISTORICO.md`, el mAP-Box y el mAP-Seg de FloorPlanCAD promedian 30 clases, y los de BLD-AR, 6. Para comparar los dos conjuntos hay que mirar clase por clase.
- La unión de predicciones de SAHI se aplica a todo el plano, aunque entre en un solo tile: también junta paredes vecinas cuyas cajas se superponen, no solo muros cortados entre tiles. Por eso el cálculo de BLD-AR también puede bajar el AP50-Seg de pared del test de FloorPlanCAD (lo mide `evaluacion-test-floorplancad-igual-bldar`).
- La prueba de la unión entre tiles (`union-paredes-entre-tiles`) debe usar el mismo cálculo que BLD-AR.
- Falta verificar si el máximo de 100 predicciones por plano y clase deja afuera paredes en los planos grandes (BLD_14 mide 15 000 × 12 000 px y se corta en cientos de tiles).

## Problema pendiente: corridas con imgsz distinto de 1024
- El notebook pasa `image_size=TILE` al modelo, así que SAHI redimensiona cada tile a 1024 px antes de la inferencia, sea cual sea el imgsz de la corrida.
- Un modelo entrenado con imgsz 640 vio muros de ~11 px y en BLD-AR recibiría muros de ~19 px: sus métricas bajarían por la escala, no por el imgsz.
- Solución propuesta, sin aplicar: un parámetro `IMGSZ` con el imgsz de la corrida, pasado como `image_size`. `TILE` queda en 1024, porque el tile equivalente no depende del imgsz.
- Mientras no se corrija, las métricas de BLD-AR de `yolo26m-seg-640` no son comparables con las de las corridas de 1024.
