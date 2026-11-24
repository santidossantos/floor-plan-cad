# Caída de rendimiento de FloorPlanCAD a BLD-AR

**Pregunta:** ¿por qué el mAP50-Seg cae de 0.819 en el conjunto de test de FloorPlanCAD a 0.324 en BLD-AR (`01-YOLO26l-SEG-1024`, 6 clases mapeadas)? Cómo se calcula cada métrica: `docs/EVALUACION.md`.

## Qué hace SAHI

Corta cada plano en tiles de 1024 px que se superponen un 20 %, pasa cada uno por el modelo y junta las predicciones en el plano completo. Hace falta porque los planos de BLD-AR miden hasta 15 000 px: achicados enteros a 1024 px, los muros quedarían de un píxel.

**Unión (GREEDYNMM):** junta las predicciones de una misma clase cuyas cajas se superponen (área en común ≥ la mitad de la caja más chica), para unir los muros cortados entre tiles. Efecto secundario: también junta paredes distintas que están cerca, aunque el plano entre en un solo tile; por ejemplo, la caja de una pared en L contiene las de sus vecinas.

## Cuánto viene del cálculo

Tarea `determinar-costo-calculo-sahi-floorplancad-vs-bldar` (`scripts/evaluation/compare_evaluation_methods.ipynb`): el mismo conjunto de test de FloorPlanCAD con (1) su propio cálculo, (2) el de BLD-AR y (2b) el de BLD-AR sin la unión (`get_prediction` de SAHI: con un tile por plano, es la misma inferencia sin unir).

**AP50-Seg por clase**

| Clase | Instancias | (1) Cálculo del conjunto de test de FloorPlanCAD | (2) Cálculo de BLD-AR | (2b) Cálculo de BLD-AR sin la unión |
|---|---:|---:|---:|---:|
| wall | 14 040 | 0.828 | 0.664 | 0.803 |
| single_door | 2 259 | 0.959 | 0.907 | 0.908 |
| window | 1 543 | 0.856 | 0.822 | 0.845 |
| sliding_door | 620 | 0.588 | 0.879 | 0.896 |
| stair | 1 403 | 0.795 | 0.678 | 0.728 |
| elevator | 19 | 0.887 | 0.857 | 0.857 |
| Media | | 0.819 | 0.801 | 0.839 |

- **Respuesta:** el cálculo explica el 4 % de la caída hasta BLD-AR (0.018 de 0.495). La caída viene del conjunto, no de cómo se mide.
- **La unión baja** el mAP50-Seg 0.038, sobre todo en wall (0.803 → 0.664, el 85 % de lo que baja wall con el cálculo de BLD-AR) y stair (−0.050).
- **El resto del cálculo sube** el mAP50-Seg 0.021, sobre todo en sliding_door (+0.308). Hipótesis: compara las máscaras a tamaño completo y no a 1/4, lo que favorece a los objetos finos.

## Mismo cálculo en los dos conjuntos

Con el cálculo de BLD-AR (con la unión) en los dos, la puerta casi no pierde y el resto cae mucho:

**AP50-Seg por clase**

| Clase | Conjunto de test de FloorPlanCAD | BLD-AR |
|---|---:|---:|
| single_door (door) | 0.907 | 0.896 |
| window | 0.822 | 0.455 |
| stair | 0.678 | 0.302 |
| wall | 0.664 | 0.114 |
| sliding_door | 0.879 | 0.118 |
| elevator (19 instancias en el test: poco estable) | 0.857 | 0.059 |

## Pendiente

La unión probablemente también baja el AP50-Seg de wall en BLD-AR (0.114), pero ahí además hace falta para juntar los muros cortados entre tiles. Lo mide `union-paredes-entre-tiles`.
