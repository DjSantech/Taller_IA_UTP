# Bitácora G — Interfaz y controlador

Formato: **Decisión · Alternativas · Por qué · Consecuencia**. Errores reales: **ERROR CORREGIDO**
(*Qué pasó / Diagnóstico / Corrección / Lección*).

Archivos: `chess_ai/controller.py`, `chess_ai/gui.py`, `tests/test_controller.py`.

---

### G-01 · Controlador sin widgets, vista delgada
- **Decisión:** toda la lógica de turnos (AL_SOLICITAR_TURNO, deshacer, nueva partida, bucle,
  exportación) vive en `GameController`, que no importa ipywidgets. `ChessApp` solo traduce
  clics en llamadas al controlador y redibuja cuando este la notifica (`on_update`).
- **Alternativas:** meter la lógica en los callbacks de los botones, como la base `ChessView`.
- **Por qué:** así la alternancia, la obsolescencia de decisiones y el deshacer se prueban con
  `pytest` sin Jupyter, y el torneo puede reutilizar el mismo controlador sin interfaz.
- **Consecuencia:** la sección 4 del enunciado (controlador ≠ vista) queda separada en código.

### G-02 · Clase nueva `ChessApp`, no herencia de `ChessView`
- **Decisión:** la clase gráfica se llama `ChessApp` y no hereda de la `ChessView` del profesor.
  Reutiliza su idea (listas origen/destino/promoción, botón Mover, destinos posibles, SVG con
  último movimiento y jaque) y la amplía.
- **Alternativas:** heredar de `ChessView`; reemplazarla con el mismo nombre.
- **Por qué:** la celda 5 del cuaderno ya define `ChessView` solo si `READY`; heredar obligaría a
  que esa celda exista, y el paquete no podría importarse ni probarse fuera del cuaderno.
  Reusar el nombre rompería la regla de nombres únicos y ocultaría la base suministrada.
- **Consecuencia:** el tablero se dibuja en un `widgets.HTML` con el SVG (no en `Output`), lo
  que además permite comprobar el SVG en las pruebas.

### G-03 · Agentes inyectados con fábricas `{etiqueta: fabrica(AgentConfig)}`
- **Decisión:** la interfaz recibe `factories: dict[str, Callable[[AgentConfig], Agent]]`;
  «Humano» se agrega siempre con valor `None`. El controlador nunca importa los agentes.
- **Alternativas:** importar los seis agentes dentro de `gui.py`.
- **Por qué:** los agentes se escriben en paralelo en otros módulos; con fábricas, la interfaz
  no depende de su existencia y las pruebas usan agentes *stub*. La fábrica recibe la
  profundidad, el plazo, la semilla y las simulaciones de los controles.
- **Consecuencia:** cuando cambia un selector o un control de configuración, los agentes se
  reconstruyen antes de la siguiente acción (`_gui_sync_agents`).

### G-04 · Semilla por jugada = semilla base + ply
- **Decisión:** el agente recibe `seed = config.seed + ply_count` (ply antes de mover).
- **Alternativas:** misma semilla en todas las jugadas; semillas aleatorias.
- **Por qué:** con la misma semilla en cada jugada un agente aleatorio repetiría patrones; con
  semillas aleatorias no se reproduce la partida. Así la partida es reproducible y cada jugada
  tiene una semilla conocida que va al CSV (columna `seed`) y al PGN (`SeedBase`, `SeedPolicy`).
- **Consecuencia:** prueba `test_same_seed_reproduces_the_game`.

### G-05 · Plazo cooperativo: medir, marcar y aplicar
- **Decisión:** el controlador mide el tiempo real de `choose` y marca `time_exceeded` si
  supera `time_limit_s + 0.05 s` (`DEFAULT_TIME_TOLERANCE_S`). La jugada se aplica igual.
  Plazo ≤ 0 significa «sin plazo» y nunca marca exceso.
- **Alternativas:** descartar la jugada que se pasa (¿y qué jugar entonces?); declarar derrota
  por tiempo; aislar al agente en otro proceso.
- **Por qué:** descartar o dar derrota inventaría un resultado; el enunciado acepta para el
  alcance mínimo «presupuesto cooperativo y registro del exceso». La tolerancia cubre la copia
  del tablero y el costo de Python fuera de la búsqueda. Es una política uniforme para todos.
- **Consecuencia:** un agente de profundidad fija o MCTS con simulaciones fijas puede exceder
  el plazo; queda en el CSV. Medir después de devolver no interrumpe a un agente bloqueado.

### G-06 · Respuesta inválida de un agente = error, sin cambios de estado
- **Decisión:** si un agente devuelve `None` en un estado no terminal, una jugada ilegal o
  lanza una excepción, el turno se reporta como `error`, se guarda en `controller.errors`, el
  estado real no cambia, el bucle automático se detiene y no se asigna resultado.
- **Alternativas:** jugar una jugada aleatoria en su lugar; dar la partida por perdida.
- **Por qué:** sustituir la jugada oculta el fallo del agente y asignar derrota inventa un
  resultado reglamentario. Parar deja el fallo visible para corregirlo.
- **Consecuencia:** pruebas `test_invalid_agent_output_does_not_change_state` (tres casos).

### G-07 · Se compara `env.version`, no el FEN
- **Decisión:** antes de pedir la decisión se guarda `env.version`; al volver, si cambió, la
  decisión se descarta (`stale`).
- **Alternativas:** comparar el FEN o no comprobar nada (todo es de un solo hilo).
- **Por qué:** el FEN no distingue «deshice y rehice la misma jugada» ni conserva la historia
  (repeticiones); `version` aumenta en cada `apply`, `undo` y `reset`. Hoy un turno es
  síncrono, pero la comprobación protege cualquier ejecución futura en hilo o proceso.
- **Consecuencia:** prueba `test_stale_decision_is_discarded` con un agente que modifica el
  tablero real mientras «piensa».

### G-08 · Política de Deshacer
- **Decisión:** humano contra agente: se deshace 1 ply y, si con eso le tocaría al agente, 1
  más (vuelve al turno del humano). Humano-humano y agente-agente: 1 ply. Prohibido mientras
  un agente busca o mientras el bucle automático está en marcha (hay que pausar primero).
- **Alternativas:** siempre 1 ply; siempre 2.
- **Por qué:** en humano contra agente, deshacer 1 ply tras la respuesta del agente deja el
  turno al agente, que respondería otra vez lo mismo: el humano nunca podría corregir su jugada.
- **Consecuencia:** el registro de decisiones se recorta junto con la pila de jugadas.

### G-09 · Bucle cooperativo con asyncio para Iniciar/Pausar
- **Decisión:** `GameController.run_async` juega un turno, cede con `await asyncio.sleep(delay)`
  y revisa la bandera de pausa; se detiene al pausar, al terminar, al truncar, en turno humano o
  ante un error. `ChessApp` lo lanza como tarea en el bucle de eventos del kernel.
- **Alternativas:** un `for` síncrono dentro del callback; un hilo.
- **Por qué:** el `for` síncrono bloquea el kernel y el botón Pausar nunca se atiende (lo
  advierte el enunciado); un hilo tocaría widgets desde otro hilo y abriría carreras con el
  tablero. Con asyncio todo sigue en un hilo y los clics se procesan entre turnos.
- **Consecuencia (limitación):** cada turno es síncrono: mientras el agente busca (~plazo) el
  kernel no atiende clics; la pausa se aplica al terminar el turno en curso. El aislamiento en
  proceso queda fuera del alcance mínimo (sección 6). Verificado en un kernel real con nbclient.

### G-10 · Humano contra agente: respuesta automática configurable
- **Decisión:** casilla «El agente responde solo» (activa por defecto). Tras una jugada humana
  válida, si le toca a un agente, se lanza el mismo bucle cooperativo, que se detiene solo al
  volver el turno humano. Desactivada, se usa «Jugar turno del agente».
- **Por qué:** reutiliza el bucle (la jugada humana se dibuja antes de que el agente piense) y
  permite también el modo paso a paso para la sustentación.
- **Consecuencia:** fuera de un kernel (pruebas) no hay bucle de eventos y la respuesta se juega
  de forma síncrona.

### G-11 · Columnas `termination` y `official_result` del CSV
- **Decisión:** el CSV tiene exactamente `CSV_FIELDS` del enunciado. Por defecto
  (`export_csv(final=True)`) esas dos columnas llevan el estado de la partida al exportar, en
  todas las filas, como `game_id` o `white_agent`. Con `final=False`, el estado tras cada jugada.
- **Por qué:** son columnas de nivel partida; el análisis del torneo agrupa por resultado.
- **Consecuencia:** una partida truncada exporta `truncated` y `*` (no tablas). `elapsed_s` es
  el tiempo medido por el controlador; el que reporta el agente queda aparte (`agent_elapsed_s`).

### G-12 · Jugadas humanas también se registran
- **Decisión:** cada jugada humana crea un `MoveRecord` con agente «Humano» y métricas en cero.
- **Por qué:** el registro queda alineado con la pila de jugadas (deshacer recorta ambos) y el
  CSV de una partida humano-agente está completo.

---

### ERROR CORREGIDO G-E1 · El botón seguía en «Pausar» después de parar el bucle
- **Qué pasó:** la prueba `test_gui_start_pause_inside_event_loop` falló: tras pausar, el bucle
  se detuvo (motivo `paused`) pero el botón seguía diciendo «Pausar».
- **Diagnóstico:** `render()` decidía si el bucle estaba activo con `not self._task.done()`. El
  último `render()` se ejecuta en el `finally` de la propia tarea, y en ese momento la tarea
  todavía no ha terminado, así que `done()` es `False`.
- **Corrección:** bandera explícita `_loop_active`, que se pone en `True` al Iniciar y en
  `False` en el `finally`, antes del último `render()`.
- **Lección:** una tarea no puede preguntarse a sí misma si ya terminó; el estado de la vista
  debe salir de banderas que el código controla, no del estado interno de asyncio.
