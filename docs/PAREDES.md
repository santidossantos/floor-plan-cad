# Paredes (wall)

**Decisión:** un polígono por pared con el criterio "pared pasante": en una T, la pared que sigue de largo queda entera y la que llega termina en su cara; en una L, la esquina va a la pared de mayor área. Solo se usan elementos con semantic-id 1 (se quitó el respaldo por capa de Inkscape).

## Hallazgos
- FloorPlanCAD dibuja cada pared con sus dos caras y los cierres, sin relleno y sin instance-id (siempre -1). Cada path es un solo segmento.
- Espesor típico: 2 unidades (viewBox de 100); va de 1 a 6 según la escala del plano.
- El 86 % de los planos son recortes: las paredes llegan al borde del viewBox, que se usa para cerrarlas.
- BLD-AR anota la pared rellena y la corta en columnas y aberturas; las L y T quedan en un mismo polígono.
- El respaldo por capa (capas con "WALL" o "墙体" sin semantic-id) aportaba el 27 % de los elementos y traía parquet, rayados y columnas.

## Limitaciones
- Se pierden las paredes dibujadas con una sola línea (~2 % de la longitud).
- Paredes más gruesas que ~1.2 veces el espesor del plano (~1.4 % de la longitud) pueden perderse o quedar sin cortar.
- Las columnas embebidas y los ductos angostos entre paredes quedan como parte de la pared.
