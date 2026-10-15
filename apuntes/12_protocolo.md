### G.1. Protocolo experimental: lo que decidí antes de medir

Antes de ejecutar nada congelé el protocolo en un diccionario (`FROZEN`): semillas 0 a 9, tamaños $k\in\{6,8,10,12\}$, presupuestos y límites de los exactos. Lo hice así para que ninguna decisión dependa de qué algoritmo "sale ganando". Los parámetros de SA y GA se calibran con datos de calibración separados de los de evaluación y solo después se congelan; el código se niega a hacer la corrida final si siguen marcados como provisionales.

<!-- celda -->

#### Las dos escalas

**Escala A (subinstancias).** De cada instancia tomo los primeros $k$ identificadores ordenados y conservo los pesos originales entre ellos. Registro el **listado de nodos**, no solo $k$, porque el óptimo del subproblema depende de esos nodos concretos. Aquí A* y RBFS sí pueden terminar, así que:

- A* y RBFS: una ejecución por caso, más una ejecución con otro origen para comprobar que el costo óptimo es invariante (si cambia, el programa se detiene: hay un error).
- HC, HC con reinicios, SA y GA: diez semillas por caso.
- El gap se calcula contra el óptimo del **subproblema**, solo si fue certificado por A*/RBFS o por enumeración (programación dinámica de Held-Karp, independiente de A*/RBFS, para $k\le 10$). Nunca contra el óptimo oficial de la instancia completa.

**Escala B (instancias completas).** att48, berlin52, brazil58 y gr48. HC, HC con reinicios, SA y GA corren diez semillas con hasta 30000 evaluaciones y 30 s; A* y RBFS hacen **un ensayo diagnóstico** con los mismos límites de exactos, sin exigirles ruta ni prueba de optimalidad.

<!-- celda -->

#### Qué significa presupuesto comparable

Una evaluación es decidir el costo de un candidato (aunque use delta). En GA cuento cada cromosoma evaluado, incluida la población inicial. En SA, el trabajo de calibrar $T_0$ se **descuenta del presupuesto y se suma** a sus evaluaciones y a su tiempo: si no, SA tendría ventaja oculta frente a HC. A* y RBFS no se miden en evaluaciones, porque una expansión (generar sucesores, calcular el MST) no equivale a evaluar una ruta de GA; los comparo por tiempo, memoria y sus propios contadores. Reconozco que el presupuesto de evaluaciones aproxima un esfuerzo común, pero no asegura que cada evaluación cueste lo mismo, por eso también reporto tiempo.

<!-- celda -->

#### Cómo evito sesgo

- **Semillas independientes:** `make_rngs(semilla)` entrega un generador para la ruta inicial y otro para las decisiones del algoritmo. HC y SA con la misma semilla parten de **la misma ruta inicial**; cambiar la implementación de un algoritmo no altera las rutas iniciales.
- **Mismos límites para todos:** los presupuestos se fijan una vez y se aplican de forma uniforme.
- **Auditoría automática de cada ejecución:** la ruta debe ser una permutación válida y su costo debe coincidir con el recalculado con la función única de costo. Un **gap negativo** frente a un óptimo certificado lanza `AuditError` y detiene todo: un algoritmo no puede ganarle al óptimo, así que el error está en datos, ruta o costo.
- **Sin óptimo certificado, el gap es `N/A`.** No sustituyo $C^*$ por la mejor ruta del grupo.
- **Gráficas fuera del tiempo medido** y siempre a partir de los registros guardados.

<!-- celda -->

#### Qué significa cada métrica

- **Gap (%)** $=100\,(C-C^*)/C^*$ frente al óptimo de referencia; un gap de 0 significa igualar la referencia, no que el método sea exacto.
- **Repeticiones válidas/previstas:** el denominador siempre se muestra. Una ejecución *censurada* es la que paró por un límite de tiempo, expansiones o memoria; no tiene ruta, su costo y gap son `N/A`, y un promedio solo sobre las que terminaron ocultaría justo las difíciles. Parar por el tope de evaluaciones en HC/SA/GA no es censura: es el presupuesto de diseño.
- **Mediana y desviación estándar muestral** ($n-1$) del costo y del gap, **mejor costo**, **tasa de coincidencia** con el óptimo de referencia y **mediana del tiempo**.
- **No promedio costos crudos de instancias distintas**: sus escalas no se relacionan; entre instancias comparo gaps.
- **Memoria:** `tracemalloc`, memoria incremental atribuible al solver y solo de asignaciones de Python (no la del proceso completo).

<!-- celda -->

#### Tiempo, paralelismo y entorno

El tiempo se mide con `perf_counter` alrededor de todo el método (ruta inicial y calibración incluidas); la carga de datos se mide aparte. El paralelismo por procesos existe pero está apagado por omisión: con varios procesos compitiendo por CPU y caché el tiempo medido puede inflarse, así que la corrida final se hace en serie. En la sección A declaro CPU, sistema operativo, versión de Python y paquetes, y la herramienta de memoria.
