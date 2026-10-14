# Histórico de entrenamientos

> 🧪 **Las métricas de FloorPlanCAD son siempre sobre el conjunto de test** (1 566 planos que el modelo no vio al entrenar), nunca sobre validación.

| Corrida                                  | Modelo      | imgsz | Albumentations        | FloorPlanCAD mAP50 (B) | FloorPlanCAD mAP50-95 (B) | FloorPlanCAD mAP50 (S) | FloorPlanCAD mAP50-95 (S) | BLD-AR mAP50 (B) | BLD-AR mAP50-95 (B) | BLD-AR mAP50 (S) | BLD-AR mAP50-95 (S) |
|------------------------------------------|-------------|------:|-----------------------|-----------------------:|--------------------------:|-----------------------:|--------------------------:|-----------------:|--------------------:|-----------------:|--------------------:|
| 00-YOLO26m-SEG-1024                      | yolo26m-seg |  1024 | Ruido analógico       |                  0.841 |                     0.774 |                  0.813 |                     0.631 |                - |                   - |                - |                   - |
| 01-YOLO26l-SEG-1024                      | yolo26l-seg |  1024 | Ruido analógico       |                  0.845 |                     0.779 |                  0.816 |                     0.633 |                - |                   - |                - |                   - |
| 02-YOLO26m-SEG-1024-NO-NOISE             | yolo26m-seg |  1024 | Ninguna               |                  0.846 |                     0.781 |                  0.817 |                     0.635 |                - |                   - |                - |                   - |
| 03-YOLO26m-SEG-1024-BLDAR-SPECIFIC-NOISE | yolo26m-seg |  1024 | Específicas de BLD-AR |                  0.846 |                     0.780 |                  0.818 |                     0.636 |                - |                   - |                - |                   - |
| 04-YOLO26m-SEG-640                       | yolo26m-seg |   640 | Ruido analógico       |                  0.834 |                     0.757 |                  0.785 |                     0.542 |                - |                   - |                - |                   - |

(B) = Box · (S) = Segmentation

## Configuración común

| Parámetro    | Valor                                 |
|--------------|---------------------------------------|
| FloorPlanCAD | Test: 1 566 planos del split 80/10/10 |
| BLD-AR       | 58 planos (`-`: todavía no evaluado)  |
| batch        | 2 (4 en 04-YOLO26m-SEG-640)           |
| Épocas       | 120                                   |
| patience     | 20                                    |
| seed         | 42                                    |

## Ruido analógico

Albumentations de `scripts/model-training/train_segmentation_model.ipynb`.

| Transformación                    | Simula                          | Probabilidad |
|-----------------------------------|---------------------------------|-------------:|
| RandomBrightnessContrast          | Tono del papel                  |          0.5 |
| RandomGamma                       | Tono del papel                  |          0.3 |
| Illumination                      | Luz despareja                   |          0.3 |
| Spatter (mud)                     | Manchas                         |          0.3 |
| Erosión o dilatación del trazo    | Trazo más grueso o más fino     |          0.3 |
| GaussNoise                        | Ruido de escaneo                |          0.3 |
| SaltAndPepper                     | Motas                           |          0.2 |
| Defocus                           | Desenfoque                      |          0.2 |
| ImageCompression                  | Artefactos JPG                  |          0.3 |
| ToGray                            | Escala de grises, como BLD-AR   |          1.0 |

## Específicas de BLD-AR

Albumentations de `scripts/model-training/train_segmentation_model_bldar_augmentations.ipynb`: las de ruido analógico cuya variación aparece en BLD-AR (ver `docs/AUGMENTATIONS.md`).

| Transformación                 | Imita en BLD-AR          | Probabilidad |
|--------------------------------|--------------------------|-------------:|
| RandomBrightnessContrast       | Contraste del trazo      |          0.5 |
| RandomGamma                    | Trazos y rellenos grises |          0.3 |
| Erosión o dilatación del trazo | Grosor del trazo         |          0.3 |
| ImageCompression               | Artefactos JPG           |          0.3 |
| ToGray                         | Escala de grises         |          1.0 |
