# Evaluación en BLD-AR

**Decisión:** `scripts/evaluation/evaluate_segmentation_model.ipynb` corta cada plano de BLD-AR en tiles de 1024 px con SAHI. Es el tamaño en el que los muros de BLD-AR quedan con el grosor que ve el modelo en FloorPlanCAD con imgsz 1024 (mediana de ~19 px contra ~18 px).

## Problema pendiente: corridas con imgsz distinto de 1024
- El notebook pasa `image_size=TILE` al modelo, así que SAHI redimensiona cada tile a 1024 px antes de la inferencia, sea cual sea el imgsz de la corrida.
- Un modelo entrenado con imgsz 640 vio muros de ~11 px y en BLD-AR recibiría muros de ~19 px: sus métricas bajarían por la escala, no por el imgsz.
- Solución propuesta, sin aplicar: un parámetro `IMGSZ` con el imgsz de la corrida, pasado como `image_size`. `TILE` queda en 1024, porque el tile equivalente no depende del imgsz.
- Mientras no se corrija, las métricas de BLD-AR de `yolo26m-seg-640` no son comparables con las de las corridas de 1024.
