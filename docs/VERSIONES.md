# Versiones

Versiones fijas de las librerías del modelo, para instalarlas en scripts y notebooks:

| Librería | Versión |
|---|---|
| ultralytics | 8.4.173 |
| sahi | 0.12.8 |

```bash
pip install ultralytics==8.4.173 sahi==0.12.8
```

## Por qué fijarlas
Los resultados de la tesis tienen que poder reproducirse, en el servidor y en cualquier otra máquina. `ultralytics` saca versiones muy seguido: solo en la serie 8.4 hay más de 170.

## Riesgos de no fijarlas
- **Resultados distintos:** si cambian los valores por defecto (hiperparámetros, augmentations, cálculo de métricas), dos entrenamientos con el mismo notebook no son comparables.
- **Pesos incompatibles:** un modelo guardado con una versión puede no cargar en otra.
- **SAHI roto:** `sahi` usa la API de `ultralytics`; un cambio en esa API puede romper la inferencia por tiles.
- **Entornos distintos:** `pip install` sin versión instala la última del momento, así que el servidor y la máquina local pueden terminar con versiones diferentes sin que se note.
