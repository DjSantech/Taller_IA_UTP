# Taller 2 — El problema del viajante (TSP)

**Curso:** Inteligencia Artificial (UTP) · **Referencia:** Russell & Norvig, *AIMA* 4.ª ed., caps. 3 y 4
**Modalidad:** en pareja · **Integrantes:** Santiago y Januar Mena

A\* con MST · RBFS · Hill Climbing · Simulated Annealing · Algoritmo genético, implementados
desde cero y comparados en cuatro instancias de TSPLIB (att48, berlin52, brazil58, gr48).
Pregunta central: *¿qué se gana y qué se pierde al cambiar garantía de optimalidad por rapidez,
diversidad o menor consumo de memoria?*

El entregable es [`Taller_IA_TSP_AStar_MST_HC_SA_GA_RBFS.ipynb`](Taller_IA_TSP_AStar_MST_HC_SA_GA_RBFS.ipynb):
el enunciado del profesor completado (primer commit `e10a4f7` = enunciado intacto), con código,
pruebas, mediciones y apuntes de exposición debajo de cada sección.

## Estructura

| Ruta | Contenido |
|---|---|
| `Taller_IA_TSP_…ipynb` | Cuaderno entregable (generado por `tools/construir_cuaderno.py`, con salidas guardadas) |
| `tsp/` | Paquete con el código fuente de cada módulo (fuente de verdad del cuaderno) |
| `tests/` | Pruebas `pytest` de todos los módulos |
| `datos/` | Instancias TSPLIB, rutas óptimas oficiales y óptimos (`tools/descargar_datos.py` los regenera) |
| `celdas/` | Celdas de código propias del cuaderno (fichas, calibración, escalas A y B, figuras) |
| `apuntes/` | Texto de exposición que se inserta en el cuaderno + bitácoras por módulo |
| `BITACORA.md` | Decisiones de diseño y errores corregidos |
| `resultados/` | Registros regenerables (`*.csv`, figuras, animación) |
| `tools/` | Descarga de datos, construcción del cuaderno, ejecución en kernel limpio, fusión de salidas |

## Reproducir

```bash
# El entorno se crea FUERA de la carpeta sincronizada por OneDrive (decisión D-03).
python -m venv C:\Users\<usuario>\venvs\ia-taller2
C:\Users\<usuario>\venvs\ia-taller2\Scripts\activate
pip install -r requirements.txt
python -m ipykernel install --user --name ia-taller2 --display-name "Python (ia-taller2)"
python tools/descargar_datos.py datos        # opcional: ya están en el repositorio
python -m pytest tests -q                    # pruebas de los módulos
python tools/construir_cuaderno.py           # regenera el cuaderno desde el enunciado y los módulos
python tools/ejecutar_cuaderno.py            # lo ejecuta en un kernel nuevo (falla en la primera celda con error)
```

Entorno verificado: Python 3.13.7 · Windows 11. Todo resultado aleatorio depende de una semilla
explícita (evaluación: 0–9; calibración: 100–104).

## Ayuda externa

Desarrollado con ayuda de un asistente de IA (Claude, mediante Claude Code); ver la sección A del
cuaderno y las decisiones D-14 y D-15 de la bitácora.
