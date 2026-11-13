# Plan: paredes-por-estilo

**Pregunta:** ¿al modelo le cuesta encontrar las paredes vacías, sin líneas adentro?

## Criterio acordado
- Cada pared etiquetada se clasifica por su interior, sin los bordes, como en la tabla de estilo de `docs/DIAGNOSTICO_PAREDES.md`:
  - relleno negro si más del 60 % es oscuro;
  - relleno gris si más de la mitad es gris;
  - con líneas adentro si más del 5 % es oscuro;
  - si no, vacía.
- **Pared encontrada:** qué parte de cada pared marca el modelo, con confianza 0.25. Se promedia por pared.
- **AP50 de seg de pared de cada grupo:** con los mismos parámetros que la evaluación en BLD-AR. Lo predicho sobre paredes de otro grupo no cuenta.
- **Decide la comparación en el test de FloorPlanCAD:** A = pared encontrada promedio de las paredes vacías; B = la de las paredes con líneas adentro. Se divide A / B (ej.: 60 % / 90 % = 67 %).
  - Menos del 80 %: encuentra claramente peor las vacías → confirmada.
  - Entre 80 % y 95 %: las encuentra algo peor → confirmada en parte.
  - 95 % o más: las encuentra casi igual → descartada.
  - BLD-AR se muestra como referencia, porque casi no tiene paredes con líneas.

## Pasos
- [x] Acordar con el usuario cómo se confirma o descarta
- [x] Crear el notebook en scripts/evaluation/, con la corrida 00 y los mismos parámetros que la evaluación en BLD-AR
- [x] Medir también el AP50 de seg de pared de cada grupo (paredes con líneas adentro, vacías y rellenas)
- [x] Probarlo localmente con pocos planos
- [ ] El usuario lo corre en el servidor
- [ ] Anotar el resultado en docs/DIAGNOSTICO_PAREDES.md
- [ ] Aprobación del script resultante por el usuario.
