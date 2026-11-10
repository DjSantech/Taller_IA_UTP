### Nuestro análisis (sección 2)

**Integrantes:** Santiago Guevara y Januar Mena.

| Componente | Nuestra especificación |
|---|---|
| **Desempeño** | (1) **Legalidad**: el 100 % de las jugadas aplicadas al estado real son legales; una jugada ilegal o una decisión `None` en un estado no terminal se registran como error, nunca se aplican. (2) **Puntos reglamentarios** bajo un presupuesto temporal fijo por decisión: victoria 1, tablas 0.5, derrota 0, solo sobre partidas terminadas; las truncadas se reportan aparte. (3) **Tiempo**: tiempo por jugada y número de excesos sobre el presupuesto. (4) **Reproducibilidad**: misma semilla y mismo presupuesto por simulaciones o profundidad ⇒ misma decisión. |
| **Entorno** | Tablero 8×8 con las reglas clásicas (python-chess las valida). Rival: humano u otro agente, desconocido para quien decide. Reloj: presupuesto cooperativo por decisión (0.2 s en el torneo, ajustado al equipo) y límite de 160 plies, que produce el estado «truncada». Política de tablas: reclamo automático cuando `outcome(claim_draw=True)` lo permite. |
| **Actuadores** | Elegir **una** jugada legal (en UCI, con la pieza de promoción cuando aplica) y devolverla en un `Decision`. El agente nunca toca el estado real: el controlador valida y aplica la jugada. |
| **Sensores** | Una copia del tablero **con su historia** (`board.copy(stack=True)`): colocación, turno, derechos de enroque, casilla de captura al paso, reloj de 50 jugadas y pila de jugadas; además, el presupuesto (`time_limit_s`) y la semilla. |

**¿Cómo mediremos la fuerza?** La medida principal es la de **puntos bajo un presupuesto temporal** (torneo, Experimento 2), porque compara agentes de naturaleza distinta (profundidad fija, profundización iterativa, MCTS) con el mismo recurso. Como medidas complementarias usamos la **precisión táctica** (acierto en posiciones con solución verificada, Experimento 4) y la **eficiencia** (nodos, hojas y podas a profundidad fija, Experimento 1). La profundidad fija sirve para estudiar alfa-beta; el presupuesto temporal, para comparar fuerza.

**Estado.** El FEN describe colocación, turno, enroques, casilla al paso y relojes, pero **no basta**: la repetición triple depende de las posiciones anteriores. Nuestro estado es el FEN más la historia de posiciones desde la última jugada irreversible. Por eso los agentes reciben `board.copy(stack=True)` y no un FEN aislado (lo comprobamos con una prueba: tras `Nf3 Nf6 Ng1 Ng8` ×2, la historia detecta la repetición y el FEN solo no).

**Clasificación del entorno (AIMA cap. 2).**

| Propiedad | Clasificación | Por qué |
|---|---|---|
| Observabilidad | Totalmente observable | El tablero y la historia son visibles para ambos jugadores. |
| Agentes | Multiagente competitivo | La utilidad de uno es la opuesta de la del otro (suma cero). |
| Determinismo | Determinista | Dado el estado y la jugada, el estado siguiente es único. |
| Episódico/secuencial | Secuencial | Cada jugada condiciona todas las siguientes. |
| Estático/dinámico | Semidinámico con reloj | El tablero no cambia mientras se piensa, pero el presupuesto sí se consume. |
| Discreto/continuo | Discreto | Número finito de estados, jugadas y turnos. |
| Conocido | Conocido | Las reglas (el modelo de transición) son conocidas por completo. |

**¿Por qué un rival desconocido no vuelve estocásticas las reglas?** En AIMA, «estocástico» se refiere al **modelo de transición**: si, dada una acción, el resultado tiene azar. En ajedrez, aplicar una jugada produce siempre la misma posición. Lo que no conocemos es **qué acción elegirá el otro agente**, y eso es incertidumbre estratégica, no azar del entorno. Por eso no se modela con probabilidades (expectiminimax) sino como adversario (minimax): se supone que el rival elige lo peor para nosotros. El azar real (dados) lo estudiamos aparte, en la actividad 7D, sin alterar las reglas del ajedrez.

**Cómo garantizamos los invariantes.**

| Invariante | Mecanismo | Prueba |
|---|---|---|
| Todo movimiento aplicado es legal | `ChessEnvironment.apply` rechaza lo que no esté en `legal_moves` y no cambia el estado | `test_environment_rejects_illegal_and_keeps_state` |
| Las búsquedas no modifican la posición real | Los agentes reciben una copia; dentro de la búsqueda, `push`/`pop` en `try/finally`; FEN y pila se verifican antes y después | Pruebas de «tablero intacto» de cada agente, también con plazo vencido |
| El turno cambia una sola vez por movimiento | El controlador aplica exactamente una jugada por turno y descarta decisiones de una `version` vieja del estado | `tests/test_controller.py` |
| Una partida terminal no pide otra jugada | `status()` es `terminal`/`truncated` ⇒ el controlador no consulta al agente; `apply` rechaza jugadas | `test_terminal_game_accepts_no_moves_and_truncation_is_not_a_draw` |

**Política de tablas.** En la partida real, reclamo automático (`outcome(claim_draw=True)`). Dentro de las búsquedas usamos una prueba terminal equivalente y más barata (`search_outcome`: mate, ahogado, material insuficiente, regla de 50 y repetición triple de la posición del nodo). Los reclamos «antes de mover» aparecen en el árbol como la repetición del hijo correspondiente (decisión D-08 de la bitácora). El límite de 160 plies produce **truncada**, con resultado oficial `*`, nunca tablas.
