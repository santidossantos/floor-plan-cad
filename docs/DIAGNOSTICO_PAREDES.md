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

**Líneas adentro de la pared.** Muestra de 300 paredes al azar del test de FloorPlanCAD, marcadas a ojo (`paredes-por-estilo`):

| Marca | Paredes |
|---|---:|
| Tiene una línea a lo largo de la pared (eje, capa o rayado), aunque sea punteada | 70 |
| No tiene: vacía, o solo la cruzan líneas de lado a lado | 115 |
| No se ve: la etiqueta no coincide con el dibujo, es un cruce de líneas o es dudosa | 115 |

De las paredes que se ven claras, el 38 % tiene líneas adentro (70 de 185). En BLD-AR casi todas son una doble línea vacía, pero hay medianeras con el eje punteado adentro (por ejemplo, en BLD_01_AR_FP_01, 02 y 03); no se contaron.

**Rellenos.** BLD-AR tiene 4 muros medianeros rellenos, que son el 27 % de su área de pared: 2 grises (BLD_01_AR_FP_01 y 02, 2 %) y 2 negros de ~195 px (BLD_14_AR_FP_01 y 02, 25 %). En FloorPlanCAD no se encontraron paredes rellenas (0 % del área en 300 planos).

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

La evaluación une las predicciones de wall con GREEDYNMM (IOS 0.5) para juntar los muros cortados entre tiles. Prueba sin el modelo: en lugar de las predicciones, se evalúan las propias paredes etiquetadas de BLD-AR (con confianza 1 y sin cortarlas en tiles), antes y después de aplicarles la unión.

| | Paredes | AP50 de seg | AP50-95 de seg |
|---|---:|---:|---:|
| Sin unir | 964 | 0.99 | 0.89 |
| Con GREEDYNMM, como en la evaluación | 749 | 0.77 | 0.65 |

El 32 % de las paredes de BLD-AR tiene su caja contenida en más de un 50 % en la de otra pared (15 % en FloorPlanCAD). El NMS del modelo (IoU 0.7) casi no las afecta (0.2 %).

## Paredes por píxel

En cada plano se juntan todas las paredes en dos mapas, el de la etiqueta y el que marca el modelo, y se superponen (`scripts/evaluation/measure_wall_pixel_overlap.ipynb`). Corrida 00, confianza 0.25 y los mismos tiles que la evaluación; en BLD-AR no cuenta lo predicho sobre las demás clases. Promedio por plano, en los planos con paredes etiquetadas.

| Píxel | Qué es |
|---|---|
| Amarillo | Pared en la etiqueta y en el modelo: acierto |
| Verde | Pared solo en la etiqueta: el modelo no la encontró |
| Rojo | Pared solo en el modelo: la marcó de más |

| Medida | Qué mide | Cálculo | Test de FloorPlanCAD (1 333 planos) | BLD-AR (56 planos) | BLD-AR comparado con el test de FloorPlanCAD |
|---|---|---|---:|---:|---:|
| Pared encontrada | De la pared etiquetada, qué parte marca el modelo | amarillo / (amarillo + verde) | 0.81 | 0.61 | 75 % |
| Pared bien marcada | De lo que marca el modelo, qué parte es pared en la etiqueta | amarillo / (amarillo + rojo) | 0.86 | 0.88 | 102 % |
| Coincidencia | De toda la pared que marcan la etiqueta o el modelo, qué parte marcan los dos | amarillo / (amarillo + verde + rojo) | 0.71 | 0.57 | 80 % |

**Ejemplo:** la etiqueta tiene 100 píxeles de pared y el modelo marca 90, de los que 70 coinciden (70 amarillos, 30 verdes y 20 rojos). Pared encontrada: 70 / 100 = 0.70. Pared bien marcada: 70 / 90 = 0.78. Coincidencia: 70 / 120 = 0.58.

- La última columna es el valor de BLD-AR dividido por el del test de FloorPlanCAD.
- Se decide con la pared encontrada porque el test de FloorPlanCAD tiene muros sin etiquetar: en 0014-0052, los de la capa `A-WALL` no tienen semantic-id y el modelo los marca. Eso baja su coincidencia y puede bajar su AP50 de seg. En 3 de 4 planos revisados, las capas de muros tienen elementos sin la clase wall.

## Por qué el AP50 de seg de pared baja de 0.82 (test de FloorPlanCAD) a 0.12 (BLD-AR)

El AP50 de seg cuenta pared por pared: una pared predicha acierta si su máscara se superpone al menos un 50 % con la de una etiquetada. En BLD-AR, y no en el test de FloorPlanCAD:
1. **La unión entre tiles junta paredes distintas:** en la prueba sin el modelo (las etiquetas usadas como predicciones), el AP50 de seg de pared de BLD-AR no pasa de 0.77. El test de FloorPlanCAD se evalúa con el plano entero, sin tiles.
2. **BLD-AR corta las paredes distinto:** deja L, T y U en un polígono (49 % de sus paredes, contra 25 % en FloorPlanCAD) y corta en las columnas. Una L bien marcada pero en dos pedazos puede contar como dos errores y una pared no encontrada.
3. **El modelo no encuentra toda la pared:** marca el 61 % de la pared de BLD-AR, contra el 81 % en el test de FloorPlanCAD. Falta saber qué pared se le escapa (estilo y espesor).

Además, el 0.82 y el 0.12 no se calculan igual: cambian la herramienta, la resolución de las máscaras y el máximo de predicciones (`docs/EVALUACION.md`). Parte de la diferencia puede venir del cálculo.

En píxeles, BLD-AR llega a tres cuartos del test de FloorPlanCAD; en AP50 de seg, a menos de un quinto. Eso sugiere que separar las paredes (1 y 2) pesa mucho, pero no se midió cuánto aporta cada causa al AP50 de seg.

## Hipótesis

| Hipótesis | Evidencia | Estado | Impacto en el AP50 de seg de pared (BLD-AR) |
|---|---|---|---|
| Etiquetado: las instancias no coinciden | BLD-AR une L, T y U en un polígono y corta en columnas. Por píxel, encuentra el 75 % de la pared que en el test de FloorPlanCAD y lo que marca es pared; el AP50 de seg cae mucho más | Confirmada en parte: encuentra el 75 % de la pared que en el test de FloorPlanCAD; falta medir cuánto del AP50 de seg se pierde por el corte | Sin medir |
| Estilo: el modelo depende de las líneas dentro de la pared | En la muestra a ojo del test de FloorPlanCAD, 70 de 185 paredes claras tienen líneas adentro; en BLD-AR casi todas son vacías, salvo medianeras con el eje punteado | Probable; se mide en `paredes-por-estilo` | Sin medir |
| Escala: muros más gruesos o finos que en entrenamiento | 24 de 56 planos fuera de 0.7–1.4 veces | Probable en los planos extremos; falta el AP50 de seg por plano | Sin medir |
| Unión de SAHI entre tiles | En la prueba sin el modelo (las etiquetas usadas como predicciones), une el 22 % de las paredes y deja el AP50 de seg en 0.77 | Confirmado: techo del AP50 de seg de pared | Solo en una prueba sin el modelo (las etiquetas usadas como predicciones): −0.22 (de 0.99 a 0.77); con las predicciones del modelo, sin medir |
| Límites de YOLO-seg con paredes | - | Pendiente | Sin medir |
