# Caída de rendimiento de FloorPlanCAD a BLD-AR

**Pregunta:** ¿por qué el mAP50-Seg cae de 0.819 en el conjunto de test de FloorPlanCAD a 0.324 en BLD-AR (`01-YOLO26l-SEG-1024`, 6 clases mapeadas)? Cómo se calcula cada métrica: `docs/EVALUACION.md`.

## 1. Medir cuánto de la caída viene de cómo se calcula el AP50-Seg

**Scripts utilizados:** [`scripts/evaluation/compare_evaluation_methods.ipynb`](../scripts/evaluation/compare_evaluation_methods.ipynb) y, para BLD-AR, [`runs/01-YOLO26l-SEG-1024/evaluate_segmentation_model.ipynb`](../runs/01-YOLO26l-SEG-1024/evaluate_segmentation_model.ipynb)

### 1.1 Cómo SAHI corta los planos en tiles y une sus predicciones

Corta cada plano en tiles de 1024 px que se superponen un 20 %, pasa cada uno por el modelo y junta las predicciones en el plano completo. Hace falta porque los planos de BLD-AR miden hasta 15 000 px: achicados enteros a 1024 px, los muros quedarían de un píxel.

**Unión (GREEDYNMM):** junta las predicciones de una misma clase cuyas cajas se superponen (área en común ≥ la mitad de la caja más chica), para unir los muros cortados entre tiles. Efecto secundario: también junta paredes distintas que están cerca, aunque el plano entre en un solo tile; por ejemplo, la caja de una pared en L contiene las de sus vecinas.

### 1.2 Comparar el AP50-Seg con tres cálculos en el conjunto de test de FloorPlanCAD y con el de BLD-AR

- 🔵 **Conjunto de test de FloorPlanCAD** (1 566 planos): (1) con su propio cálculo, (2) con el de BLD-AR y (2b) con el de BLD-AR sin la unión (`get_prediction` de SAHI: con un tile por plano, es la misma inferencia sin unir).
- 🟠 **BLD-AR** (58 planos): (3) con su propio cálculo, el de BLD-AR, con [`scripts/evaluation/evaluate_bldar.ipynb`](../scripts/evaluation/evaluate_bldar.ipynb) (ejecutado en [`runs/01-YOLO26l-SEG-1024/evaluate_segmentation_model.ipynb`](../runs/01-YOLO26l-SEG-1024/evaluate_segmentation_model.ipynb)).

**AP50-Seg por clase en 🔵 el conjunto de test de FloorPlanCAD y 🟠 BLD-AR**

| Clase | 🔵 (1) Cálculo del conjunto de test de FloorPlanCAD | 🔵 (2) Cálculo de BLD-AR | 🔵 (2b) Cálculo de BLD-AR sin la unión | 🟠 (3) Cálculo de BLD-AR |
|---|---:|---:|---:|---:|
| wall | 0.828 | 0.664 | 0.803 | 0.114 |
| single_door (door) | 0.959 | 0.907 | 0.908 | 0.896 |
| window | 0.856 | 0.822 | 0.845 | 0.455 |
| sliding_door | 0.588 | 0.879 | 0.896 | 0.118 |
| stair | 0.795 | 0.678 | 0.728 | 0.302 |
| elevator | 0.887 | 0.857 | 0.857 | 0.059 |
| Media | 0.819 | 0.801 | 0.839 | 0.324 |

- **El conjunto pesa casi todo:** con el mismo cálculo, de (2) a (3) el mAP50-Seg cae 0.477. La puerta casi no pierde (0.907 → 0.896) y el resto cae mucho (elevator, con 19 instancias en el test, es poco estable).
- **La unión baja** el mAP50-Seg 0.038, sobre todo en wall (0.803 → 0.664, el 85 % de lo que baja wall con el cálculo de BLD-AR) y stair (−0.050).
- ⚠️ **El resto del cálculo sube** el mAP50-Seg 0.021 solo por sliding_door (+0.308); en las otras 5 clases baja (entre −0.011 y −0.067). Causa sin medir.

> 📌 **Conclusión:** en la media, el cálculo explica el 4 % de la caída del mAP50-Seg (0.018 de 0.495), pero porque sliding_door sube y compensa; sin ella, explica el 16 %. La mayor parte de la caída viene del conjunto (domain gap). Dentro del cálculo, lo que más baja es la unión de SAHI en wall (−0.139 de AP50-Seg).

## Pendiente: medir la unión de SAHI en BLD-AR

La unión probablemente también baja el AP50-Seg de wall en BLD-AR (0.114), pero ahí además hace falta para juntar los muros cortados entre tiles. Lo mide `union-paredes-entre-tiles`.
