# Evaluación en BLD-AR

**Decisión:** `scripts/evaluation/evaluate_bldar.ipynb` corta cada plano de BLD-AR en tiles de 1024 px con SAHI. Así los muros quedan del grosor que el modelo vio al entrenar (~19 px contra ~18 px). Qué hace SAHI: `docs/CAIDA_RENDIMIENTO_BLDAR.md`, sección 1.1.

## Cómo se calcula el AP50-Seg

Una predicción acierta si es de la clase de la etiqueta y sus máscaras se superponen al menos un 50 % (IoU ≥ 0.5); cada etiqueta acepta una sola predicción. El AP50-Seg es el área bajo la curva de precisión y recall, y el mAP50-Seg, su media entre clases. El AP50-Box es igual, con cajas (el rectángulo que contiene cada objeto) en lugar de máscaras.

| Umbral | Qué decide | Si se sube |
|---|---|---|
| IoU (0.5) | Cuánto se tiene que superponer la predicción con la etiqueta | Es más difícil acertar: el AP50-Seg baja |
| Confianza mínima (0.001 o 0.05) | Qué predicciones se descartan antes de evaluar | Se pierden predicciones dudosas: el AP50-Seg baja o queda igual |

Por eso se evalúa con confianza baja; una alta, como el 0.25 de las visualizaciones, solo sirve para mostrar resultados.

## Los dos cálculos

| | Cálculo del conjunto de test de FloorPlanCAD | Cálculo de BLD-AR |
|---|---|---|
| Herramienta | `model.val` de Ultralytics (notebooks de entrenamiento) | SAHI y COCOeval (`evaluate_bldar.ipynb`) |
| Imagen | Plano entero, a imgsz | Tiles de 1024 px y unión de sus predicciones |
| Resolución de las máscaras | 1/4 de imgsz | La del plano |
| Confianza mínima | 0.001 | 0.05 |
| Máximo de predicciones | 300 por imagen | 100 por plano y clase |
| Orden para emparejar | Por IoU | Por confianza |
| Zonas ignoradas | Ninguna | Clases de BLD-AR sin mapear |
| Clases en el mAP50-Seg y el mAP50-Box | 30 | 6 |

- En el AP50-Seg, el cálculo pesa poco en la diferencia entre los dos conjuntos, salvo la unión de SAHI en wall (`docs/CAIDA_RENDIMIENTO_BLDAR.md`).
- Para comparar los dos conjuntos hay que mirar clase por clase: en `docs/HISTORICO.md`, el mAP50-Seg y el mAP50-Box promedian 30 clases en FloorPlanCAD y 6 en BLD-AR.
- Falta verificar si el máximo de 100 predicciones deja afuera paredes en los planos más grandes de BLD-AR (BLD_14 se corta en cientos de tiles).

## Pendiente: corridas con imgsz distinto de 1024

El notebook pasa `image_size=TILE` (1024) al modelo, así que una corrida entrenada con imgsz 640 recibe muros más gruesos de los que aprendió. Falta un parámetro `IMGSZ` pasado como `image_size`; hasta entonces, BLD-AR de `04-YOLO26m-SEG-640` no es comparable.
