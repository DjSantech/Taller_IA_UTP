# Bitácora B — Búsqueda local (2-opt, HC, SA)

### B-01 · Pares válidos y sorteo uniforme
- **Decisión:** pares `(i, j)` con `j ≥ i+2` excluyendo `(0, n-1)`; el sorteo toma dos posiciones distintas, las ordena y rechaza el par si no es válido.
- **Alternativas:** sortear `i` y luego `j ∈ [i+2, n-1]`; mapear un índice a un par.
- **Por qué:** la segunda opción no es uniforme (los `i` pequeños tienen más `j`); el rechazo da uniformidad exacta y casi siempre acepta al primer intento.
- **Consecuencia:** el número de llamadas al generador por propuesta es variable, pero determinista por semilla. Hay una prueba estadística de uniformidad.

### B-02 · Presupuesto consultado antes de cada evaluación
- **Decisión:** `budget.check(evals)` antes de cada delta.
- **Alternativas:** comprobar después de cada pasada (se pasaría hasta n(n-3)/2 evaluaciones).
- **Por qué:** el enunciado exige no exceder el presupuesto (14.1).
- **Consecuencia:** `evals ≤ max_evals` siempre (probado). Si la última evaluación permitida cierra una pasada sin mejora, el resultado sí es `LOCAL_OPTIMUM`.

### B-03 · El costo de la ruta inicial no cuenta como evaluación
- **Decisión:** solo cuentan los deltas evaluados; la suma O(n) de la ruta inicial no.
- **Por qué:** es idéntico en HC y SA y es una sola vez; queda declarado (14.1 pide declarar, no necesariamente contar). El coordinador puede cambiarlo.
- **Consecuencia:** SA recibe `initial_evals` (parámetro opcional) para sumar la calibración de T0.

### B-04 · Mejoras estrictas en HC
- **Decisión:** `delta < 0`, nunca `<= 0`. **Por qué:** terminación garantizada; aceptar empates permite ciclar. SA, en cambio, acepta `delta <= 0` como pide la sección 11.

### B-05 · Reinicios: el primero siempre arranca
- **Decisión:** el primer ascenso de `hill_climbing_restarts` se inicia aunque el presupuesto sea 0 (se corta en su primera evaluación); los siguientes consultan el presupuesto antes.
- **Por qué:** hace falta devolver una ruta válida. Consecuencia útil: el primer reinicio es `random_tour(n, rng_init)`, la misma ruta inicial que recibirían HC y SA (comparación controlada).

### B-06 · Calibración de T0 y alternativa sin deltas positivos
- **Decisión:** mediana de Δ⁺ sobre 200 movimientos; si no hay positivos, mediana de |Δ| no nulos; luego mediana de pesos de aristas; luego 1.0.
- **Por qué:** T0 debe ser siempre > 0 y estar en las unidades del costo.

### B-07 · Series de SA con tope de puntos
- **Decisión:** un punto por ventana de 500 propuestas; al superar 2000 puntos se descarta uno de cada dos y se duplica el intervalo.
- **Por qué:** 30000 evaluaciones darían solo 60 puntos, pero ejecuciones largas no deben crecer sin límite. La tasa de aceptación de cada punto es la de su ventana (no un promedio de las saltadas).

### B-08 · `route_history`
- **Decisión:** HC guarda la ruta inicial (evals = 0) y cada mejora aplicada; SA guarda la inicial y cada **nueva mejor** ruta, no cada movimiento aceptado.
- **Por qué:** la animación muestra mejoras; guardar todos los movimientos aceptados de SA (miles) no aporta.

### B-09 · HALLAZGO — en eil51 HC no llega a un óptimo local con 30000 evaluaciones
- Una pasada cuesta 1224 evaluaciones; el ascenso desde una ruta aleatoria no termina. "HC con reinicios" hace 1 solo reinicio y es idéntico a HC de una ruta (557, 615, 589). Hay que advertirlo en el análisis para no atribuir al reinicio un efecto que no ocurrió. La primera mejora (445, 544, 445) rinde mucho más con ese presupuesto.

### B-10 · HALLAZGO — `steps` debe ajustarse al calendario
- Con `steps = 100` y `α = 0.995` el recocido agota las 30000 evaluaciones sin enfriar (EVAL_LIMIT) y rinde mal (eil51: 612 / 957). Se propone fijar `steps = (presupuesto − calibración) // ⌈ln(Tmin/T0)/ln α⌉` para que el enfriamiento termine (COOLED). Con esa regla las seis combinaciones α × p0 terminaron dentro del presupuesto.

### ERROR CORREGIDO — reinicios con presupuesto 0
- **Qué pasó:** la primera versión de `hill_climbing_restarts` consultaba el presupuesto *antes del primer ascenso*. Con `max_evals=0` el bucle terminaba sin haber creado ninguna ruta y `best_route` era `None`, por lo que `tour_cost(D, None)` habría lanzado un error.
- **Diagnóstico:** lo encontré al diseñar las pruebas de presupuesto exacto (caso límite 0), antes de ejecutarlas; no lo detectó una prueba fallida.
- **Corrección:** el chequeo previo se aplica solo a partir del segundo reinicio (`restarts > 0`); el primer ascenso se corta en su primera evaluación y devuelve la ruta inicial válida. Hay una prueba (`presupuesto 0` devuelve exactamente `random_tour(n, rng_init)`).
- **Lección:** los casos frontera del presupuesto (0, 1) deben probarse para cada solver, porque una ruta que devolver es parte del contrato.
