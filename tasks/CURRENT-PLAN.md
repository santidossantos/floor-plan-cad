# Plan: paredes-por-estilo

**Pregunta:** ¿al modelo le cuesta encontrar las paredes vacías, sin líneas adentro?

## Criterio acordado
- **Muestra:** 300 paredes al azar del test de FloorPlanCAD (semilla fija). Cada una se marca a ojo:
  - **tiene:** hay una línea a lo largo de la pared (eje, capa o rayado), aunque sea punteada;
  - **no tiene:** no hay líneas a lo largo. No cuentan los bordes ni las líneas que la cruzan de lado a lado;
  - **no se ve:** la etiqueta no coincide con el dibujo; queda afuera.
- Las marcas van en una celda del notebook. El usuario revisa una parte.
- **Pared encontrada:** qué parte de cada pared marca el modelo, con confianza 0.25, en promedio por pared.
- **AP50 de seg de pared de cada grupo:** con los mismos parámetros que la evaluación en BLD-AR. Las paredes fuera del grupo o fuera de la muestra son zonas a ignorar.
- **Decisión:** A = pared encontrada de las que no tienen líneas; B = la de las que tienen. Se divide A / B (ej.: 60 % / 90 % = 67 %).
  - Menos del 80 %: encuentra claramente peor las vacías → confirmada.
  - Entre 80 % y 95 %: las encuentra algo peor → confirmada en parte.
  - 95 % o más: las encuentra casi igual → descartada.
- BLD-AR no entra en este notebook: no decide la hipótesis.

## Pasos
- [x] Acordar con el usuario cómo se confirma o descarta
- [x] Armar la muestra y las hojas para marcar a ojo
- [x] Marcar tiene / no tiene / no se ve en cada pared
- [x] Revisión de una parte de las marcas por el usuario
- [x] Adaptar el notebook: marcas de la muestra en vez del 5 %, sin BLD-AR, con el AP50 de seg de pared de cada grupo
- [x] Probarlo localmente con pocos planos
- [ ] El usuario lo corre en el servidor
- [ ] Anotar el resultado en docs/DIAGNOSTICO_PAREDES.md
- [ ] Aprobación del script resultante por el usuario.
