### Pruebas de corrección: qué verifica la celda anterior y qué fallos corregimos

La celda anterior ejecuta, **dentro del cuaderno**, las siete pruebas que pide el enunciado sobre los seis agentes. Cada afirmación es un `assert`: si una falla, la ejecución del cuaderno se detiene ahí. La tabla final resume casos y resultado.

| # | Prueba del enunciado | Cómo la comprobamos |
|---|---|---|
| 1 | Minimax frente a alfa-beta | 12 posiciones (5 del enunciado y 5 intermedias: captura, jaque, final de torres, final de peones y piezas menores), profundidades 1 y 2 (y 3 en las baratas). Alfa-beta natural y ordenado dan **exactamente** el mismo valor que minimax (`==`, no aproximado). Cuando la jugada difiere, verificamos que ambas alcanzan el mismo valor: es un empate y no un error (pregunta 3). |
| 2 | Decisiones legales | Los seis agentes en 7 posiciones no terminales devuelven una jugada de `legal_moves`. En `checkmate` y `stalemate` todos devuelven `move=None` con la utilidad exacta: −100 000 (derrota de negras) y 0. |
| 3 | Victoria inmediata y evasión | Mate en uno con blancas y con el tablero reflejado (negras al turno). En la evasión propia `k3r3/8/8/7Q/8/8/8/4K3 w` todos salen del jaque y los agentes de búsqueda capturan la torre que lo da. |
| 4 | Tablero e historia intactos | Mismo FEN y misma pila de jugadas tras buscar; tras un `SearchTimeout` a mitad del árbol; con el plazo vencido; y aunque la evaluación lance una excepción (los `pop` están en `finally`). |
| 5 | Reproducibilidad | Misma semilla, misma jugada (aleatorio, voraz). MCTS con simulaciones fijas da las mismas visitas en la raíz. Una partida completa Voraz–MCTS por el controlador se repite jugada a jugada. |
| 6 | Profundización con plazo agotado | Con plazo de 1e-9 s devuelve la jugada de respaldo (legal, `score=None`, `completed_depth=0`). Con 0,1 s devuelve la jugada y el valor de la última iteración completa. |
| 7 | Perspectiva de MCTS | Con negras al turno, el agente correcto acierta y una variante con el error típico (guardar todo desde blancas) falla, con las mismas semillas. Además recorremos el árbol y verificamos que cada nodo «pertenece» al jugador que movió para llegar a él. |

**Posiciones propias (sección 8).** Agregamos cuatro, cada una con su justificación:

| Posición | FEN | Qué comprueba y por qué la elegimos |
|---|---|---|
| Captura al paso ilegal | `8/8/8/K2pP2r/8/8/8/7k w - d6 0 2` | La captura al paso exd6 quitaría **dos** peones de la quinta fila y dejaría al rey de a5 en jaque por la torre de h5. El FEN marca d6 como casilla al paso, pero la jugada no es legal. Una regla especial que cualquier implementación propia de reglas suele olvidar. |
| Enroque prohibido | `4k3/8/8/8/8/8/6b1/R3K2R w KQ - 0 1` | Hay derechos de enroque, pero el alfil de g2 ataca f1: O-O es ilegal (el rey pasaría por una casilla atacada) y O-O-O sí es legal. Distingue «tener derecho» de «poder enrocar ahora». |
| Mate en dos | `k7/8/2K5/8/8/8/8/7R w - - 0 1` | Con profundidad 2 minimax no ve el mate; con profundidad 3 da exactamente 100 000 − 3. Muestra el horizonte y la preferencia por el mate más corto. |
| Pieza envenenada | `6k1/pp3ppp/4p3/3n4/8/8/PP3PPP/3Q2K1 w - - 0 1` | El caballo de d5 parece colgado, pero lo defiende e6. El voraz juega Dxd5 y pierde la dama; minimax de profundidad 2 no la toma. |

Además, la suite `pytest` del repositorio (`tests/`) tiene **{{N_PRUEBAS}} pruebas** que cubren los mismos invariantes con más casos (todas pasan; ver el README para ejecutarla).

#### Fallos que corregimos (de la bitácora)

Estos fallos ocurrieron de verdad durante el desarrollo; cada uno está en `BITACORA.md` con la marca ERROR CORREGIDO.

| Entrada | Qué pasó | Cómo se corrigió y cómo lo comprobamos |
|---|---|---|
| G-E1 | Tras pausar, el bucle se detenía, pero el botón seguía diciendo «Pausar». | El `render()` final se ejecuta dentro de la propia tarea, que aún no está `done()`. Usamos una bandera explícita `_loop_active`. La prueba `test_gui_start_pause_inside_event_loop` pasa. |
| S-16 | La posición de perspectiva daba 0 (tablas) a toda profundidad. | Tras Cxa4 quedaba material insuficiente, que es terminal y se resuelve **antes** que E. Añadimos peones y ahora Cxa4 vale +336,5 desde negras. |
| S-17 | Una prueba exigía `score > 500` y a veces fallaba según la carga de la máquina. | El valor es el de la posición, no la ganancia de la jugada (umbral corregido), y las pruebas de comportamiento pasaron a usar `time_limit_s=0`. Verificado con 3 corridas seguidas y 4 en paralelo. |
| S-18 | La quietud contaba dos veces el nodo frontera. | Lo encontramos revisando el código contra la definición de nodo antes de ejecutarlo. Parámetro `entry=True`: solo las llamadas recursivas cuentan nodo. |
| M-E1 | El rollout uniforme de 8 plies empeoraba la táctica (0,90 frente a 1,00 de evaluar la hoja). | Rollout con sesgo a capturas y límite 4, elegido midiendo (benchmark repetido). |
| M-E2 | La prueba de perspectiva de MCTS pasaba o fallaba por suerte. | Con 8 defensas correctas de 28, un agente equivocado acierta a veces. Usamos tácticas de solución única (T3, T6), donde la variante errónea falla con todas las semillas, y añadimos un recorrido estructural del árbol (prueba 7). |
| M-E3 | MCTS reportaba un mate en uno como +5526 cp en vez de 99 999. | La inversa de la sigmoide no llega a una victoria. Si el hijo elegido es terminal se reporta su valor exacto; el benchmark se repitió completo. |
| I-13 | La búsqueda AND-OR devolvía un plan de mate en 3 en una posición con mate en 1. | Profundización 1, 2, …, n: el primer plan hallado es el más corto (`test_shortest_plan_is_preferred`). |
| I-14 | La posición de «mate del pasillo» copiada de memoria no era mate en 2. | Lo detectó el propio buscador AND-OR. Doblamos las torres (d1 y d2), y el verificador independiente certifica el plan. |
