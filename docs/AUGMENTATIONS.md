# Augmentations

**Decisión:** el entrenamiento aplica 10 Albumentations que simulan planos en papel escaneados (`scripts/model-training/train_segmentation_model.ipynb`). Ultralytics las aplica solo en entrenamiento; en promedio cada imagen recibe 2.7 degradaciones y solo un 4 % queda sin ninguna.

| Albumentation                  | Parámetros                | Por qué sirve en planos                                                   | En BLD-AR                                                          |
|--------------------------------|---------------------------|---------------------------------------------------------------------------|--------------------------------------------------------------------|
| RandomBrightnessContrast       | p=0.5                     | Papel amarillento o grisáceo y copias con más o menos contraste.          | En parte: varía el contraste del trazo, el fondo es siempre blanco |
| RandomGamma                    | p=0.3                     | Aclara u oscurece los grises intermedios sin mover el blanco ni el negro. | Sí: trazos y rellenos grises                                       |
| Illumination                   | p=0.3                     | Luz despareja al escanear o fotografiar el plano.                         | No                                                                 |
| Spatter (mud)                  | p=0.3                     | Manchas de suciedad o humedad en el papel.                                | No                                                                 |
| Erosión o dilatación del trazo | p=0.3, núcleo 2×2         | Trazo más grueso o más fino por impresión, copia o resolución.            | Sí: el grosor del trazo varía entre planos                         |
| GaussNoise                     | p=0.3, std 0.02–0.1       | Grano del sensor del escáner o la cámara.                                 | No                                                                 |
| SaltAndPepper                  | p=0.2, 0.1–1 % de píxeles | Polvo y motas sueltas.                                                    | No                                                                 |
| Defocus                        | p=0.2, radio 1–3          | Escaneo o foto fuera de foco.                                             | No: los trazos son nítidos                                         |
| ImageCompression               | p=0.3, calidad 40–90      | Artefactos de compresión JPEG.                                            | Sí: 55 de 58 imágenes son JPG                                      |
| ToGray                         | p=1.0                     | Los planos escaneados se usan en gris; deja los tres canales iguales.     | Sí: las 58 imágenes son grises                                     |

La erosión o dilatación es una transformación propia (`StrokeMorphology`): `A.Morphological` también modifica las cajas de las etiquetas, y con imágenes de más de 512 px de ancho OpenCV falla.

## Hallazgos
- BLD-AR no son escaneos sino exportaciones digitales en gris: fondo blanco puro, sin manchas, ruido ni luz despareja. Varían el tono del trazo (negro, gris medio o muy claro), el grosor, los rellenos y la resolución (de 1200×1600 a 15000×12000 px).
- Por eso Illumination, Spatter, GaussNoise, SaltAndPepper y Defocus no se pueden evaluar con BLD-AR: apuntan a degradaciones que no tiene.
- El aporte de las augmentations se mide contra la corrida sin ellas (`train_segmentation_model_without_analog_noise.ipynb`), en `runs/HISTORICO.md`.
