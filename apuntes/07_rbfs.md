### D.2. RBFS: límites, valores respaldados y medición

**Qué hice.** En `tsp/rbfs.py` implementé el RBFS de la sección 8 sobre **el mismo modelo y la misma cota** de `astar.py` (`SearchNode`, `successors`, `make_heuristic`, `route_of`), de modo que la comparación mide la estrategia de búsqueda y no una cota distinta. La firma es `rbfs(inst, origin=0, budget=None, heuristic="mst", audit=True) -> RunResult`. Usé `child.f = max(g+h, node.f)`, ordenación estable por `(f, h)` y propagación de `INTERRUPTED` desde cualquier nivel de la recursión. Es la versión de árbol: no hay conjunto de visitados, porque cada extensión quita un pendiente y el último paso cierra el ciclo.

**Instrumentación (8.1).** Cuento expansiones (llamadas a `successors` sobre un nodo no cerrado), llamadas, generados, cálculos de MST, profundidad máxima (la raíz es 0 y el cierre queda en profundidad $n$) y nodos retenidos simultáneamente (la raíz más las listas de hijos de los marcos de la pila; guardo el máximo).

**Qué cuento como regeneración.** Expandir un nodo que ya se había expandido, identificado por su *camino* desde la raíz (no por su estado: dos caminos al mismo estado son ramas distintas del árbol). Para reconocerlo uso un registro de auditoría: un conjunto de hashes de 64 bits de los caminos expandidos. Ese registro **consume memoria que no pertenece al algoritmo** (unos 70 bytes por camino distinto) y por eso lo declaro y lo puedo apagar con `audit=False`. Sin auditoría solo cuento como regeneración volver a expandir el mismo registro que sigue vivo en la lista de hijos de su padre, una cota inferior muy floja: en brazil58 con 8 ciudades da 826 frente a 56 374 exactas, y la memoria pico baja de 76 532 B a 10 736 B. Por eso lo declaro: en todas las tablas de este cuaderno (escalas A y B) las regeneraciones y la memoria de RBFS se miden con `audit=True`, es decir, **la memoria de RBFS incluye el registro de auditoría**; sin él sería menor todavía (en ese ejemplo, 10 736 B).

<!-- celda -->

**Traza con retroceso** (4 ciudades: $AB=4,AC=2,AD=5,BC=5,BD=7,CD=1$; óptimo 14). Columnas: profundidad, ciudad, $f$ al entrar, límite recibido.

| llamada | $f$ | límite | qué ocurre |
|---|---|---|---|
| 0 A | 10 | ∞ | hijos B 12, D 13, C 14: baja por B, alternativa D=13 |
| 1 B | 12 | 13 | sus hijos valen 15 y 14, ambos > 13: FAILURE, respaldado 14 |
| 1 D | 13 | 14 | A reordena (D 13, B 14, C 14); D tiene hijos 19 y 15: FAILURE, respaldado 15 |
| 1 B | 14 | 14 | B vuelve a ser el mejor (h menor): **se expande otra vez**, sus hijos se habían descartado |
| 2 D, 3 C, 4 A | 14 | 14 | baja hasta el cierre: FOUND, costo 14 |

7 llamadas, 6 expansiones, 11 generados, 1 regeneración (la de B), 8 nodos retenidos como máximo. A\* resuelve este caso con 5 expansiones.

**Por qué el máximo.** Cuando se regeneran los hijos de un nodo ya respaldado, su $g+h$ se recalcula desde cero y puede ser menor que lo que se aprendió de ese subárbol; el máximo les transmite el valor respaldado del padre ("todo lo que cuelga de aquí cuesta al menos esto"). Con mi cota, que es consistente, $g+h$ no baja al avanzar, así que el máximo solo actúa tras un retroceso. Lo medí: en att48 con 8 ciudades elevó el $f$ de 235 de los 1 493 hijos generados; en el microcaso y en gr48 con 6 ciudades, sin regeneraciones, elevó 0. (Al principio creí que el máximo sería neutro con una cota consistente; me equivoqué y lo corregí: ver bitácora A-09.)

<!-- celda -->

**Memoria contra recomputación** (subinstancias, límites por defecto; una ejecución, memoria con tracemalloc, por lo que varía entre corridas):

| Instancia | k | A\* exp. | RBFS exp. | Regen. exactas | Memoria A\* | Memoria RBFS (audit) | Tiempo RBFS |
|---|---|---|---|---|---|---|---|
| att48 | 10 | 170 | 2 793 | 2 527 | 185–216 KB | 34 KB | 0.5 s |
| att48 | 12 | 376 | 31 961 | 31 164 | 487–628 KB | 82 KB | 9.8 s |
| berlin52 | 10 | 63 | 706 | 569 | 67 KB | 28 KB | 0.17 s |
| berlin52 | 12 | 437 | 78 640 | 76 920 | 549 KB | 224 KB | 28.1 s |
| brazil58 | 8 | 225 | 57 313 | 56 374 | 85–118 KB | 76 KB (11 KB sin audit) | 4.2 s |
| brazil58 | 10 | 953 | **100 000** (límite) | 98 835 | 423 KB | 91 KB | 13.5 s, interrumpido |
| brazil58 | 12 | 4 478 | 86 954 en 30 s (límite) | 85 921 | 2.4 MB | 89 KB | interrumpido |
| gr48 | 12 | 38 | 79 | 41 | 63 KB | 28 KB | 0.05 s |

Respuesta a la pregunta 5 de la discusión: RBFS redujo memoria y aumentó la recomputación en att48 y berlin52 (con 12 ciudades usa unas 7 veces menos memoria que A\* en att48, pero hace 85 veces más expansiones y tarda más de 100 veces más). No es una ley: en gr48, donde la cota es muy buena, casi no retrocede y RBFS casi iguala a A\*; y en brazil58 con 8 ciudades casi no ahorra memoria con la auditoría y tarda 4 s contra 0.02 s. En brazil58 con 10 y 12 ciudades RBFS no termina dentro de los límites propuestos mientras A\* termina en 0.1 y 0.5 s: esos casos se informan como **interrumpidos**, sin ruta y sin certificado, no como fracaso.

<!-- celda -->

**Instancias completas** (10 s): las cuatro terminan por `TIME_LIMIT` sin ruta. RBFS: att48 487 expansiones (retiene 349 registros como máximo, profundidad máxima 7), berlin52 494, brazil58 394, gr48 849; memoria pico entre 70 y 100 KB frente a 7 a 14 MB de A\* en los mismos 10 s. El valor respaldado de la raíz en ese momento no se usa como certificado de brecha, como pide el enunciado.

**Costo de medir.** `tracemalloc` multiplica el tiempo por ≈ 5 a 9 (att48, k=10: 0.13 s sin medir, 0.74 s midiendo); `measure_memory=False` permite tomar tiempos puros. El límite de memoria se revisa cada 256 expansiones.

**Qué prueba lo respalda:** `test_rbfs_un_solo_hijo_n2`, `test_rbfs_empate_se_resuelve_por_h_y_luego_por_orden_de_generacion`, `test_rbfs_limite_menor_que_la_mejor_f_devuelve_fracaso_con_f_respaldada`, `test_rbfs_agotamiento_de_subarbol_respalda_el_valor_correcto`, `test_rbfs_retrocede_y_regenera_subarboles_en_un_caso_real`, `test_rbfs_el_maximo_transmite_el_valor_respaldado`, `test_interrupcion_por_expansiones/tiempo/memoria`, y la igualdad de costo con la enumeración (24 matrices y 14 subinstancias). Guía: `estudio/Etapa7_teoria.txt`.
