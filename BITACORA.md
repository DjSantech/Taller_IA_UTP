# Bitácora de decisiones — Taller 2 (TSP)

Registro breve de las decisiones de diseño, los errores cometidos y su corrección.
Cada entrada: **Decisión · Alternativas · Por qué · Consecuencia**. Los errores
corregidos llevan la marca **ERROR CORREGIDO**; son material directo para la sustentación.

---

## Etapa 0 — Estructura, entorno y datos

### D-01 · El entregable es el propio cuaderno del profesor, construido desde módulos probados
- **Decisión:** el código vive en el paquete `tsp/` (un módulo por responsabilidad, con
  pruebas en `tests/`) y `tools/construir_cuaderno.py` inserta ese mismo código en las
  celdas del cuaderno del enunciado, conservando sus secciones y su pseudocódigo.
- **Alternativas:** escribir todo directamente en celdas; entregar un cuaderno delgado que importe el paquete.
- **Por qué:** los módulos se prueban con `pytest` y se pueden desarrollar en paralelo;
  pero la entrega exige un cuaderno que se ejecute de arriba abajo con datos locales y sin
  dependencias implícitas, así que el código que se ejecuta en el cuaderno debe estar *en* el cuaderno.
- **Consecuencia:** los módulos solo pueden importar de módulos anteriores en el orden
  `datos → modelo → mst → astar → rbfs → vecindad → hc → sa → ga → experimentos`.

### D-02 · Primer commit con el enunciado intacto
- El commit `e10a4f7` contiene el cuaderno exactamente como lo entregó el profesor.
  Hace verificable en el historial qué es del docente y qué es propio.

### D-03 · Entorno virtual fuera de OneDrive
- `C:\Users\santi\venvs\ia-taller2`, con versiones fijadas en `requirements.txt`
  (misma razón que D-03 del Taller 1: OneDrive sincronizaría miles de archivos y puede corromper el entorno).

### D-04 · Misma repo de GitHub, rama independiente `taller-2`
- **Decisión:** rama huérfana `taller-2` del repositorio `DjSantech/Taller_IA_UTP`
  (el Primer Taller vive en `main`). No se hace `push` sin orden explícita.
- **Por qué:** el repo ya existe y se pidió usarlo, pero mezclar en `main` los archivos
  de los dos talleres ensuciaría ambos historiales.

### D-05 · Identificadores en inglés, explicaciones en español
- El enunciado lo pide expresamente («nombres sugeridos … en inglés; explicaciones y conclusiones en español»).
  El Taller 1 usó identificadores en español; aquí se sigue la regla nueva.

### D-06 · Ciudades por posición, identificadores aparte
- **Decisión:** todos los algoritmos trabajan con posiciones `0..n-1`; `TSPInstance.node_ids`
  guarda la correspondencia con los identificadores reales del archivo.
- **Por qué:** el enunciado (§3.1) prohíbe suponer que el nodo `i` está en la posición `i-1`.
- **Origen fijo:** posición 0 (el identificador menor). Un parámetro `origin` permite cambiarlo
  para la prueba de invarianza del costo óptimo.

### D-07 · Semillas enteras y generadores independientes
- **Decisión:** `make_rngs(seed)` devuelve dos `random.Random` sembrados con enteros
  (`1000003*seed+1` para la ruta inicial y `+2` para las decisiones del algoritmo).
- **Alternativas:** sembrar con cadenas o con `hash(...)`; un único generador compartido.
- **Por qué:** (a) el enunciado exige generadores independientes para que cambiar un algoritmo
  no altere las rutas iniciales; (b) la lección de D-08 del Taller 1: lo que depende de `hash`
  puede variar entre procesos (`PYTHONHASHSEED`), un entero no.

### D-08 · Memoria incremental con `tracemalloc`
- **Decisión:** `MemoryMeter` mide la memoria *incremental* atribuible al solver con
  `tracemalloc`, descontando la base previa.
- **Límite declarado:** solo cuenta asignaciones de Python; no es la memoria del proceso
  completo (§14.1 exige distinguirlas y declarar la herramienta).

### D-09 · ERROR CORREGIDO — `gr48` numerado 0..47 por la biblioteca, 1..48 por los archivos
- **Qué se hizo primero:** `node_ids = sorted(problem.get_nodes())` para todas las instancias.
- **Qué falló:** la prueba que lee `gr48.opt.tour` lanzó `KeyError: 48`. Para instancias
  `EXPLICIT` sin coordenadas, `tsplib95` numera los nodos de 0 a n-1 (`gr48`, `brazil58`,
  `gr17`), mientras que el archivo `.opt.tour` y la convención TSPLIB usan 1 a n.
- **Por qué importa:** si la prueba no hubiera existido, las rutas de salida habrían quedado
  desplazadas en uno, y cualquier comparación con una ruta oficial habría sido absurda.
  Es exactamente la advertencia del enunciado sobre no presuponer la numeración.
- **Corrección:** se separan las *claves de `get_weight`* (internas) de los *identificadores reales*
  (`posición+1` en las explícitas). Tras el cambio, el tour óptimo oficial de `gr48` cuesta
  **5046**, el valor publicado: eso confirma que la matriz está bien leída.
- **Lección:** verificar los datos contra una ruta oficial *conocida* detecta errores de
  lectura que ninguna auditoría de simetría o diagonal puede ver.

### D-10 · Auditoría de datos
- Para las 7 instancias: dimensión, simetría, diagonal cero y pesos no negativos
  (`_audit_matrix`); fórmulas EUC_2D y ATT recalculadas por separado y comparadas contra la
  biblioteca en **todos** los pares de `berlin52` y `att48`; costo de los `.opt.tour`
  oficiales (att48, berlin52, gr48) verificado contra los óptimos publicados.


---

## Etapas 3 a 7 — Modelo de estados, MST, A* y RBFS (prefijo A-)

# Bitácora A — algoritmos exactos (MST, A\*, RBFS)

Formato: **Decisión · Alternativas · Por qué · Consecuencia**. Los errores reales llevan la marca **ERROR CORREGIDO** con *Qué pasó / Diagnóstico / Corrección / Lección*.

---

### A-01 · Pendientes como máscara de bits
- **Decisión:** `remaining` es un entero (bit *v* encendido = la ciudad *v* falta). El bit del origen nunca se enciende.
- **Alternativas:** `frozenset` de ciudades; tupla ordenada.
- **Por qué:** es inmutable y hashable, quitar una ciudad es `mask ^ bit` en O(1) y ocupa mucho menos memoria que un `frozenset` por nodo, y la memoria es una variable medida en el taller.
- **Consecuencia:** hace falta `mask_cities` para pasar a lista cuando se calcula el MST (O(n)); el costo es menor que el del propio MST.

### A-02 · Clave de estado `(last, remaining, closed)`
- **Decisión:** la clave del enunciado, sin añadir profundidad ni costo.
- **Alternativas:** solo la última ciudad; última ciudad + profundidad.
- **Por qué:** dos nodos con esta clave tienen exactamente las mismas continuaciones, así que se conserva el de menor $g$. Con solo la ciudad se descartan rutas parciales que sí llegan al óptimo (contraejemplo de 5 ciudades, A-11).
- **Consecuencia:** el diccionario `bestG` crece con el número de estados distintos (hasta $n2^{n-2}$).

### A-03 · Prim O(|U|²) con "mejor costo de conexión"
- **Decisión:** vector `best[j]` con la arista más barata de cada pendiente hacia lo ya conectado, eliminando por intercambio con el último elemento.
- **Alternativas:** Prim conceptual O(|U|³); Kruskal con ordenación.
- **Por qué:** es el O(|U|²) que pide la sección 6.1 y es el más natural con matriz densa.
- **Consecuencia:** `mst_edges` es una segunda implementación (con origen de cada arista) para validar que es árbol; ambas se contrastan con un Kruskal escrito en el test.

### A-04 · Desempate `(f, h, contador)`
- **Decisión:** a igual $f$, menor $h$; a igual, FIFO. Sucesores por posición ascendente.
- **Alternativas:** solo contador; mayor $g$ explícito.
- **Por qué:** menor $h$ con igual $f$ equivale a mayor $g$ y favorece nodos avanzados y cerrados; el contador además impide comparar nodos.
- **Consecuencia:** en el microcaso $B$ ($h=10$) se expande antes que $E$ ($h=11$), ambos con $f=14$. El costo no depende del desempate.

### A-05 · Memoria cada 256 expansiones — ERROR CORREGIDO (antes de ejecutar)
- **Decisión:** `MEM_CHECK_EVERY = 256`; tiempo y expansiones se consultan en cada iteración.
- **Alternativas:** medir memoria en cada expansión; cada 1 000.
- **Por qué:** `tracemalloc.get_traced_memory` en cada iteración añade ruido; 256 expansiones es granularidad suficiente. Consecuencia declarada: la memoria puede rebasar el límite hasta ~256 expansiones antes de detectarse.
- **ERROR CORREGIDO — Qué pasó:** mi primera versión comprobaba `expanded % 256 == 0` en cada vuelta del bucle.
- **Diagnóstico:** al revisar el código vi que, si la frontera tiene muchas entradas obsoletas seguidas, `expanded` no cambia y la condición se cumple repetidamente: se mediría la memoria decenas de veces seguidas.
- **Corrección:** `next_mem_check`: se mide cuando `expanded >= next_mem_check` y se avanza 256. Misma lógica en RBFS.
- **Lección:** una condición sobre un contador que no avanza en todas las iteraciones puede dispararse en rachas.

### A-06 · Qué es "regeneración" en RBFS y registro de auditoría
- **Decisión:** regeneración = expandir un nodo (identificado por su camino) ya expandido antes. `audit=True` guarda un conjunto de hashes de 64 bits de los caminos; `audit=False` cuenta solo la re-expansión del mismo registro vivo (cota inferior).
- **Alternativas:** identificar por estado `(last, remaining)`; guardar caminos completos.
- **Por qué:** por estado confundiría ramas distintas con regeneración; caminos completos gastarían mucha más memoria. El hash de 64 bits es compacto y su probabilidad de colisión es despreciable.
- **Consecuencia:** el registro cuesta ~70 B por camino distinto (brazil58, k=8: pico 76 532 B con auditoría, 10 736 B sin ella) y la cota inferior es floja (826 frente a 56 374 exactas). Las tablas de memoria de RBFS usan `audit=False`.

### A-07 · `upper_bound` en A\*
- **Decisión:** podar hijos con $g+h>$ cota. Si sale un cerrado, es óptimo; si se agota la frontera, solo se afirma que no existe ruta ≤ cota (`EXHAUSTED`, `NO_ROUTE`, nota en `extras`).
- **Por qué:** $h$ admisible hace segura la poda, y no confundir la ruta de la cota con una descubierta por A\* (sección 4).

### A-08 · Hallazgo: la heurística MST es consistente
- **Decisión:** analizar la consistencia con demostración y con comprobación.
- **Resultado:** 0 violaciones en 37 998 transiciones y en 2 394 204 de una búsqueda previa de contraejemplos; la demostración usa MST($U$) ≤ MST($U\setminus w$) + mín $d(w,u)$, mín $d(v,u)\le d(v,w)$ y que el mínimo sobre un conjunto mayor no sube.
- **Consecuencia:** $g+h$ no baja a lo largo de una ruta, pero se conserva `bestG` y las entradas obsoletas (un estado puede generarse antes por un camino caro y mejorar mientras sigue en la frontera).

### A-09 · ERROR CORREGIDO — "el máximo de RBFS es neutro con una cota consistente"
- **Qué pasó:** en una primera redacción de la prueba y de la guía de estudio escribí que, al ser $h$ consistente, `max(g+h, node.f)` nunca cambiaba el valor.
- **Diagnóstico:** al preparar el ejemplo de por qué se usa el máximo vi que después de un retroceso el $f$ respaldado de un nodo (14 en la traza de 4 ciudades) supera su $g+h$ (12), y los hijos regenerados lo heredan. Lo comprobé instrumentando el código: en att48 k=8 el máximo elevó 235 de 1 493 hijos.
- **Corrección:** renombré la prueba (ahora solo afirma que $g+h$ no decrece), añadí el contador `raised_by_max` y la prueba `test_rbfs_el_maximo_transmite_el_valor_respaldado`, y corregí la guía.
- **Lección:** consistencia de $h$ no es consistencia del $f$ respaldado; hay que distinguir el $f$ estático del $f$ aprendido.

### A-10 · ERROR CORREGIDO — número equivocado en una aserción
- **Qué pasó:** en la prueba de las dos rutas parciales fusionables escribí a ojo que el total de la ruta $X$ era 23.
- **Diagnóstico:** la prueba falló (14 ≠ 23). Recalculé: $X=A\!-\!B\!-\!D$ tiene $g=2$ y mejor continuación $D\!-\!C\!-\!E\!-\!A=1+10+1=12$, total 14.
- **Corrección:** valor 14 en la aserción; sigue siendo mayor que el óptimo 5 de $Y$, que es lo que demuestra el contraejemplo.
- **Lección:** los números de las pruebas salen de calcularlos con el oráculo, no de estimarlos mentalmente.

### A-11 · ERROR CORREGIDO — qué falla con la clave "solo ciudad"
- **Qué pasó:** esperaba que la variante con clave `(última ciudad, closed)` devolviera una ruta *más cara*. Mi primer script de búsqueda de contraejemplos además lanzó `KeyError` porque inicialicé `bestG` con una clave distinta de la que consultaba.
- **Diagnóstico:** tras unificar la clave, probé miles de matrices de 5 a 7 ciudades: la variante nunca dio una ruta más cara; o acertaba o **no hallaba ninguna** (frontera vacía).
- **Corrección:** el contraejemplo del test afirma exactamente eso (`malo is None or malo.g > óptimo`) y la explicación dice que el daño es perder rutas y la garantía. La demostración conceptual sigue siendo el par $X$/$Y$ con totales 14 y 5.
- **Lección:** no afirmar un modo de falla que no se pudo reproducir.

### A-12 · ERROR CORREGIDO — medición con tiempo imposible
- **Qué pasó:** en la primera tanda de medidas, A\* en att48 completa con tope de 10 s reportó `elapsed_seconds = 3975` con solo 16 expansiones.
- **Diagnóstico:** 3975 s no es coherente con 16 expansiones ni con el tope; el reloj saltó (probablemente el equipo se suspendió mientras corría en segundo plano; no lo pude verificar). Las expansiones y los contadores no se afectan, el tiempo sí.
- **Corrección:** repetí esa ejecución sola: 765 expansiones, 10.04 s, `TIME_LIMIT`. Las demás filas de la tanda son coherentes.
- **Lección:** validar cada medición contra otra variable (aquí, expansiones por segundo) antes de citarla.

### A-13 · Viabilidad de los límites propuestos (30 s, 100 000 expansiones, 256 MiB)
- **Hallazgo:** A\*+MST termina todas las subinstancias k ≤ 12 de las cuatro instancias (máximo 4 478 expansiones, 2.4 MB, 0.55 s). RBFS no: en brazil58 k=10 llega a 100 000 expansiones (13.5 s) y en k=12 al tiempo (30 s), y berlin52 k=12 tarda 28.1 s (casi el límite). El límite de memoria nunca se alcanza en estas pruebas (máximo ≈ 14 MB de A\* en instancias completas a 10 s).
- **Decisión:** mantener los límites propuestos y tratar las interrupciones de RBFS como resultados censurados, no como errores; reportarlos con denominador.
- **Consecuencia:** la medición con `tracemalloc` multiplica el tiempo por ≈ 5–9; por eso existe `measure_memory=False`. Las cifras de memoria varían entre corridas (p. ej. 487 KB y 628 KB para el mismo caso).


---

## Etapas 8 y 9 — 2-opt, Hill Climbing y Simulated Annealing (prefijo B-)

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


---

## Etapa 10 — Algoritmo genético (prefijo C-)

# Bitácora C — Algoritmo genético (Taller 2)

Formato: **Decisión · Alternativas · Por qué · Consecuencia**. Los errores reales llevan **ERROR CORREGIDO**.

---

### C-01 · Cromosoma sin el origen
- **Decisión:** el cromosoma tiene las n−1 ciudades distintas del origen; se decodifica anteponiendo el origen.
- **Alternativas:** permutación completa con el origen dentro; rotar al origen tras cada operador.
- **Por qué:** con el origen fuera, ningún operador puede moverlo o duplicarlo y no hace falta reparar rutas.
- **Consecuencia:** el parámetro `origin` funciona para la prueba de invarianza (`test_otro_origen_es_valido`).

### C-02 · OX literal del pseudocódigo
- **Decisión:** `_ox(parent1, parent2, left, right)` copia el segmento en las mismas posiciones y rellena desde right+1 en círculo con los genes de parent2 leídos desde right+1.
- **Alternativas:** variantes de OX que rellenan desde el inicio del cromosoma.
- **Por qué:** el enunciado fija ese pseudocódigo, y la actividad manual (hijo `[G,C,D,E,F,B]`) debe poder comprobarse a mano.
- **Consecuencia:** función pura, genérica sobre cualquier tipo de gen, probada con letras y con miles de cortes.

### C-03 · Contabilidad: copias heredadas no cuentan
- **Decisión:** las élites y las copias exactas de un padre (sin cruce ni mutación) heredan su costo y no suman evaluaciones; se anotan en `reused_costs`.
- **Alternativas:** reevaluar todo hijo; cache general por ruta.
- **Por qué:** 14.1 dice que las élites con costo conservado no se reevalúan, y una copia sin cambios es el mismo caso; una cache general añadiría una política que habría que medir.
- **Consecuencia:** el costo exacto de una generación varía (≤ población − élites); la prueba de presupuesto exacto usa `pc=1`, `pm=0`.

### C-04 · Reserva del peor caso antes de cada generación
- **Decisión:** si `evals + (población − élites) > max_evals`, paro antes con `EVAL_LIMIT`.
- **Alternativas:** generar a medias y descartar; usar todo el presupuesto.
- **Por qué:** 14.1: «no exceda el presupuesto para completar una generación».
- **Consecuencia:** con 30000 evaluaciones y población 80 sobran decenas de evaluaciones sin usar (p. ej. 29922–29976 usadas); es un costo asumido y documentado.

### C-05 · Duplicados permitidos; diversidad canónica
- **Decisión:** no filtro duplicados; mido `unique_fraction` con forma canónica (rotada al origen, menor entre ruta e inversa) y `edge_diversity`.
- **Alternativas:** rechazar hijos repetidos; contar rutas tal cual.
- **Por qué:** filtrar gasta evaluaciones y oculta la convergencia; contar rutas sin canonizar trata como distintos dos ciclos iguales.
- **Consecuencia:** la canonización no altera costo porque `D` es simétrica (probado).

### C-06 · Memético en archivo aparte
- **Decisión:** `tsp/memetico.py` (algorithm `GA+2opt`) con 2-opt de primera mejora, cada delta cuenta 1 evaluación y se desglosa en `ls_evals`/`child_evals`.
- **Alternativas:** un flag en `genetic_algorithm`.
- **Por qué:** 12.1 pide compararlo aparte y no atribuir al cruce la mejora de la búsqueda local; la reserva del peor caso no es posible porque el trabajo de 2-opt no se conoce de antemano.
- **Consecuencia:** puede terminar a mitad de generación (nunca excede el presupuesto). Hallazgo: en eil51 con 30000 evaluaciones gasta casi todo en la población inicial (0 generaciones); queda `ls_max_evals` como palanca para la calibración.

### ERROR CORREGIDO · Restos de código en el bucle de generaciones
- **Qué pasó:** en la primera versión de `ga.py` quedaron líneas provisionales (`if ... if False else False: pass`, una variable `p1_idx` que no estaba definida y una variable `inherited` sin uso).
- **Diagnóstico:** lo vi al releer el archivo, antes de ejecutarlo; habría fallado con `NameError` en cuanto una copia de padre no se cruzara ni mutara.
- **Corrección:** el torneo guarda los índices `p1_idx`/`p2_idx` y se eliminaron las líneas provisionales.
- **Lección:** releer el código recién escrito antes de la primera ejecución; los marcadores temporales no se dejan en el archivo.

### ERROR CORREGIDO · Prueba de «mejoras estrictas» incluía el punto final de la traza
- **Qué pasó:** `test_ruta_valida_y_costo_coherente` falló al exigir que todos los costos de `trace` fueran estrictamente decrecientes.
- **Diagnóstico:** el último punto de la traza es el cierre (mismas evaluaciones finales) y repite el mejor costo; no es una mejora.
- **Corrección:** la prueba compara solo `trace[:-1]` y verifica aparte que el último punto coincide con el resultado.
- **Lección:** la especificación de la traza (inicio, mejoras y final) hace que el final sea un punto distinto; la prueba debía reflejarla.

### Nota de entorno
- Mi script de cordura compartía la carpeta temporal de sesión con otro agente, que sobrescribió un archivo del mismo nombre. Mis cifras salieron de la ejecución anterior a ese cambio (impresas en pantalla y copiadas a los apuntes); no hubo efecto en el código del proyecto.


---

## Etapas 12 y 13 — Experimentos y gráficas (prefijo E-)



### E-01 · Configuración congelada en un diccionario, con marcador de calibración
- **Decisión:** `FROZEN` guarda semillas, $k$, presupuestos y límites; SA y GA llevan `"calibrated": False` hasta que el coordinador fija los valores.
- **Alternativas:** constantes sueltas en las celdas; valores por omisión silenciosos.
- **Por qué:** el enunciado pide fijar la configuración antes de la evaluación principal. `assert_frozen` se niega a continuar si siguen provisionales.
- **Consecuencia:** una corrida final con parámetros sin calibrar es imposible por accidente.

### E-02 · Solvers por importación perezosa e inyectables
- **Decisión:** `_solver(clave, solvers)` busca primero un solver inyectado, luego el nombre ya definido en el espacio global (cuaderno) y por último el módulo `tsp.*`.
- **Alternativas:** `import` al principio del módulo.
- **Por qué:** los solvers se escribieron en paralelo; así el protocolo se probó con solvers falsos antes de que existieran los reales, y el módulo sigue funcionando al concatenarse en el cuaderno.
- **Consecuencia:** el protocolo tiene pruebas que no dependen de los algoritmos, y pruebas de integración que se omiten si falta un módulo.

### E-03 · El cronómetro envuelve todo el método; la calibración de SA se cuenta
- **Decisión:** `elapsed_seconds` es el `perf_counter` total de `run_one`. En SA, las evaluaciones y el tiempo de `calibrate_t0` se restan del presupuesto, se suman a `candidate_evaluations` y desplazan la traza.
- **Alternativas:** usar el tiempo interno del solver; dejar la calibración gratis.
- **Por qué:** §14.1 exige registrar la calibración y no excluir sin documentar la ruta inicial; sin esto SA tendría ventaja oculta sobre HC.
- **Consecuencia:** las curvas de HC y SA son comparables en el eje de evaluaciones y de tiempo.

### E-04 · Certificado del subproblema independiente de A*/RBFS
- **Decisión:** para $k\le 10$ el óptimo también se calcula con Held-Karp; si dos certificados chocan, `AuditError`.
- **Alternativas:** confiar solo en A*/RBFS.
- **Por qué:** un error compartido en la heurística MST haría que A* y RBFS coincidieran en un valor equivocado; un método independiente lo delata.
- **Consecuencia:** el "óptimo certificado" de la tabla de subinstancias indica su fuente.

### E-05 · Resultados guardados en CSV (planos) y JSON (completos)
- **Decisión:** `save_rows_csv` guarda una fila por ejecución; `save_results_json` guarda además `trace` y `extras`.
- **Por qué:** el CSV no contiene las curvas, pero las gráficas de convergencia, SA y GA las necesitan; ambas salidas son registros, no números a mano.
- **Consecuencia:** `summarize` acepta tanto objetos como filas del CSV y da el mismo resultado (hay una prueba).

### E-06 · Paralelismo opcional, apagado por omisión
- **Decisión:** `ProcessPoolExecutor` con `pool.map` (orden determinista), pero `workers=1` por omisión.
- **Por qué:** con varios procesos el tiempo medido se infla. Los solvers inyectados no se pueden serializar, por eso con `workers>1` se rechazan.
- **Consecuencia:** la corrida final de tiempos debe ir en serie.

### E-07 · Curvas de convergencia como función escalonada, con tramo conservado diferenciado
- **Decisión:** cada traza se evalúa con `searchsorted` en una rejilla común (valor vigente, sin interpolar); el trazo es discontinuo cuando menos de la mitad de las semillas sigue ejecutando.
- **Alternativas:** interpolación lineal; extender sin marcar.
- **Por qué:** §11.1 solo permite extender una curva constante si se identifica como conservación.

### E-08 · Memoria de los métodos locales no medida
- **Decisión:** si el solver no reporta memoria (`peak_memory == 0`), las tablas muestran "no medida" y no `0 B`.
- **Por qué:** `tracemalloc` ralentiza mucho y distorsionaría el tiempo de HC/SA/GA; el interés de la memoria está en A* vs RBFS. Escribir `0 B` sería presentar como medición algo que no se midió.

### ERROR CORREGIDO · La prueba de invarianza del origen no detectaba nada
- **Qué pasó:** escribí un solver falso que cambiaba el costo al usar otro origen para comprobar que `run_scale_a` lanza `AuditError`; la prueba falló con "DID NOT RAISE".
- **Diagnóstico:** el falso solo intercambiaba dos ciudades vecinas y en `gr17[k=6]` hay 8 rutas óptimas empatadas: la ruta "dañada" seguía costando lo mismo, así que la prueba comprobaba algo que no ocurría.
- **Corrección:** el falso intercambia pares de ciudades hasta que el costo realmente cambia.
- **Lección:** una prueba que debe fallar tiene que verificar primero que la entrada es de verdad mala; con empates, "cambiar la ruta" no es "cambiar el costo".

### ERROR CORREGIDO · Comparar trazas con sus tiempos
- **Qué pasó:** la prueba de reproducibilidad de SA falló aunque costo y ruta coincidían.
- **Diagnóstico:** la traza incluye segundos reales (y el desplazamiento por el tiempo de calibración), que nunca son idénticos entre corridas.
- **Corrección:** la prueba compara (evaluaciones, costo) y no los segundos.
- **Lección:** la reproducibilidad se exige en lo determinista (semilla, rutas, costos, evaluaciones); el tiempo es una medición y varía.


---

## Etapas 11 y 12 — Validación, calibración y congelación (coordinación)

### D-11 · `steps` de SA se deriva del presupuesto
- **Decisión:** `sa_steps = "auto"`: propuestas por temperatura = presupuesto // niveles, con niveles = ⌈ln(tmin_ratio)/ln α⌉.
- **Por qué:** B observó que con `steps` fijo y α cercano a 1 SA agotaba el presupuesto sin enfriar (957 en eil51, óptimo 426). Con un calendario que no cabe en el presupuesto, comparar valores de α mide el calendario, no el recocido.
- **Consecuencia:** las seis combinaciones (α, p0) terminan por enfriamiento y la calibración es justa.

### D-12 · Calibración en datos distintos y congelación verificable
- **Decisión:** gr17, burma14 y eil51 con semillas 100–104; criterio: promedio de los gaps medianos por instancia. SA → α = 0,97, p0 = 0,8 (empata con α = 0,995; desempate declarado: menor α). GA → población 40, 2 élites, pm = 0,3.
- **Por qué:** no ajustar los parámetros con los datos con que se juzga. La celda de calibración del cuaderno se puede volver a ejecutar y *falla* si su elección difiere de los valores congelados en `FROZEN`.
- **Efecto colateral corregido:** la prueba `test_assert_frozen_y_entorno` suponía parámetros provisionales y dejó de ser válida al congelar; se reescribió para comprobar las dos cosas (el `FROZEN` real pasa; una copia sin calibrar se rechaza).

### D-13 · ERROR CORREGIDO — mi primer contraejemplo de la clave de estado no encontraba nada
- **Qué se hizo primero:** en `tsp/validacion.py` escribí una variante de A\* con un conjunto *cerrado* de ciudades y busqué por sorteo una matriz de 7 ciudades donde diera una ruta más cara que el óptimo.
- **Qué falló:** 400 matrices aleatorias sin un solo contraejemplo, y la fila «Dos conjuntos pendientes distintos» de la batería quedó en ✘.
- **Diagnóstico:** el agente A ya había documentado el mismo hecho (A-11): con la clave «solo ciudad» el algoritmo en la práctica o acierta o *no encuentra ninguna ruta*; casi nunca devuelve una ruta más cara. Mi variante (cerrado por ciudad) no es la que expresa la actividad de §5. La actividad pide dos rutas parciales concretas con la misma última ciudad y pendientes distintos.
- **Corrección:** se adoptaron los dos contraejemplos deterministas de A (X = 0,1,3 con g = 2 e Y = 0,1,2,3 con g = 3; totales 14 y 5) y una variante de A\* con `bestG` por `(última, cerrado)`. Resultado: sin ruta en ambas matrices; la clave completa da el óptimo (5 y 27).
- **Lección:** no debilité la prueba para que pasara. Un contraejemplo no se busca a ciegas: se construye a partir de la propiedad que se quiere refutar. Además, «el error pierde el óptimo» puede manifestarse como «el algoritmo no devuelve nada».

### D-14 · Sobrecosto de `tracemalloc`, medido y declarado
- A midió que `tracemalloc` multiplica el tiempo de A\*/RBFS por ≈ 5–9 (medido en tres casos) y que la memoria varía ±30 % entre corridas. En lugar de ocultarlo, se agregó una celda que mide el factor en tres casos reales y se declara en la discusión.
- **Consecuencia:** los tiempos de A\* y RBFS son comparables *entre sí* (ambos medidos igual), pero no con los de HC/SA/GA, que no usan `tracemalloc` (memoria «no medida» en esos tres).

### D-15 · Ayuda externa
- El código, las pruebas y los apuntes se desarrollaron con ayuda de un asistente de IA (Claude, mediante Claude Code) que coordinó agentes en paralelo por módulo. Debe declararse en la sección A del cuaderno (exigido por la sección 2 del enunciado). Cada integrante debe poder explicar y modificar cualquier fragmento durante la sustentación: de ahí las guías de estudio por etapa.

### D-16 · HALLAZGO — HC con reinicios es idéntico a HC en la escala B, y se midió por qué
- **Qué se vio:** en las cuatro instancias completas, `HC` y `HC-restarts` dan exactamente los mismos números.
- **Diagnóstico:** con mejor mejora, un barrido 2-opt cuesta ≈ 1000–1600 evaluaciones. Midiendo sin tope práctico, HC necesita 48060 (att48), 61789 (berlin52), 92510 (brazil58) y 45360 (gr48) evaluaciones para su *primer* óptimo local, y en 0 de 40 ejecuciones lo alcanza con 30000. Nunca reinicia.
- **Consecuencia:** el gap de HC (20–76 %) es el de una ruta a medio ascender, no el del método terminado (los óptimos locales completos tienen gap mediano de 3,2–5,4 %). En burma14 y gr17, donde el ascenso cabe, los reinicios suben los óptimos de 5 a 10 de 10 y de 1 a 8 de 10. Quedó como suplemento aparte (§14.E), no mezclado con las tablas principales.
- **Lección:** «con reinicios» no mejora a HC por sí mismo: es una manera de usar presupuesto sobrante.

### D-17 · Comparación a tiempo igual (2 s) y su efecto en el ranking
- **Decisión:** además de la comparación por 30000 evaluaciones (la aproximación que propone el enunciado), se comparó con 2 s de reloj por ejecución, con SA dimensionado por una corrida piloto (semilla 99, fuera de la evaluación) y HC con reinicios y GA limitados por reloj.
- **Resultado:** el ranking cambia: de SA < GA ≪ HC a HC con reinicios ≈ SA ≪ GA. HC procesa ≈ 3,4 millones de evaluaciones en 2 s y GA ≈ 55 mil, unas 60 veces menos.
- **Por qué:** una evaluación de HC/SA es un delta de 4 pesos (O(1)); una de GA es un costo completo (O(n)) más operadores. «Igual número de evaluaciones» no es «igual esfuerzo» (§14.1).
- **Límite declarado:** los tiempos dependen de Python y de este equipo; solo el orden de magnitud es robusto.

### D-18 · ERROR CORREGIDO — la celda de auditoría de datos usaba funciones definidas más abajo
- **Qué falló:** la primera ejecución completa del cuaderno de arriba abajo se detuvo en la celda de auditoría de §3 con `NameError: is_valid_tour`. Esa celda usa `tour_cost` e `is_valid_tour`, que se definen en el módulo de §4.
- **Por qué no lo vieron las pruebas:** las pruebas de `tests/` importan el paquete completo; solo la ejecución en un kernel nuevo, en el orden del cuaderno, expone las dependencias implícitas (justo lo que exige el enunciado).
- **Corrección:** la celda se movió a continuación del módulo `modelo` y se hizo una revisión estática de nombres indefinidos en todo el cuaderno concatenado (`pyflakes`): ninguno más.
- **Lección:** «funciona en las pruebas» no implica «funciona en el cuaderno».

### D-19 · Herramienta de fusión de salidas
- `tools/fusionar_salidas.py` toma las celdas Markdown del cuaderno recién construido y las celdas de código con sus salidas de una ejecución completa (~25 min), y **exige** que el código de cada celda sea idéntico en ambos. Se usó porque tras ejecutar solo se corrigieron textos (por ejemplo el factor de sobrecosto de `tracemalloc`, medido ×5,3–×8,7 en la ejecución final). Si algún código cambiara, la herramienta se niega y hay que volver a ejecutar.
