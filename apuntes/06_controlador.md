## Integración del controlador: `GameController`

`GameController` (`chess_ai/controller.py`) coordina el estado real (`ChessEnvironment`) con los
dos jugadores. Cada jugador es un agente que cumple el contrato `Agent` o `None` (humano). No
crea widgets: la interfaz se suscribe con `on_update` y recibe un `TurnReport` después de cada
operación. Por eso toda la lógica de turnos se prueba con `pytest` sin Jupyter.

### AL_SOLICITAR_TURNO en código

`request_turn()` sigue el pseudocódigo de la sección 6 paso a paso:

| Pseudocódigo | Implementación | Resultado |
|---|---|---|
| si hay búsqueda activa o partida terminada: informar y salir | `searching` o `env.is_over()` | `busy` / `over` (nunca se pide jugada a un agente en un estado terminal) |
| identificar agente según el color al turno | `agent_for(board.turn)` | |
| si es humano: esperar | agente `None` | `human` |
| capturar identificador de versión | `version = env.version` | |
| copiar el tablero conservando la historia | `env.copy_for_agent()` (`copy(stack=True)`) | |
| solicitar Decision | `agent.choose(copia, time_limit_s=plazo, seed=semilla_base + ply)` | |
| comprobar plazo | tiempo real medido > plazo + 0,05 s → `time_exceeded` | se registra, la jugada se aplica |
| comprobar que la versión siga vigente | `env.version != version` | `stale`: decisión descartada |
| comprobar legalidad | `None`, jugada ilegal o excepción | `error`: estado sin cambios, sin resultado inventado |
| aplicar exactamente una jugada | `env.apply(move)` | `applied` |
| registrar métricas y actualizar vista | `MoveRecord` + `on_update` | |

Cada llamada aplica **como máximo una** jugada. Las jugadas humanas entran por `human_move()`,
que rechaza jugadas ilegales, jugadas en el turno de un agente y jugadas en partidas terminadas;
las válidas pasan también por `env.apply`.

### Por qué se compara `version`

El agente trabaja sobre una copia. Entre el momento en que se copia el tablero y el momento en
que vuelve la decisión, el estado real podría cambiar: el usuario deshace, empieza una partida
nueva o hay otra jugada. Si el controlador aplicara la decisión sin comprobarlo, aplicaría una
jugada pensada para una posición que ya no existe: podría ser ilegal o, peor, legal pero sin
sentido (y además el turno avanzaría dos veces).

`ChessEnvironment.version` aumenta en cada `apply`, `undo` y `reset`. Compararla es más sólido
que comparar el FEN: el FEN no distingue «deshice y volví a jugar lo mismo» y no contiene la
historia (repeticiones, regla de 50) con la que el agente decidió. Hoy cada turno es síncrono y
de un solo hilo, así que el caso solo aparece si algo modifica el tablero durante `choose`; la
prueba `test_stale_decision_is_discarded` lo provoca con un agente que mueve el tablero real
mientras «piensa», y comprueba que su jugada se descarta. La comprobación deja el controlador
listo para ejecutar agentes en un hilo o en otro proceso sin cambiar la lógica.

### Políticas

- **Semilla por jugada:** `semilla = semilla_base + ply` (ply antes de mover). La misma semilla
  base reproduce la partida; cada jugada tiene una semilla conocida (columna `seed` del CSV).
- **Plazo:** cooperativo. Se mide el tiempo real de `choose`; si supera el plazo más una
  tolerancia de 0,05 s se marca `time_exceeded` y la jugada se aplica igual, para todos los
  agentes por igual. Plazo 0 = sin plazo. Medir después no interrumpe a un agente bloqueado;
  el aislamiento en proceso queda fuera del alcance mínimo.
- **Respuesta inválida:** `None` en estado no terminal, jugada ilegal o excepción → error
  registrado en `controller.errors`, estado sin cambios y bucle detenido.
- **Deshacer:** humano contra agente vuelve al turno del humano (pareja de turnos si el agente
  ya respondió); otros modos, un ply; prohibido con búsqueda activa o bucle en marcha.
- **Truncada:** el límite de plies lo aplica el entorno (`max_plies`): el estado pasa a
  `truncated`, el controlador ya no pide jugadas y el PGN/CSV llevan resultado `*`, no tablas.

### Bucle cooperativo

`run_async()` juega turnos seguidos y entre uno y otro ejecuta `await asyncio.sleep(pausa)`,
que devuelve el control al bucle de eventos del kernel para que atienda el botón **Pausar**.
Se detiene por pausa, partida terminada, truncamiento, turno humano o error, y devuelve el
motivo. Un turno sigue siendo síncrono: la cancelación es entre turnos, no dentro de la búsqueda.
`play_until_stop()` es la versión síncrona para pruebas y scripts sin bucle de eventos.

### Exportación

- `export_pgn(ruta)`: `env.to_pgn` con encabezados de agentes, semilla base y política,
  plazo, tolerancia, profundidad, simulaciones y modo. Una partida truncada lleva `Result "*"`.
- `export_csv(ruta)`: exactamente las columnas `CSV_FIELDS` del enunciado; una fila por jugada
  (agente o humano). `termination` y `official_result` llevan el estado de la partida al exportar.
