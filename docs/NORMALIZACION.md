# Normalización de imágenes

**Decisión:** `svg_to_json.py` guarda cada PNG de FloorPlanCAD con fondo blanco y líneas oscuras, como en BLD-AR. Reemplaza a `normalize_dataset.py`, que hacía lo mismo en un paso aparte sobre el dataset YOLO.

## Hallazgos
- Los PNG de FloorPlanCAD (15 663, todos RGBA) tienen fondo transparente con RGB = 0, así que YOLO los lee con fondo negro. BLD-AR tiene fondo blanco y líneas oscuras.
- En un experimento previo, un modelo entrenado con fondo negro bajó de 0.517 a 0.038 de Box mAP50-95 en test con solo invertir la polaridad de las imágenes.
- Alrededor del 11 % de los píxeles de trazo son negros en RGB (en 42 de 60 imágenes de muestra) y desaparecen sobre el fondo negro. Por eso el trazo se toma del canal alfa.
- Los trazos son antialiasados (mediana de alfa 137). Con `INK_GAIN = 4`, el 83 % de los píxeles de trazo queda oscuro (< 128), contra el 56 % sin ganancia.
