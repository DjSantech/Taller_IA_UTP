### 4.A Modelo común y arquitectura

Modelo el problema de dos maneras, como pide el enunciado:

- **Rutas parciales** (A\* y RBFS): un nodo es `(last, remaining, g, parent, closed)`. Se construye la ruta ciudad por ciudad.
- **Permutaciones completas** (HC, SA y GA): una ruta es una permutación `π = (s, π₁, …, π_{n−1})` con el origen fijo en la posición 0, y siempre es una solución *factible*; lo que cambia entre algoritmos es cómo se mejora.

El costo de una ruta completa incluye el regreso:  **C(π) = Σ_{i=0}^{n−2} d(π_i, π_{i+1}) + d(π_{n−1}, s)**.

| Componente del enunciado | Mi módulo | Evidencia |
|---|---|---|
| `TSPInstance` | `tsp/datos.py` | fichas y auditoría (sección 3) |
| `Tour` (validez y costo) | `tsp/modelo.py`: `tour_cost`, `tour_problems`, `is_valid_tour` | pruebas de cierre y duplicados |
| `SearchNode`, `MSTHeuristic` | `tsp/mst.py`, `tsp/astar.py` | trazas y pruebas exactas |
| `AStarSolver`, `RBFSSolver` | `tsp/astar.py`, `tsp/rbfs.py` | comparación con enumeración |
| `HillClimbingSolver`, `AnnealingSolver`, `GeneticSolver` | `tsp/hc.py`, `tsp/sa.py`, `tsp/ga.py` | curvas y repeticiones |
| `ExperimentRunner`, `RunResult` | `tsp/experimentos.py`, `RunResult` en `tsp/modelo.py` | tablas reproducibles |

**Una sola función de costo.** Todos los algoritmos llaman a `tour_cost`; ninguno duplica esa lógica. Así, si el costo estuviera mal, estaría mal en un único lugar y las pruebas lo detectarían de inmediato.

<!-- celda -->

### 4.B Contrato de salida y presupuestos

Cada ejecución devuelve un `RunResult` con los campos de la sección 4 y de la tabla 15: instancia, subconjunto, algoritmo, parámetros, semilla, ruta (o `None`), costo, gap, tiempo, memoria máxima, evaluaciones de candidatos, expansiones, nodos generados, llamadas a MST, tamaño máximo de la frontera, regeneraciones, motivo de parada y estado de optimalidad.

Tres decisiones que importan para interpretar los resultados:

1. **Ausencia explícita de ruta.** Si A\* o RBFS se interrumpen, el resultado es `tour = None`, `cost = None`, `NO_ROUTE`. No fabrico una ruta de respaldo; si algún día se usara una, el campo `fallback_route` la identificaría, porque no cuenta como ruta descubierta por A\* o RBFS.
2. **«Interrumpido» no es «fracaso» ni «óptimo».** Los motivos de parada son distintos (`OPTIMAL`, `EVAL_LIMIT`, `TIME_LIMIT`, `EXPANSION_LIMIT`, `MEMORY_LIMIT`, `LOCAL_OPTIMUM`, `COOLED`, …). Solo A\* y RBFS terminados sin interrupción llevan `PROVEN_OPTIMAL`. Los métodos locales **nunca** llevan certificado de optimalidad, aunque su ruta coincida con el óptimo publicado.
3. **Aleatoriedad controlada.** Cada semilla produce dos generadores independientes (uno para la ruta inicial y otro para las decisiones del algoritmo), sembrados con enteros. Así, cambiar un algoritmo no altera las rutas iniciales y los resultados se reproducen entre procesos.

**Presupuesto** (`Budget`): evaluaciones, segundos, expansiones y memoria. **Memoria**: `MemoryMeter` mide con `tracemalloc` la memoria *incremental* atribuible al solver. Declaro su límite: solo ve asignaciones de Python, no la memoria total del proceso ni la de extensiones en C.
