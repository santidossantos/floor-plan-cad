# Evaluación en BLD-AR

**Decisión:** `scripts/evaluation/evaluate_bldar.ipynb` evalúa BLD-AR cortando cada plano en tiles de 1024 px con SAHI. Con ese tamaño, los muros de BLD-AR quedan con el grosor que el modelo vio en FloorPlanCAD con imgsz 1024 (mediana de ~19 px contra ~18 px). Qué hace SAHI y cómo une las predicciones: `docs/DIAGNOSTICO_MALA_TRANSFERENCIA.md`.

## Cómo se calcula el AP-Seg

Cada predicción tiene una máscara (la forma del objeto, píxel a píxel) y una caja (el rectángulo más chico que la contiene). Una predicción coincide con una etiqueta si son de la misma clase y sus máscaras se superponen lo suficiente: el área en común dividida por el área que cubren entre las dos (IoU) tiene que llegar al umbral.
- Cada etiqueta coincide con una sola predicción. Una predicción sin pareja cuenta como error, y una etiqueta sin pareja, como objeto no encontrado.
- Con las predicciones ordenadas por confianza se arma la curva de precisión y recall; el AP-Seg es el área bajo esa curva.
- AP50-Seg usa el umbral 0.5 y AP50-95-Seg promedia los umbrales 0.50, 0.55, …, 0.95. El mAP-Seg promedia el AP-Seg de las clases.
- El AP-Box se calcula igual, con las cajas en lugar de las máscaras.

**Dos umbrales que no hay que confundir**

| | Qué decide | Valor | Si se sube |
|---|---|---|---|
| Umbral de IoU | Cuánto se tiene que superponer la máscara predicha con la etiqueta para contar como acierto | 0.5 en AP50-Seg; de 0.50 a 0.95 en AP50-95-Seg | Hay que dibujar el objeto con más precisión: el AP-Seg baja |
| Confianza mínima | Qué tan seguro tiene que estar el modelo de una predicción para no descartarla antes de evaluar | 0.001 en el cálculo del conjunto de test de FloorPlanCAD; 0.05 en el de BLD-AR | Se pierden las predicciones dudosas, algunas de ellas aciertos: el AP-Seg baja o queda igual |

- **Ejemplo de IoU:** wall en el conjunto de test de FloorPlanCAD (`01-YOLO26l-SEG-1024`, cálculo del conjunto de test de FloorPlanCAD) tiene AP50-Seg 0.828 y AP50-95-Seg 0.510. El modelo encuentra las paredes, pero sus bordes no coinciden al detalle con la etiqueta.
- **Por qué se evalúa con confianza baja:** el AP-Seg resume toda la curva, desde las predicciones más seguras hasta las más dudosas, y subir la confianza corta su parte final. Una confianza alta, como el 0.25 de las visualizaciones, sirve para mostrar resultados, no para medir. En el cálculo de BLD-AR, la confianza además decide qué predicciones entran en la unión de SAHI.

## Los dos cálculos

El AP-Seg del conjunto de test de FloorPlanCAD de `docs/HISTORICO.md` y el de BLD-AR no se calculan igual. Cada cálculo lleva el nombre del conjunto en el que se usa normalmente:

| | Cálculo del conjunto de test de FloorPlanCAD | Cálculo de BLD-AR |
|---|---|---|
| Dónde se calcula | `model.val` de Ultralytics, en los notebooks de entrenamiento | COCOeval de pycocotools, en `evaluate_bldar.ipynb` |
| Imagen | Plano entero, a imgsz | Tiles de 1024 px con SAHI, y después la unión de sus predicciones |
| Resolución de las máscaras al compararlas | 1/4 de imgsz (256 px con imgsz 1024) | La del plano original |
| Confianza mínima | 0.001 | 0.05 |
| Máximo de predicciones | 300 por imagen | 100 por plano y clase, las de más confianza |
| Orden para emparejar | De mayor a menor IoU | De mayor a menor confianza |
| Zonas ignoradas | Ninguna | Las clases de BLD-AR sin mapear: no cuenta lo predicho sobre ellas (área en común sobre el área de la predicción ≥ umbral) |
| Clases en el mAP-Box y el mAP-Seg | Las 30 | Las 6 mapeadas |

**Consistencia**
- Entre el conjunto de test de FloorPlanCAD y BLD-AR cambia más que el conjunto: también la herramienta, la resolución de las máscaras, el máximo de predicciones y la confianza mínima. En el AP-Seg pesa poco (ver `docs/DIAGNOSTICO_MALA_TRANSFERENCIA.md`); en el AP-Box no se midió.
- En `docs/HISTORICO.md`, el mAP-Box y el mAP-Seg de FloorPlanCAD promedian 30 clases, y los de BLD-AR, 6. Para comparar los dos conjuntos hay que mirar clase por clase.
- La unión de predicciones de SAHI baja el AP50-Seg de wall aunque el plano entre en un solo tile: en el conjunto de test de FloorPlanCAD, de 0.803 a 0.664 (ver `docs/DIAGNOSTICO_MALA_TRANSFERENCIA.md`).
- Falta verificar si el máximo de 100 predicciones por plano y clase deja afuera paredes en los planos grandes (BLD_14 mide 15 000 × 12 000 px y se corta en cientos de tiles). En el conjunto de test de FloorPlanCAD no recorta: ningún plano tiene más de 86 etiquetas de una clase.

## Problema pendiente: corridas con imgsz distinto de 1024
- El notebook pasa `image_size=TILE` al modelo, así que SAHI redimensiona cada tile a 1024 px antes de la inferencia, sea cual sea el imgsz de la corrida.
- Un modelo entrenado con imgsz 640 vio muros de ~11 px y en BLD-AR recibiría muros de ~19 px: sus métricas bajarían por la escala, no por el imgsz.
- Solución propuesta, sin aplicar: un parámetro `IMGSZ` con el imgsz de la corrida, pasado como `image_size`. `TILE` queda en 1024, porque el tile equivalente no depende del imgsz.
- Mientras no se corrija, las métricas de BLD-AR de `yolo26m-seg-640` no son comparables con las de las corridas de 1024.
