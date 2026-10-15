### C.2. MST y heurística: definición, demostración y pruebas

**Qué hice.** Implementé en `tsp/mst.py` el costo del árbol de expansión mínima con Prim en $O(|U|^2)$ (`mst_cost`), una segunda versión que devuelve las aristas para poder validar que es un árbol (`mst_edges`), la heurística de la sección 6 (`heuristic_mst`) y la heurística nula (`heuristic_zero`). Los casos $|U|=0$ y $|U|=1$ devuelven 0, según el enunciado.

**Por qué Prim con "mejor costo de conexión".** El Prim conceptual vuelve a explorar todas las aristas de corte en cada paso y cuesta $O(|U|^3)$. Yo guardo, para cada ciudad pendiente, el peso de su arista más barata hacia lo ya conectado; al añadir una ciudad solo actualizo esa lista. Son $|U|-1$ pasos de $O(|U|)$ cada uno. Con la matriz densa es lo natural. No usé caché de MST: crece de forma exponencial con los conjuntos $U$, contradice la idea de memoria reducida de RBFS y falsearía la comparación de memoria. Cada cálculo de MST se cuenta en `mst_calls`.

<!-- celda -->

**La heurística.**

$$h(v,U)=\begin{cases}0&\text{cerrado}\\ d(v,s)&U=\varnothing\\ \operatorname{MST}(U)+\min_{u\in U}d(v,u)+\min_{u\in U}d(u,s)&\text{otro caso}\end{cases}$$

**Demostración de admisibilidad.** Cualquier continuación desde $v$ es $v\to u_1\to\cdots\to u_k\to s$ con $\{u_1,\ldots,u_k\}=U$. Su costo se parte en tres: (1) $d(v,u_1)\ge\min_u d(v,u)$; (2) $d(u_1,u_2)+\cdots+d(u_{k-1},u_k)$ es un camino que une todos los pendientes, y un camino es un árbol, así que cuesta al menos $\operatorname{MST}(U)$; (3) $d(u_k,s)\ge\min_u d(u,s)$. Sumando, toda continuación cuesta al menos $h(v,U)$, en particular la más barata. No se usa la desigualdad triangular. Con un solo pendiente la cota es exacta.

**Consistencia (lo pedido como tarea).** Resulta ser consistente. Sea $n=(v,U)$ y $n'=(w,U\setminus\{w\})$ con costo $c=d(v,w)$. Si $U\setminus\{w\}\neq\varnothing$ sumo tres desigualdades: (a) $\operatorname{MST}(U)\le\operatorname{MST}(U\setminus w)+\min_{u\in U\setminus w}d(w,u)$, porque al MST de $U\setminus w$ le agrego la arista más barata de $w$ y obtengo un árbol que une $U$; (b) $\min_{u\in U}d(v,u)\le d(v,w)$; (c) $\min_{u\in U}d(u,s)\le\min_{u\in U\setminus w}d(u,s)$, porque el mínimo sobre un conjunto mayor no puede ser mayor. Si $U=\{w\}$, y también en el paso de cierre, se cumple con igualdad. Hallé este resultado después de buscar un contraejemplo sin éxito; la prueba explica por qué no existe.

<!-- celda -->

**Resultados reales (`tests/test_exactos.py`).**

| Comprobación | Resultado |
|---|---|
| MST: 40 matrices aleatorias (2 a 12 nodos, pesos 0..15 con empates) | árbol válido (una arista menos que nodos, sin ciclos, una componente) y peso igual a Kruskal independiente |
| Microcaso: MST({C,D,E}) | 5, aristas de peso 2 y 3 |
| Admisibilidad: 15 casos de 6 a 8 ciudades, **27 789 prefijos** | 0 violaciones; $h$ comparada con `best_completion_cost` (enumeración de las continuaciones de cada prefijo) |
| Con ≤ 1 pendiente | $h$ = costo real en todos |
| Consistencia: 37 998 transiciones de los mismos casos | 0 violaciones |
| Búsqueda previa de contraejemplos: 300 matrices aleatorias + 300 euclidianas (5 a 8 ciudades) | 0 violaciones en 2 394 204 transiciones |

La holgura de la cota en el microcaso es de 0 o 1 en todos los prefijos de longitud 2 y 3 (por ejemplo $A\!-\!D$: $h=11$, costo restante real 12). Por eso A\* con MST expande 5 nodos contra 33 con $h=0$.

**Qué no es.** El MST no es una ruta TSP: no impone grado dos, no cierra ciclo y las dos conexiones pueden elegir la misma ciudad. Esa información perdida es lo que separa la cota del óptimo.

**Qué prueba lo respalda:** `test_mst_fronteras_cero_uno_dos`, `test_mst_microcaso_U_CDE_cuesta_5`, `test_mst_es_arbol_y_coincide_con_kruskal`, `test_heuristica_casos_de_la_formula`, `test_admisibilidad_sobre_todos_los_prefijos`, `test_consistencia_h_n_menor_o_igual_c_mas_h_hijo`. Guía: `estudio/Etapa5_teoria.txt`.
