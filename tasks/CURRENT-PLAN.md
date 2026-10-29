# Plan: paredes-por-pixel

**Pregunta:** ¿el modelo encuentra las paredes, pero las corta distinto que la etiqueta?

## Criterio acordado
- En cada plano se juntan todas las paredes en un mapa de píxeles: uno con lo que predice el modelo y otro con la etiqueta.
- Se calculan tres números:
  - **Coincidencia:** píxeles que son pared en los dos mapas, sobre los que son pared en al menos uno.
  - **Pared encontrada:** qué parte de la pared etiquetada marca el modelo.
  - **Pared bien marcada:** qué parte de lo que marca el modelo es pared en la etiqueta.
- Promedio por plano, en los planos con paredes etiquetadas. En FloorPlanCAD se usa el test completo.
- Una predicción cuenta como pared desde confianza 0.25. Lo predicho sobre las clases excluidas de BLD-AR no cuenta.
- **Confirmada** si la pared encontrada en BLD-AR llega al 80 % o más de la de FloorPlanCAD. **Descartada** si queda debajo del 50 %. Entre los dos, parcial.
- Se decide con la pared encontrada y no con la coincidencia, porque FloorPlanCAD tiene muros sin etiquetar: en 0014-0052, los de la capa `A-WALL` no tienen clase y el modelo los marca. Eso baja la coincidencia en FloorPlanCAD, pero no la pared encontrada.

## Pasos
- [x] Acordar con el usuario cómo se confirma o descarta
- [x] Crear el notebook en scripts/evaluation/, con la corrida 00 y los mismos parámetros que la evaluación en BLD-AR
- [x] Probarlo localmente con pocos planos
- [ ] El usuario lo corre en el servidor
- [ ] Anotar el resultado en docs/DIAGNOSTICO_PAREDES.md
- [ ] Aprobación del script resultante por el usuario.
