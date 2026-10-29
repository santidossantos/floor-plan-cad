# Plan: diagnostico-paredes

Por qué wall transfiere tan mal a BLD-AR y si conviene segmentarla con una red semántica (p. ej. UNet) en lugar de YOLO.

## Pasos
1. [x] Comparar cómo trata wall el paper de FloorPlanCAD, cómo la etiqueta BLD-AR y cómo la etiqueta nuestra conversión (cantidad, tamaño, forma y dónde se corta).
2. [x] Comparar el estilo de dibujo de las paredes y clasificar los planos de BLD-AR por estilo.
3. [x] Definir con el usuario la corrida a diagnosticar y el alcance de los análisis con el modelo (planos, muestra de FloorPlanCAD).
4. [ ] Medir wall por píxel, sin instancias, en BLD-AR y en el test de FloorPlanCAD.
5. [ ] Generar los mapas de calor de la red para wall y superponerlos con las etiquetas.
6. [ ] Armar la matriz de confusión por píxel de wall.
7. [ ] Relacionar el rendimiento de wall por plano con el grosor de muro y el estilo, y probar tiles adaptados.
8. [ ] Revisar los límites de YOLO-seg con paredes.
9. [x] Testear localmente el notebook de diagnóstico con un subconjunto chico.
10. [ ] Documentar el diagnóstico en `docs/` y proponer si conviene una red semántica para wall.
11. [ ] Aprobación del script resultante por el usuario.
