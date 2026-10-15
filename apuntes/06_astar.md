### D.1. A\* con MST: modelo, clave de estado y resultados

**Qué hice.** En `tsp/astar.py` implementé el modelo de la sección 5 (`SearchNode` con `last`, `remaining`, `g`, `parent`, `closed`; `successors`) y el A\* de la sección 7 con `bestG`, entradas obsoletas y meta = nodo cerrado. La firma es `astar(inst, origin=0, budget=None, heuristic="mst", upper_bound=None) -> RunResult`.

**Decisiones.**

- *Pendientes como máscara de bits.* La clave de estado es `(last, remaining, closed)` con `remaining` entero. Es inmutable, hashable, quitar una ciudad es $O(1)$ y pesa mucho menos que un `frozenset`, lo que importa porque mido memoria con `tracemalloc`.
- *Desempate:* la cola ordena por `(f, h, contador)`: menor $f$; a igual $f$ menor $h$ (nodo más avanzado, cerrados primero); a igual, el generado antes. Es determinista y el costo final no depende de él.
- *Meta al sacar, no al generar,* y nodos con $g>\texttt{bestG}$ se ignoran al sacarlos (entradas obsoletas).
- *Presupuesto:* tiempo y expansiones se revisan en cada iteración; la memoria incremental, cada 256 expansiones (frecuencia declarada). Si el presupuesto vence, el resultado es sin ruta, `NO_ROUTE` y el motivo del presupuesto; nunca se llama óptimo ni fracaso definitivo.
- *Cota superior opcional:* con `upper_bound` poda los hijos con $g+h>$ cota. Si saca un cerrado de costo $c\le$ cota, $c$ es óptimo (todo lo podado costaría más que la cota); si agota la frontera, no existe ruta de costo $\le$ cota y lo informo como `EXHAUSTED` sin afirmar optimalidad.

<!-- celda -->

**Por qué no basta la última ciudad.** Con la matriz de 5 ciudades de mi prueba (origen $A$; $A\!B=1,\,AC=10,\,AD=10,\,AE=1,\,BC=1,\,BD=1,\,BE=10,\,CD=1,\,CE=10,\,DE=1$) hay dos rutas parciales que terminan en $D$:

- $X=A\!-\!B\!-\!D$, $g=2$, pendientes $\{C,E\}$: la mejor continuación cuesta 12, total **14**.
- $Y=A\!-\!B\!-\!C\!-\!D$, $g=3$, pendientes $\{E\}$: la mejor continuación cuesta 2, total **5**, que es el óptimo.

Fusionar por ciudad conserva $X$ (menor $g$) y descarta $Y$, que es la única que llega al óptimo. La clave correcta no las fusiona (`{C,E}` ≠ `{E}`). Dentro del test escribí una variante de A\* idéntica salvo por la clave `(última ciudad, closed)`: sobre esta matriz y sobre otra aleatoria de 5 ciudades **no halla ninguna ruta** (la frontera se vacía), mientras el A\* correcto devuelve 5 y 27. Debo decir lo que no pude reproducir: en miles de matrices de 5 a 7 ciudades la variante nunca devolvió una ruta *más cara*; o acertaba o se quedaba sin ruta. El daño de esa clave es perder rutas y con ellas la garantía.

Pregunta 4 de la discusión (devolver el primer nodo sin pendientes): en esa misma matriz el recorrido sin el regreso suma menos que el costo real, y una prueba lo comprueba.

<!-- celda -->

**Resultados reales** (una ejecución por caso, límites por defecto; el tiempo incluye la sobrecarga de `tracemalloc`):

| Instancia | k | Costo óptimo | A\*+MST exp. | A\*(h=0) exp. | A\*+MST memoria pico | Tiempo A\*+MST |
|---|---|---|---|---|---|---|
| att48 | 10 | 6178 | 170 | 2305 | 216 KB | 0.03 s |
| att48 | 12 | 6209 | 376 | 11264 | 487 KB | 0.08 s |
| berlin52 | 10 | 2826 | 63 | 2305 | 67 KB | 0.01 s |
| berlin52 | 12 | 4056 | 437 | 11265 | 549 KB | 0.13 s |
| brazil58 | 10 | 17652 | 953 | 2305 | 423 KB | 0.10 s |
| brazil58 | 12 | 18372 | 4478 | 11265 | 2.4 MB | 0.55 s |
| gr48 | 12 | 2446 | 38 | 11229 | 63 KB | 0.01 s |

A\* con $h=0$ y con MST dan siempre el mismo costo (`test_h0_y_mst_dan_el_mismo_costo_pero_mst_expande_menos`), pero la cota MST expande entre 2.5 veces (brazil58, la matriz más irregular) y unas 300 veces (gr48) menos. Con $k=6$ y $8$ el costo coincide con la enumeración exhaustiva en las 7 instancias; con 24 matrices aleatorias simétricas de 4 a 8 ciudades (algunas con pesos 0..4, muchos empates) también, y cambiar el origen no altera el costo óptimo.

<!-- celda -->

**Instancias completas** (diagnóstico, 10 s, 100000 expansiones, 256 MiB): ninguna termina; las cuatro paran por `TIME_LIMIT`, sin ruta y sin certificado.

| Instancia | Expansiones | Generados | Frontera máx. | Memoria pico |
|---|---|---|---|---|
| att48 | 765 | 31 758 | 26 594 | 11.8 MB |
| berlin52 | 674 | 31 752 | 26 247 | 11.4 MB |
| brazil58 | 488 | 25 979 | 18 210 | 7.3 MB |
| gr48 | 1 153 | 47 985 | 34 002 | 14.4 MB |

Cada expansión de una instancia completa genera unos 47 hijos y calcula un MST de 46 ciudades para cada uno, de ahí el costo por expansión (entre 9 y 20 ms según la instancia, con `tracemalloc` activo). Aunque gr48 y att48 tienen 48 ciudades, en las subinstancias de 12 ciudades gr48 necesita 38 expansiones y att48 376: depende de cuán ajustada queda la cota con esos pesos, no del tamaño.

**Qué prueba lo respalda:** `test_astar_y_rbfs_igualan_la_enumeracion_*`, `test_a_star_con_clave_solo_por_ciudad_pierde_el_optimo_y_el_real_no`, `test_dos_rutas_parciales_misma_ciudad_final_no_se_pueden_fusionar`, `test_astar_con_cota_superior_certifica_o_agota`, `test_astar_registra_contadores_y_entradas_obsoletas`, `test_invarianza_del_costo_al_cambiar_el_origen`, `test_interrupcion_por_*`. Guía: `estudio/Etapa6_teoria.txt`.
