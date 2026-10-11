# Histórico de entrenamientos

| Corrida             | Modelo      | imgsz | Albumentations  | Box mAP50 | Box mAP50-95 | Seg mAP50 | Seg mAP50-95 |
|---------------------|-------------|------:|-----------------|----------:|-------------:|----------:|-------------:|
| 00-YOLO26m-SEG-1024 | yolo26m-seg |  1024 | Ruido analógico |     0.841 |        0.774 |     0.813 |        0.631 |
| 01-YOLO26l-SEG-1024 | yolo26l-seg |  1024 | Ruido analógico |     0.845 |        0.779 |     0.816 |        0.633 |

## Configuración común

| Parámetro  | Valor                                                  |
|------------|--------------------------------------------------------|
| Evaluación | Test de FloorPlanCAD: 1 566 planos del split 80/10/10  |
| batch      | 2                                                      |
| Épocas     | 120                                                    |
| patience   | 20                                                     |
| seed       | 42                                                     |

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
