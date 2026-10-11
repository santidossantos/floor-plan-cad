# Mapeo de clases

**Decisión:** en BLD-AR se evalúan solo las clases que se dibujan y anotan igual que en FloorPlanCAD. Las demás clases de BLD-AR quedan excluidas, y se descartan las predicciones de las clases de FloorPlanCAD sin equivalente.

| FloorPlanCAD | BLD-AR       | Instancias en BLD-AR |
|--------------|--------------|---------------------:|
| wall         | wall         |                  964 |
| single_door  | door         |                  294 |
| window       | window       |                  269 |
| sliding_door | sliding_door |                   48 |
| stair        | stair        |                   79 |
| elevator     | elevator     |                   38 |
| railing      | railing      |                   33 |

## Clases de BLD-AR excluidas

| Clase de BLD-AR     | Instancias | Motivo                          |
|---------------------|-----------:|---------------------------------|
| column              |        668 | Sin equivalente en FloorPlanCAD |
| void                |        194 | Sin equivalente en FloorPlanCAD |
| parapet_wall        |        115 | Equivalencia dudosa             |
| pocket_door         |         26 | Equivalencia dudosa             |
| parapet_railing     |         22 | Equivalencia dudosa             |
| elevator_door       |         17 | Equivalencia dudosa             |
| cwall               |         16 | Equivalencia dudosa             |
| gutter              |         11 | Sin equivalente en FloorPlanCAD |
| ramp                |          9 | Sin equivalente en FloorPlanCAD |
| metal_roof          |          7 | Sin equivalente en FloorPlanCAD |
| horizontal_void     |          6 | Sin equivalente en FloorPlanCAD |
| finial              |          4 | Sin equivalente en FloorPlanCAD |
| car_elevator        |          3 | Equivalencia dudosa             |
| roof_flashing_metal |          3 | Sin equivalente en FloorPlanCAD |
| partition_wall      |          2 | Equivalencia dudosa             |
| vent_cap            |          2 | Sin equivalente en FloorPlanCAD |
| gate                |          1 | Equivalencia dudosa             |
| demolish            |          1 | Sin equivalente en FloorPlanCAD |

## Clases de FloorPlanCAD sin mapear

Se descartan sus predicciones al evaluar en BLD-AR: TV_cabinet, airconditioner, bath, bath_tub, bay_window, bed, bedside_cupboard, blind_window, chair, curtwall, double_door, escalator, gas_stove, opening_symbol, refrigerator, sink, sofa, squat_toilet, table, toilet, urinal, wardrobe, washing_machine.

## Hallazgos
- BLD-AR anota solo elementos de arquitectura (25 clases): no tiene muebles, sanitarios ni electrodomésticos.
- double_door no se mapea: la única puerta doble encontrada en BLD-AR está anotada como dos puertas, una por hoja, y FloorPlanCAD la anota como un solo polígono.
- wall: BLD-AR deja las L y T en un mismo polígono y corta en las columnas; FloorPlanCAD corta en los encuentros (ver `docs/PAREDES.md`).
