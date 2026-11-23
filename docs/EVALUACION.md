# Evaluación en BLD-AR

**Decisión:** `scripts/evaluation/evaluate_bldar.ipynb` evalúa BLD-AR cortando cada plano en tiles de 1024 px con SAHI. Con ese tamaño, los muros de BLD-AR quedan con el grosor que el modelo vio en FloorPlanCAD con imgsz 1024 (mediana de ~19 px contra ~18 px).

## Qué hace SAHI

SAHI es una librería para usar el modelo en imágenes mucho más grandes que las de entrenamiento.
- **Problema:** el modelo se entrenó con planos de ~1 000 px, y los de BLD-AR miden hasta 15 000 px. Si se achicara el plano entero a 1024 px, en los planos más grandes los muros quedarían de alrededor de un píxel.
- **Solución:** SAHI corta el plano en cuadrados de 1024 × 1024 px (tiles) que se superponen un 20 %, para que lo que cae en un borde aparezca entero en algún tile. Pasa cada tile por el modelo y ubica sus predicciones en el plano completo.
- **Unión:** un objeto que cruza el borde entre dos tiles sale predicho en dos pedazos, y SAHI los junta en una sola predicción (ver «Unión de predicciones de SAHI»).

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
- Entre el conjunto de test de FloorPlanCAD y BLD-AR cambia más que el conjunto: también la herramienta, la resolución de las máscaras, el máximo de predicciones y la confianza mínima. En el AP-Seg pesa poco (ver «Cuánto de la diferencia viene del cálculo»); en el AP-Box no se midió.
- En `docs/HISTORICO.md`, el mAP-Box y el mAP-Seg de FloorPlanCAD promedian 30 clases, y los de BLD-AR, 6. Para comparar los dos conjuntos hay que mirar clase por clase.
- La unión de predicciones de SAHI baja el AP50-Seg de wall aunque el plano entre en un solo tile (ver «Unión de predicciones de SAHI»).
- Falta verificar si el máximo de 100 predicciones por plano y clase deja afuera paredes en los planos grandes (BLD_14 mide 15 000 × 12 000 px y se corta en cientos de tiles). En el conjunto de test de FloorPlanCAD no recorta: ningún plano tiene más de 86 etiquetas de una clase.

## Cuánto de la diferencia viene del cálculo

`scripts/evaluation/compare_evaluation_methods.ipynb` aplica los dos cálculos al mismo conjunto de test de FloorPlanCAD: el suyo (`model.val`) y el de BLD-AR (con las otras 24 clases como zonas ignoradas). Corrida `01-YOLO26l-SEG-1024`, 6 clases mapeadas.

| Clase | Instancias | AP50-Seg, cálculo del conjunto de test de FloorPlanCAD | AP50-Seg, cálculo de BLD-AR | AP50-95-Seg, cálculo del conjunto de test de FloorPlanCAD | AP50-95-Seg, cálculo de BLD-AR |
|---|---:|---:|---:|---:|---:|
| wall | 14 040 | 0.828 | 0.664 | 0.510 | 0.456 |
| single_door | 2 259 | 0.959 | 0.907 | 0.829 | 0.820 |
| window | 1 543 | 0.856 | 0.822 | 0.534 | 0.668 |
| sliding_door | 620 | 0.588 | 0.879 | 0.281 | 0.556 |
| stair | 1 403 | 0.795 | 0.678 | 0.588 | 0.490 |
| elevator | 19 | 0.887 | 0.857 | 0.815 | 0.800 |
| Media | | 0.819 | 0.801 | 0.593 | 0.632 |

- **Respuesta:** el cálculo explica el 4 % de la caída del mAP50-Seg de FloorPlanCAD a BLD-AR (0.018 de 0.819 → 0.324) y nada de la del mAP50-95-Seg, que con el cálculo de BLD-AR sube 0.039. La caída viene del conjunto, no de cómo se mide.
- **Por clase hay dos efectos que se compensan.** Son hipótesis: el notebook no los separa.
  - **Bajan wall y stair.** Encaja con la unión de SAHI (ver la sección siguiente).
  - **Suben sliding_door (en los dos AP-Seg) y window (en AP50-95-Seg).** Son objetos finos: tiras angostas, de pocos píxeles de ancho. El cálculo del conjunto de test de FloorPlanCAD compara las máscaras achicadas a 1/4 (256 px en lugar de 1024); por ejemplo, una tira de 8 px queda de 2 px, y un corrimiento mínimo arruina la superposición. El de BLD-AR las compara a tamaño completo. Indicio: con el cálculo del conjunto de test de FloorPlanCAD, sliding_door tiene AP50-Box 0.959 pero AP50-Seg 0.588: la caja la ubica bien y lo que pierde es la máscara.
- **Con el mismo cálculo en los dos conjuntos**, la puerta casi no pierde y el resto cae mucho (AP50-Seg, corrida `01-YOLO26l-SEG-1024`):

| Clase | Conjunto de test de FloorPlanCAD | BLD-AR |
|---|---:|---:|
| single_door (door) | 0.907 | 0.896 |
| window | 0.822 | 0.455 |
| stair | 0.678 | 0.302 |
| wall | 0.664 | 0.114 |
| sliding_door | 0.879 | 0.118 |
| elevator (19 instancias en el test: poco estable) | 0.857 | 0.059 |

## Unión de predicciones de SAHI

**Para qué está.** Una pared que cruza el borde entre dos tiles sale predicha en dos pedazos, uno en cada tile. Por separado, ninguno de los dos se parece lo suficiente a la pared etiquetada: hay que juntarlos.

**Cómo decide qué juntar: GREEDYNMM** (*Greedy Non-Maximum Merging*).
1. Ordena las predicciones de más a menos confianza.
2. Toma la primera y busca otras de la misma clase cuya caja se superponga con la suya en al menos la mitad del área de la caja más chica.
3. Las junta con ella en una sola predicción: suma sus máscaras.
4. Sigue con la próxima predicción que quedó sin juntar.

Se llama *greedy* (codicioso) porque decide una sola vez, en orden, sin volver atrás, y *merging* porque junta las predicciones en lugar de borrarlas. La alternativa, NMS (*Non-Maximum Suppression*), borra las de menos confianza y no junta nada. Con confianza menor a 0.1, SAHI cambia sola a NMS; por eso `evaluate_bldar.ipynb` fuerza GREEDYNMM (`force_postprocess_type=True`).

**El efecto secundario.** SAHI solo mira las cajas: no distingue dos pedazos de la misma pared de dos paredes distintas que están cerca. Y junta en todo el plano, no solo en los bordes entre tiles, así que pasa aunque el plano entre en un solo tile (`get_sliced_prediction` de sahi 0.12.8). Por ejemplo, la caja de una pared predicha en L es un rectángulo grande que contiene las cajas de las paredes de al lado:

```text
┌───────────────┐ ← caja de la pared predicha en L
│███████████████│
│██       ▓▓    │   ▓▓ = otra pared: su caja queda adentro,
│██       ▓▓    │        así que SAHI la junta con la L
└───────────────┘
```

La predicción unida cubre varias paredes, pero las etiquetas tienen cada pared por separado. Puede no llegar a IoU 0.5 con ninguna: entonces cuenta como un error, y esas paredes, como no encontradas.

**Cuánto baja wall.** Con el cálculo de BLD-AR, el AP50-Seg de wall del conjunto de test de FloorPlanCAD baja de 0.828 a 0.664 (−0.164). Es la mayor caída de las 6 clases y el 23 % de la caída de wall hasta BLD-AR (0.828 → 0.114).

**Causa probable, pero no aislada.** La unión es la única parte del cálculo que junta predicciones, y wall es la clase con más objetos por plano (10.5 de media en los planos con paredes del conjunto de test, hasta 86). Pero el notebook mide el cálculo completo; para confirmarlo hay que evaluar sin la unión. Lo hará `union-paredes-entre-tiles`, que debe usar el mismo cálculo que BLD-AR.

## Problema pendiente: corridas con imgsz distinto de 1024
- El notebook pasa `image_size=TILE` al modelo, así que SAHI redimensiona cada tile a 1024 px antes de la inferencia, sea cual sea el imgsz de la corrida.
- Un modelo entrenado con imgsz 640 vio muros de ~11 px y en BLD-AR recibiría muros de ~19 px: sus métricas bajarían por la escala, no por el imgsz.
- Solución propuesta, sin aplicar: un parámetro `IMGSZ` con el imgsz de la corrida, pasado como `image_size`. `TILE` queda en 1024, porque el tile equivalente no depende del imgsz.
- Mientras no se corrija, las métricas de BLD-AR de `yolo26m-seg-640` no son comparables con las de las corridas de 1024.
