# Diagnóstico de la mala transferencia a BLD-AR

¿Por qué el modelo rinde mucho peor en BLD-AR que en el conjunto de test de FloorPlanCAD? Con `01-YOLO26l-SEG-1024`, en las 6 clases mapeadas, el mAP50-Seg cae de 0.819 a 0.324. Cómo se calcula cada métrica: `docs/EVALUACION.md`.

## Qué hace SAHI

SAHI es una librería para usar el modelo en imágenes mucho más grandes que las de entrenamiento.
- **Problema:** el modelo se entrenó con planos de ~1 000 px, y los de BLD-AR miden hasta 15 000 px. Si se achicara el plano entero a 1024 px, en los planos más grandes los muros quedarían de alrededor de un píxel.
- **Solución:** SAHI corta el plano en cuadrados de 1024 × 1024 px (tiles) que se superponen un 20 %, para que lo que cae en un borde aparezca entero en algún tile. Pasa cada tile por el modelo y ubica sus predicciones en el plano completo.
- **Unión:** un objeto que cruza el borde entre dos tiles sale predicho en dos pedazos, y SAHI los junta en una sola predicción (ver «Unión de predicciones de SAHI»).

## Cuánto de la diferencia viene del cálculo

Tarea `determinar-costo-calculo-sahi-floorplancad-vs-bldar`. `scripts/evaluation/compare_evaluation_methods.ipynb` aplica tres cálculos al mismo conjunto de test de FloorPlanCAD: (1) el suyo (`model.val`), (2) el de BLD-AR, con las otras 24 clases como zonas ignoradas, y (2b) el de BLD-AR sin la unión de SAHI. Corrida `01-YOLO26l-SEG-1024`, 6 clases mapeadas. (1) y (2) dieron exactamente lo mismo en dos ejecuciones del notebook.

**AP50-Seg**

| Clase | Instancias | (1) Cálculo del conjunto de test de FloorPlanCAD | (2) Cálculo de BLD-AR | (2b) Cálculo de BLD-AR sin la unión |
|---|---:|---:|---:|---:|
| wall | 14 040 | 0.828 | 0.664 | 0.803 |
| single_door | 2 259 | 0.959 | 0.907 | 0.908 |
| window | 1 543 | 0.856 | 0.822 | 0.845 |
| sliding_door | 620 | 0.588 | 0.879 | 0.896 |
| stair | 1 403 | 0.795 | 0.678 | 0.728 |
| elevator | 19 | 0.887 | 0.857 | 0.857 |
| Media | | 0.819 | 0.801 | 0.839 |

**AP50-95-Seg**

| Clase | (1) Cálculo del conjunto de test de FloorPlanCAD | (2) Cálculo de BLD-AR | (2b) Cálculo de BLD-AR sin la unión |
|---|---:|---:|---:|
| wall | 0.510 | 0.456 | 0.596 |
| single_door | 0.829 | 0.820 | 0.824 |
| window | 0.534 | 0.668 | 0.690 |
| sliding_door | 0.281 | 0.556 | 0.566 |
| stair | 0.588 | 0.490 | 0.535 |
| elevator | 0.815 | 0.800 | 0.800 |
| Media | 0.593 | 0.632 | 0.668 |

- **Respuesta:** el cálculo explica el 4 % de la caída del mAP50-Seg de FloorPlanCAD a BLD-AR (0.018 de 0.819 → 0.324) y nada de la del mAP50-95-Seg, que con el cálculo de BLD-AR sube 0.039. La caída viene del conjunto, no de cómo se mide.
- **Ese 4 % suma dos partes que se compensan:**
  - **La unión de SAHI baja** el mAP50-Seg 0.038 y el mAP50-95-Seg 0.037, de (2b) a (2). Sobre todo en wall (−0.139 en AP50-Seg) y stair (−0.050); ver «Unión de predicciones de SAHI».
  - **El resto del cálculo sube** el mAP50-Seg 0.021 y el mAP50-95-Seg 0.076, de (1) a (2b). Sube sobre todo en objetos finos: sliding_door (+0.308 en AP50-Seg) y, en AP50-95-Seg, window (+0.156) y wall (+0.086). Son tiras angostas, de pocos píxeles de ancho. El cálculo del conjunto de test de FloorPlanCAD compara las máscaras achicadas a 1/4 (256 px en lugar de 1024); por ejemplo, una tira de 8 px queda de 2 px, y un corrimiento mínimo arruina la superposición. El de BLD-AR las compara a tamaño completo. Que sea por la resolución es una hipótesis: el resto del cálculo también cambia la confianza mínima, el máximo de predicciones y el orden de emparejamiento. Indicio: con el cálculo del conjunto de test de FloorPlanCAD, sliding_door tiene AP50-Box 0.959 pero AP50-Seg 0.588: la caja la ubica bien y lo que pierde es la máscara.
  - **Sin explicar:** el resto del cálculo baja un poco el AP50-Seg de las demás clases (stair −0.067, single_door −0.051, elevator −0.030, wall −0.025, window −0.011).
- **Con el mismo cálculo en los dos conjuntos**, la puerta casi no pierde y el resto cae mucho (AP50-Seg, corrida `01-YOLO26l-SEG-1024`, los dos con la unión; en BLD-AR no se midió sin ella):

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

**Cuánto baja wall por la unión (medido).** Con el cálculo de BLD-AR, el AP50-Seg de wall del conjunto de test de FloorPlanCAD es 0.803 sin la unión y 0.664 con ella. La unión le quita 0.139: el 85 % de lo que baja wall con ese cálculo (0.828 → 0.664). En AP50-95-Seg le quita 0.140 (0.596 → 0.456). Sin la unión hay 36 801 predicciones; con ella, 25 750.
- **Cómo se midió:** cada plano del conjunto de test de FloorPlanCAD entra en un solo tile, así que `get_prediction` de SAHI hace la misma inferencia que `get_sliced_prediction`, sin la unión. Ahí la unión no tiene muros cortados que juntar: todo lo que baja es error de medición.
- **Por qué afecta más a wall:** es la clase con más objetos por plano (10.5 de media en los planos con paredes del conjunto de test, hasta 86), así que tiene más vecinas con las que juntarse.

**En BLD-AR, sin medir.** Allí la unión sí hace falta: junta los muros cortados entre tiles y elimina las predicciones repetidas donde los tiles se superponen, así que no alcanza con sacarla. El mismo efecto secundario probablemente también baja el 0.114 de wall en BLD-AR, pero no se sabe cuánto. Lo mide `union-paredes-entre-tiles`, comparando alternativas a la unión.
