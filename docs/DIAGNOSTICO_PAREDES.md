# Diagnóstico de paredes (wall)

**Problema:** wall transfiere mal a BLD-AR. Con la corrida 00 da AP50 de seg 0.12 en BLD-AR, contra 0.82 en el test de FloorPlanCAD.

## Etiquetado

Medido sobre las 964 paredes de BLD-AR y 2 403 paredes de 300 planos de test-00.

| | Paper de FloorPlanCAD | Conversión propia | BLD-AR |
|---|---|---|---|
| Tipo de clase | Stuff: sin instancias, se evalúa por píxel | Una instancia por pared ("pared pasante", `docs/PAREDES.md`) | Una instancia por polígono |
| Largo / espesor (mediana) | - | 10.5 | 18.9 |
| Paredes no rectangulares (L, T, U, anillos) | - | 25 % | 49 % |
| Columnas | - | Quedan dentro de la pared | Cortan la pared (y son zona ignorada) |
| Aberturas que tocan 2 paredes | - | 59 % | 66 % |

## Estilo de dibujo

Interior de las paredes, sin sus bordes, ponderado por área.

| Interior de la pared | FloorPlanCAD | BLD-AR |
|---|---:|---:|
| Vacío (doble línea limpia) | 31 % | 72 % |
| Con trazos adentro (ejes, capas, rayado) | 68 % | 0 % |
| Relleno gris | 0 % | 2 % (1 muro medianero en BLD_01_AR_FP_01 y otro en 02) |
| Relleno negro | 0 % | 25 % (1 muro medianero de ~195 px en BLD_14_AR_FP_01 y otro en 02) |

## Escala

Espesor de muro por plano, en píxeles de la imagen que ve el modelo (tile de 1024 px en BLD-AR, imagen redimensionada a 1024 px en FloorPlanCAD).

| | FloorPlanCAD | BLD-AR (56 planos con paredes) |
|---|---:|---:|
| Espesor mediano | ~17 px | 18.7 px |
| Rango | - | 9 – 98 px |
| Planos entre 0.7 y 1.4 veces el espesor de FloorPlanCAD | - | 32 |
| Planos más finos | - | 7 (BLD_07, BLD_09, BLD_10, BLD_13) |
| Planos más gruesos | - | 17 (BLD_14_AR_FP_02 a 06: ~97 px) |

## Unión de predicciones de SAHI

La evaluación une las predicciones de wall con GREEDYNMM (IOS 0.5) para juntar los muros cortados entre tiles. Con las etiquetas de wall de BLD-AR como si fueran predicciones perfectas:

| | Paredes | AP50 (S) | AP50-95 (S) |
|---|---:|---:|---:|
| Sin unir | 964 | 0.99 | 0.89 |
| Con GREEDYNMM, como en la evaluación | 749 | 0.77 | 0.65 |

El 32 % de las paredes de BLD-AR tiene su caja contenida en más de un 50 % en la de otra pared (15 % en FloorPlanCAD). El NMS del modelo (IoU 0.7) casi no las afecta (0.2 %).

## Hipótesis

| Hipótesis | Evidencia | Estado |
|---|---|---|
| Etiquetado: las instancias no coinciden | BLD-AR une L, T y U en un polígono y corta en columnas | Probable; falta medir wall por píxel |
| Estilo: el modelo depende de los trazos dentro de la pared | 68 % de las paredes de FloorPlanCAD tienen trazos adentro; las de BLD-AR casi nunca | Probable; falta medir en FloorPlanCAD por estilo |
| Escala: muros más gruesos o finos que en entrenamiento | 24 de 56 planos fuera de 0.7–1.4 veces | Probable en los planos extremos; falta el AP por plano |
| Unión de SAHI entre tiles | Aun con predicciones perfectas, une el 22 % de las paredes y deja el AP50 de seg en 0.77 | Confirmado: techo del AP de wall |
| Límites de YOLO-seg con paredes | - | Pendiente |
