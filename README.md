# Taller 1 — Hunt-and-Kill y Búsqueda no Informada

**Curso:** Inteligencia Artificial (UTP) · **Referencia:** Russell & Norvig, *AIMA* 4.ª ed., cap. 3
**Modalidad:** individual

## Qué es este repositorio

Se entrega únicamente un generador de laberintos perfectos (algoritmo **Hunt-and-Kill**).
A partir del grafo que produce, hay que **diseñar, implementar, verificar y comparar**
algoritmos de búsqueda no informada en tres versiones independientes:

1. **Desde cero** — sin bibliotecas de búsqueda ni de grafos.
2. **SimpleAI** — modelando el laberinto como `SearchProblem`.
3. **AIMA-Python** — modelando el laberinto como subclase de `Problem`.

El producto evaluado es el cuaderno
[`Taller_Hunt_and_Kill_Busqueda_No_Informada.ipynb`](Taller_Hunt_and_Kill_Busqueda_No_Informada.ipynb),
que debe ejecutarse de arriba abajo en un entorno limpio, sin celdas fuera de orden
ni resultados pegados a mano.

## Estructura

| Ruta | Contenido |
|---|---|
| `Taller_Hunt_and_Kill_Busqueda_No_Informada.ipynb` | Cuaderno entregable (enunciado + solución) |
| `BITACORA.md` | Bitácora de decisiones de diseño y errores corregidos |
| `requirements.txt` | Dependencias con versión fijada |
| `resultados/` | Salidas regenerables del protocolo experimental |
| `aima/` | AIMA-Python vendorizado sin modificar (commit `bbf6bc2`, licencia MIT) |
| `tools/ejecutar_cuaderno.py` | Ejecuta el cuaderno completo en un kernel nuevo |

## Reproducir

```bash
# El entorno se crea FUERA de la carpeta sincronizada por OneDrive (ver D-03).
python -m venv C:\Users\<usuario>\venvs\ia-taller1
C:\Users\<usuario>\venvs\ia-taller1\Scripts\activate
pip install -r requirements.txt
python -m ipykernel install --user --name ia-taller1 --display-name "Python (ia-taller1)"
jupyter lab                      # seleccionar el kernel "Python (ia-taller1)"
```

Entorno verificado: **Python 3.13.7 / Windows 11**. SimpleAI 0.8.3 importa y
ejecuta correctamente en Python 3.13, comprobado con un `SearchProblem` mínimo.

Todo resultado aleatorio depende de una **semilla explícita**; no hay estado global oculto.

## Plan de trabajo por etapas

Cada etapa cierra con un commit propio, de modo que el historial muestre el proceso.

| Etapa | Contenido | Estado |
|---|---|---|
| 0 | Estructura del repositorio, entorno y bitácora | ✅ |
| 1 | Auditoría del generador Hunt-and-Kill + pruebas de invariantes | ✅ |
| 2 | Instancia individual reproducible y formulación formal del espacio de estados | ✅ |
| 3 | Contrato `ResultadoBusqueda`, núcleo de búsqueda en grafo, DFS y BFS | ✅ |
| 4 | Búsqueda de costo uniforme (UCS) con entradas obsoletas | ✅ |
| 5 | Búsqueda limitada en profundidad (DLS) y profundización iterativa (IDDFS) | ✅ |
| 6 | Búsqueda bidireccional | ✅ |
| 7 | Algoritmo de Lee y visualización del frente de onda | ✅ |
| 8 | Versión SimpleAI e instrumentación de métricas | ✅ |
| 9 | Versión AIMA-Python e instrumentación de métricas | ✅ |
| 10 | Pruebas de aceptación, casos límite y concordancia entre versiones | ✅ |
| 11 | Segunda familia de problemas: ciclos y costos no unitarios | ✅ |
| 12 | Protocolo experimental (≥30 instancias) y gráficas obligatorias | ✅ |
| 13 | Análisis teórico, conclusiones y referencias | 🚧 |
| 14 | Preparación de la defensa oral | ⬜ |

## Referencias

Las fuentes consultadas se citan en la sección 14 del cuaderno y en `BITACORA.md`.
