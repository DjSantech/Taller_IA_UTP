# Bitácora I: actividades de integración (sección 7, apartados A, B y D)

Formato: **Decisión · Alternativas · Por qué · Consecuencia**. Los errores reales llevan la marca
**ERROR CORREGIDO** (*Qué pasó / Diagnóstico / Corrección / Lección*). Código:
`chess_ai/rook_problem.py`, `chess_ai/uncertainty.py`. Pruebas: `tests/test_integracion.py`.

---

## Apartado A: torre y búsqueda no informada

### I-01 · La torre se programa desde cero, con reglas simplificadas explícitas
- **Decisión:** el estado es la casilla de la torre como tupla `(columna, fila)` en 0..7
  (a1 = (0,0), h8 = (7,7)). Las acciones son `(dirección, k)`: avanzar k ≥ 1 casillas al N, E, S
  u O sin salir del tablero. Admitimos obstáculos fijos opcionales, que la torre no puede ocupar
  ni saltar. No usamos python-chess.
- **Alternativas:** usar `chess.Board` con una torre y los dos reyes; representar la casilla
  como entero 0..63.
- **Por qué:** el enunciado pide «reglas simplificadas explícitas, no posiciones legales
  completas». Un `chess.Board` exige reyes, turnos y jaques que no forman parte del problema y
  esconden el modelo de transición. La tupla de enteros es inmutable y hashable, y hace que el
  orden de iteración sea reproducible (Taller 1, D-08).
- **Consecuencia:** `RookProblem.is_valid_path` verifica cada paso de forma independiente de
  los buscadores (misma línea recta, sin salirse, sin atravesar obstáculos).

### I-02 · Orden fijo de acciones: N, E, S, O y k creciente
- **Decisión:** las acciones se generan en el orden N, E, S, O (el mismo del Taller 1, D-14) y,
  dentro de cada dirección, con k creciente. `long_moves_first=True` invierte el orden de k.
- **Alternativas:** k decreciente por omisión (DFS hallaría a1→a8→h8 de inmediato).
- **Por qué:** el orden no cambia el costo óptimo de BFS, UCS ni A*, pero sí la ruta de DFS y los
  desempates. Dejamos el orden «natural» como base y medimos cuánto cambia DFS con otros órdenes.
- **Consecuencia (medido):** con N,E,S,O y k creciente DFS devuelve una escalera de 14
  movimientos (a1→a2→b2→…→g8→h8). Con k decreciente devuelve a1→a8→h8 (2 movimientos, 2
  expandidos). Con E,N,O,S devuelve otra escalera de 14 movimientos. El óptimo (2) no cambia
  (`test_dfs_route_depends_on_action_order`).

### I-03 · Mismas convenciones de métricas que el Taller 1
- **Decisión:** la prueba de objetivo se hace al **extraer**. BFS y DFS marcan al **generar**.
  «Expandido» significa que se generaron sus sucesores, así que el objetivo extraído no cuenta.
  «Generado» es todo sucesor construido, incluidos los repetidos descartados; la raíz no cuenta.
  La frontera máxima incluye las entradas obsoletas del montículo.
- **Alternativas:** probar el objetivo al generar en BFS (ahorra un nivel).
- **Por qué:** son las convenciones de D-19/D-20 del Taller 1. Así las cifras se pueden comparar
  con las de aquel taller y entre los cinco algoritmos.
- **Consecuencia:** BFS expande 63 de 64 casillas en a1→h8, aunque la meta esté a profundidad 2.
  Todas las casillas están a lo sumo a 2 movimientos y h8 sale de la cola de última.

### I-04 · Un solo núcleo primero-el-mejor para UCS, A* y voraz
- **Decisión:** `_rook_best_first` implementa BEST-FIRST-SEARCH con `best_g` y eliminación
  perezosa. Las prioridades son: UCS `(g, orden)`, A* `(g+h, h, orden)` y voraz `(h, orden)`.
- **Alternativas:** tres funciones separadas.
- **Por qué:** igual que la frontera inyectada del Taller 1 (D-17), la diferencia entre los tres
  algoritmos queda en una sola línea, la prioridad, y el resto (repetidos, métricas) es común. El
  desempate `(f, h, orden)` es el de A-04 del Taller 2.
- **Consecuencia:** con costo unitario y desempate FIFO, UCS expande exactamente en el mismo
  orden que BFS en los tres escenarios. Es la predicción D-22 del Taller 1, comprobada de nuevo
  (`test_ucs_unit_reproduces_bfs_expansion_order`).

### I-05 · Escenario con obstáculos donde longitud ≠ costo, hallado por muestreo
- **Decisión:** el tercer escenario usa 9 obstáculos (a2, b4, c2, d3, d8, e3, f3, g2, h5),
  fijados como `ROOK_OBSTACLES_LENGTH_VS_COST`.
- **Alternativas:** diseñar los obstáculos a mano; dejar solo el tablero vacío.
- **Por qué:** en el tablero vacío la ruta de menos movimientos (a1→a8→h8) también recorre el
  mínimo de casillas (14), así que no separa longitud de costo. Nuestro primer escenario hecho
  a mano (un muro en b7–h7 y g1–g6) tampoco lo separaba: seguía existiendo a1→a8→h8, con 2
  movimientos y 14 casillas. Entonces muestreamos obstáculos al azar (`random.Random(7)`, de 4 a 14 obstáculos) y
  nos quedamos con el caso de menos obstáculos. Otro muestreo de 60 000 tableros con solo 3 a 8
  obstáculos (`random.Random(2026)`) no encontró ninguno.
- **Consecuencia:** UCS con costo unitario da a1→h1→h3→g3→g8→h8 (5 movimientos, 16 casillas).
  UCS con costo por distancia da a1→b1→b3→c3→c4→e4→e8→h8 (7 movimientos, 14 casillas). Las
  pruebas verifican la propiedad, no el muestreo. Es el mismo criterio fuerte de D-39 del
  Taller 1: la ruta más barata debe tener **estrictamente** más movimientos.

### I-06 · HALLAZGO: con costo por distancia, UCS expande más que BFS
- En d4→h8, BFS expande 39 nodos y UCS con costo por distancia expande 63. El costo óptimo es 8 y
  casi todas las casillas del tablero están a distancia (Manhattan) ≤ 8 de d4. UCS tiene que
  sacar de la cola todas las de costo < 8 y, por los empates, muchas de costo 8 antes que h8. Más
  costo no implica más trabajo para BFS, porque BFS solo mira los movimientos.

---

## Apartado B: búsqueda informada

### I-07 · Admisibilidad verificada exhaustivamente con un oráculo independiente
- **Decisión:** `rook_true_costs` calcula h*(s) con Dijkstra hacia atrás desde el destino, para
  todas las casillas. `rook_check_heuristic` compara h ≤ h* y h(s) ≤ c(s,a,s') + h(s') en cada
  transición.
- **Alternativas:** confiar en la demostración; comparar con el A* que se está evaluando.
- **Por qué:** es D-07 del Taller 1: no se valida con el mismo código que se quiere validar. Se
  puede usar el grafo inverso porque un movimiento de torre recorre las mismas casillas en los
  dos sentidos.
- **Consecuencia (medido):** h de la consigna con costo unitario: 0 violaciones de admisibilidad
  y 0 de consistencia, tanto en tablero vacío (64 estados) como con obstáculos (55). Manhattan
  con costo por distancia: también 0 y 0. Manhattan con costo unitario: 60 de 64 casillas
  sobreestimadas (hasta 12 de exceso: h(a1)=14 frente a h*=2) y 336 transiciones inconsistentes.

### I-08 · Contraejemplo: Manhattan con costo unitario hace que A* no sea óptimo
- **Decisión:** `rook_unit_manhattan_counterexample` recorre en orden fijo muros horizontales con
  un hueco y devuelve el primero donde A*(Manhattan) da más movimientos que BFS.
- **Resultado:** muro en la fila 3 con hueco en b3. BFS da a1→b1→b8→h8 (3 movimientos);
  A*(Manhattan) da a1→a2→b2→b8→h8 (4 movimientos). A* con la h de la consigna da 3. Mostrar que
  h(a1)=14 > h*(a1)=2 no basta: hace falta ver que la sobreestimación cambia la respuesta.
  Esto también lo aprendimos en el Taller 1, D-39.

### I-09 · Voraz: rápido, pero no óptimo en costo
- En el escenario con obstáculos y costo por distancia, el voraz con Manhattan expande 6 nodos y
  devuelve una ruta de 16 casillas, mientras que el óptimo es 14
  (`test_greedy_is_not_optimal_in_distance_cost_with_obstacles`). En el tablero vacío coincide
  con A*, porque la heurística ya lleva directo a la meta.

---

## Apartado D: incertidumbre

### I-10 · El plan AND-OR es un diccionario anidado `{jugada: {respuesta: subplan}}`
- **Decisión:** un nodo OR del plan tiene exactamente una jugada del atacante. Su valor es un nodo
  AND con **todas** las respuestas legales del defensor. Una hoja de mate es `{jugada: {}}`.
- **Alternativas:** la lista con `if-then-else` de AIMA; clases propias.
- **Por qué:** se puede imprimir y verificar con un recorrido simple, y la condición «cubre todas
  las defensas» queda como `set(sub) == set(board.legal_moves)`.
- **Consecuencia:** `verify_mate_plan` recorre el plan con las reglas de python-chess, sin usar el
  buscador, y rechaza las secuencias lineales («defensas sin cubrir: a5a4, h6h5») y los planes
  que repiten la misma jugada contra todas las defensas.

### I-11 · Un nodo AND sin respuestas NO es éxito si no hay mate (desviación de AIMA)
- **Decisión:** el éxito solo se declara cuando la jugada del atacante da **jaque mate**. Si el
  defensor queda sin jugadas y no está en jaque (ahogado), o si se llega a tablas, es fracaso
  (`failures_by_draw`).
- **Alternativas:** el AND-SEARCH literal de AIMA, que con un conjunto vacío de estados devuelve
  el plan vacío, es decir, éxito.
- **Por qué:** aplicado sin más, AIMA contaría el ahogado como un «objetivo». En
  `7k/8/8/6K1/8/8/8/5Q2 w` la jugada 1.Qf7 ahoga. Nuestra búsqueda la registra como fracaso y
  no devuelve ningún plan de 1 jugada (`test_stalemate_is_not_success`).

### I-12 · Jaques y capturas primero en los nodos OR
- **Decisión:** las jugadas del atacante se ordenan con los jaques primero, luego las capturas y
  luego el UCI.
- **Por qué:** el orden no cambia si existe un plan, solo cuánto se explora hasta hallarlo. Es la
  misma idea que ordenar jugadas en alfa-beta (apartado B). Sirve de puente entre los dos
  apartados.

### I-13 · ERROR CORREGIDO: la búsqueda devolvía un plan, pero no el más corto
- **Qué pasó:** la primera versión probaba las jugadas OR con el límite completo
  `max_attacker_moves` y devolvía el primer plan que funcionaba. En el mate en 1 del enunciado
  con límite 2, los contadores mostraban que primero exploraba 1.Qe8+ (2 nodos OR, 1 AND) y solo
  después encontraba Qg7#.
- **Diagnóstico:** el orden «jaques primero» pone 1.Qe8+ (UCI `g6e8`) antes que 1.Qg7#
  (`g6g7`). Si 1.Qe8+ también fuerza mate dentro del límite, la búsqueda devuelve ese plan más
  largo. Lo comprobamos: con límite 3 y sin profundización devuelve 1.Qe8+ Kh7 2.Qd7+ (3
  defensas) 3.Qg7#/Qh3#, un plan de 3 jugadas, en una posición que tiene mate en 1.
- **Corrección:** `shortest=True` (por omisión) profundiza con n = 1, 2, …, máx. Es la
  profundización iterativa del Taller 1, y el primer plan que encuentra es el mate forzado más
  corto. `test_shortest_plan_is_preferred` fija los dos comportamientos.
- **Lección:** «encuentra un plan» y «encuentra el mejor plan» son garantías distintas. Un plan
  correcto pero largo puede pasar desapercibido si solo verificamos que sea correcto.

### I-14 · ERROR CORREGIDO: la primera posición de «mate del pasillo» no era mate en 2
- **Qué pasó:** escribimos `2r3k1/5ppp/8/8/8/8/5PPP/3RR1K1 w` (torres en d1 y e1) creyendo que
  1.Re8+ Rxe8 2.Rxe8# era mate en 2. `and_or_mate_search(…, 2)` devolvió fracaso (29 nodos OR,
  26 AND).
- **Diagnóstico:** tras 1.Re8+ Rxe8, la torre que queda está en d1 y no llega a e8. Para
  recapturar en la misma columna, las torres tienen que estar dobladas.
- **Corrección:** `2r3k1/5ppp/8/8/8/8/3R1PPP/3R2K1 w` (torres en d1 y d2): 1.Rd8+ Rxd8 2.Rxd8#.
  La búsqueda lo confirma y también confirma que no hay mate en 1.
- **Lección:** una posición «conocida» copiada de memoria también hay que verificarla. Aquí fue
  el propio buscador AND-OR el que detectó el error de la posición.

### I-15 · Mate en 2 con jugada tranquila y respuestas distintas por defensa
- **Decisión:** además del pasillo (1 sola defensa), usamos `8/4K3/7k/p7/8/8/6Q1/8 w`: 1.Kf6 y
  luego Kh5 Qg5#, Kh7 Qg7#, a4 Qg6#.
- **Por qué:** el pasillo no muestra la ramificación AND. Buscamos posiciones K+D contra R+P con
  un generador aleatorio de posiciones (no fijamos la semilla en un archivo, así que la búsqueda
  no es reproducible). Elegimos esta porque cada defensa exige un mate distinto. La posición está
  fija en el código y se verifica en las pruebas: el plan cubre las 3 defensas, termina en mate
  en cada hoja y no existe mate en 1.

### I-16 · Minimax sobre el árbol con azar = el azar como adversario
- **Decisión:** `worst_case_minimax` trata los nodos de azar como nodos MIN (peor caso).
  `expectiminimax` calcula la esperanza.
- **Alternativas:** minimax que asume el resultado más probable; eliminar los nodos de azar.
- **Por qué:** es lo que haría nuestro agente minimax si nadie le dijera que el azar no es un
  rival. Así queda claro el contraste entre una garantía (peor caso) y el promedio.
- **Consecuencia:** en el árbol «segura/arriesgada», expectiminimax elige la arriesgada (3.5
  contra 2.75) y minimax la segura (2 contra −4).

### I-17 · Transformación monótona no lineal u → 4^u
- **Decisión:** en el árbol de escala aplicamos u → 4^u. Es creciente, así que conserva el orden
  de las hojas (lo verifica la prueba).
- **Consecuencia:** expectiminimax cambia de a1 (2.1 contra 1.3) a a2 (20.8 contra 29.2), y
  minimax sigue en a1 (2 contra 1; 16 contra 4). Es AIMA 5.5: con azar, las utilidades tienen
  que ser una **escala** con significado (utilidad esperada), no solo un orden.

### I-18 · Estado de creencia de Kriegspiel como conjunto de tableros
- **Decisión:** el estado de creencia es un diccionario `{epd: tablero}`. El árbitro anuncia
  `(casilla de captura o None, da jaque)` de cada jugada rival. Nuestros intentos de jugada parten
  el estado de creencia en «legal» e «ilegal».
- **Simplificación declarada:** el árbitro real también anuncia la dirección del jaque y los
  intentos ilegales del rival. No los modelamos.
- **Consecuencia (medido, desde la posición inicial):** 1 mundo → tras 1.e4 y una respuesta no
  observada, 20 → tras 2.Nf3 y otra respuesta no observada, 266. Si blancas intentan e4–e5 después
  de 1.e4, el árbitro dice «ilegal» en 1 mundo (…e5) y «legal» en 19.
