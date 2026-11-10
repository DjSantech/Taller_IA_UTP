# Bitácora de decisiones — Taller 3 (ajedrez gráfico y agentes)

**Integrantes:** Santiago Guevara y Januar Mena · **Curso:** Inteligencia Artificial (UTP)

Registro de las decisiones de diseño, los errores cometidos y su corrección.
Formato de cada entrada: **Decisión · Alternativas · Por qué · Consecuencia**. Los errores
reales llevan la marca **ERROR CORREGIDO** (*Qué pasó / Diagnóstico / Corrección / Lección*):
son el material de la conclusión individual que pide la sección 12.

Prefijos: `D-` decisiones generales; `E-` evaluación y agentes básicos; `S-` minimax,
alfa-beta y profundización; `M-` MCTS; `T-` ajuste de pesos (mejora); `G-` interfaz y
controlador; `I-` actividades de integración (torre, AND-OR, expectiminimax, Kriegspiel);
`X-` experimentos y torneo; `N-` cuaderno, README y entrega.

Este archivo se **genera** con `python tools/unir_bitacora.py` a partir de `apuntes/bitacora_*.md`
(una bitácora por etapa, escrita mientras se desarrollaba cada módulo).

---

## Etapa 0 — Estructura, entorno, contrato y evaluación (prefijo D-)

#### D-01 · El entregable es el propio cuaderno del profesor, construido desde módulos probados
- **Decisión:** el código vive en el paquete `chess_ai/` (un módulo por responsabilidad, con
  pruebas en `tests/`) y `tools/construir_cuaderno.py` lo inserta en las celdas del enunciado,
  conservando todas sus secciones y su pseudocódigo.
- **Alternativas:** escribir todo en celdas; entregar un cuaderno delgado que solo importe el paquete.
- **Por qué:** el mismo esquema funcionó en el Taller 2: los módulos se prueban con `pytest`,
  se pueden desarrollar en paralelo, y el cuaderno sigue siendo autocontenido. Además la lista
  de entrega pide expresamente «módulos propios y README».
- **Consecuencia:** cada módulo solo importa de los anteriores en el orden
  `contract → environment → evaluation → agents_basic → search → mcts → tuning → controller → gui → tournament → experiments`.

#### D-02 · Primer commit con el enunciado intacto
- El primer commit de la rama `taller-3` contiene el cuaderno exactamente como lo entregó el
  profesor. Separa en el historial lo del docente de lo propio y es la base idempotente del constructor.

#### D-03 · Entorno virtual fuera de OneDrive, versiones fijadas
- `C:\Users\<usuario>\venvs\ia-taller3` (misma razón que en los talleres 1 y 2: OneDrive sincronizaría
  miles de archivos del entorno). `requirements.txt` fija las versiones realmente probadas.

#### D-04 · Mismo repositorio, rama independiente `taller-3`
- Repositorio `DjSantech/Taller_IA_UTP`: el Taller 1 está en `main`, el Taller 2 en `taller-2`.
  El Taller 3 va en su propia rama para no mezclar historiales. No se hace `push` sin orden explícita.

#### D-05 · Identificadores en inglés, explicaciones en español
- El contrato suministrado ya usa nombres en inglés (`ChessEnvironment`, `SearchStats`,
  `Decision`…); se mantiene la convención del Taller 2.

#### D-06 · Perspectiva única: E(s) desde blancas; `Decision.score` desde quien decide
- **Decisión:** la evaluación y las utilidades terminales «absolutas» son siempre desde blancas
  (positivo = bueno para blancas). Cada agente multiplica por `perspective_sign(color)` para
  obtener el valor del jugador que decide en la raíz, y así reporta `Decision.score`.
- **Alternativas:** evaluación relativa al jugador al turno (estilo negamax).
- **Por qué:** con una sola convención absoluta, minimax MAX/MIN se escribe tal como en AIMA
  y un error de signo se detecta con una prueba simple de antisimetría (reflejar el tablero
  invierte el signo). La pregunta 4 de la sustentación trata exactamente de este error.
- **Consecuencia:** la evaluación de negras «favorece a negras» porque, cuando negras deciden,
  se minimiza E (equivalente a maximizar −E).

#### D-07 · Terminales antes que E, mates más cortos preferidos
- `MATE_SCORE = 100000`; una victoria a distancia `ply` vale `MATE_SCORE − ply`; tablas, 0.
  `E` se recorta a ±10000, así que cualquier mate domina a cualquier estimación.
- **Interacción con la caché (si se usa tabla de transposición):** el valor de mate depende de la
  distancia a la raíz; si alguna vez se guarda en una tabla hay que convertirlo a «distancia
  desde el nodo» al guardar y deshacer la conversión al leer.

#### D-08 · Dos pruebas terminales: la de la partida y la de la búsqueda
- **Decisión:** la partida real usa `board.outcome(claim_draw=True)` (política del enunciado).
  Dentro de la búsqueda se usa `search_outcome`: sin jugadas legales (mate/ahogado), material
  insuficiente, `halfmove_clock ≥ 100` y `is_repetition(3)`.
- **Alternativas:** usar `claim_draw=True` en cada nodo.
- **Por qué:** `can_claim_threefold_repetition` prueba además cada jugada legal posible (empuja
  y deshace todas), lo que multiplica el costo de cada nodo. Esos reclamos «antes de mover»
  aparecen en el árbol como repetición triple del hijo correspondiente, así que el valor de la
  búsqueda no cambia. Se verifica en las pruebas que ambas políticas coinciden en mate y ahogado.
- **Consecuencia:** la clave de la historia importa: un FEN aislado no detecta la repetición
  (prueba `test_repetition_is_detected_from_history_not_from_fen`, pregunta 7).

#### D-09 · «Truncada» no es tablas
- `ChessEnvironment.status()` devuelve `ongoing | terminal | truncated`. El límite de plies
  produce `truncated` con resultado oficial `*`, separado de las tablas reglamentarias.

#### D-10 · Plazo cooperativo (`Deadline`), no interrupción
- La búsqueda pregunta por el plazo; nadie la detiene desde fuera. Si una búsqueda de
  profundidad fija se pasa, el controlador mide y registra `time_exceeded`; no puede
  interrumpir un agente bloqueado. El aislamiento en otro proceso queda fuera del alcance mínimo
  (sección 6 del enunciado) y se documenta como tal.

#### D-11 · Evaluación común E = wm·M + wp·P + wk·K + wa·A
- M material (P=1, N=3.2, B=3.3, R=5, Q=9); P pasados (con bono por avance) − doblados − aislados;
  K (escudo de peones − casillas de la zona del rey atacadas) × fase, que se apaga en finales;
  A casillas atacadas por N, B, R, Q no ocupadas por piezas propias.
- Pesos iniciales `(100, 15, 10, 4)` centipeones por unidad. La tabla completa (escala, signo,
  costo y qué decisión induce cada término) está en el docstring de `chess_ai/evaluation.py`.
- **Por qué estos términos:** son baratos con bitboards y cada uno induce una decisión
  distinta (no regalar material, empujar pasados, enrocar, desarrollar). El vector de
  características `features()` se reutiliza para el ajuste de pesos por búsqueda local.

---

## Etapa 1 — Interfaz y controlador (prefijo G-)

Archivos: `chess_ai/controller.py`, `chess_ai/gui.py`, `tests/test_controller.py`.

---

#### G-01 · Controlador sin widgets, vista delgada
- **Decisión:** toda la lógica de turnos (AL_SOLICITAR_TURNO, deshacer, nueva partida, bucle,
  exportación) vive en `GameController`, que no importa ipywidgets. `ChessApp` solo traduce
  clics en llamadas al controlador y redibuja cuando este la notifica (`on_update`).
- **Alternativas:** meter la lógica en los callbacks de los botones, como la base `ChessView`.
- **Por qué:** así la alternancia, la obsolescencia de decisiones y el deshacer se prueban con
  `pytest` sin Jupyter, y el torneo puede reutilizar el mismo controlador sin interfaz.
- **Consecuencia:** la sección 4 del enunciado (controlador ≠ vista) queda separada en código.

#### G-02 · Clase nueva `ChessApp`, no herencia de `ChessView`
- **Decisión:** la clase gráfica se llama `ChessApp` y no hereda de la `ChessView` del profesor.
  Reutiliza su idea (listas origen/destino/promoción, botón Mover, destinos posibles, SVG con
  último movimiento y jaque) y la amplía.
- **Alternativas:** heredar de `ChessView`; reemplazarla con el mismo nombre.
- **Por qué:** la celda 5 del cuaderno ya define `ChessView` solo si `READY`; heredar obligaría a
  que esa celda exista, y el paquete no podría importarse ni probarse fuera del cuaderno.
  Reusar el nombre rompería la regla de nombres únicos y ocultaría la base suministrada.
- **Consecuencia:** el tablero se dibuja en un `widgets.HTML` con el SVG (no en `Output`), lo
  que además permite comprobar el SVG en las pruebas.

#### G-03 · Agentes inyectados con fábricas `{etiqueta: fabrica(AgentConfig)}`
- **Decisión:** la interfaz recibe `factories: dict[str, Callable[[AgentConfig], Agent]]`;
  «Humano» se agrega siempre con valor `None`. El controlador nunca importa los agentes.
- **Alternativas:** importar los seis agentes dentro de `gui.py`.
- **Por qué:** los agentes se escriben en paralelo en otros módulos; con fábricas, la interfaz
  no depende de su existencia y las pruebas usan agentes *stub*. La fábrica recibe la
  profundidad, el plazo, la semilla y las simulaciones de los controles.
- **Consecuencia:** cuando cambia un selector o un control de configuración, los agentes se
  reconstruyen antes de la siguiente acción (`_gui_sync_agents`).

#### G-04 · Semilla por jugada = semilla base + ply
- **Decisión:** el agente recibe `seed = config.seed + ply_count` (ply antes de mover).
- **Alternativas:** misma semilla en todas las jugadas; semillas aleatorias.
- **Por qué:** con la misma semilla en cada jugada un agente aleatorio repetiría patrones; con
  semillas aleatorias no se reproduce la partida. Así la partida es reproducible y cada jugada
  tiene una semilla conocida que va al CSV (columna `seed`) y al PGN (`SeedBase`, `SeedPolicy`).
- **Consecuencia:** prueba `test_same_seed_reproduces_the_game`.

#### G-05 · Plazo cooperativo: medir, marcar y aplicar
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

#### G-06 · Respuesta inválida de un agente = error, sin cambios de estado
- **Decisión:** si un agente devuelve `None` en un estado no terminal, una jugada ilegal o
  lanza una excepción, el turno se reporta como `error`, se guarda en `controller.errors`, el
  estado real no cambia, el bucle automático se detiene y no se asigna resultado.
- **Alternativas:** jugar una jugada aleatoria en su lugar; dar la partida por perdida.
- **Por qué:** sustituir la jugada oculta el fallo del agente y asignar derrota inventa un
  resultado reglamentario. Parar deja el fallo visible para corregirlo.
- **Consecuencia:** pruebas `test_invalid_agent_output_does_not_change_state` (tres casos).

#### G-07 · Se compara `env.version`, no el FEN
- **Decisión:** antes de pedir la decisión se guarda `env.version`; al volver, si cambió, la
  decisión se descarta (`stale`).
- **Alternativas:** comparar el FEN o no comprobar nada (todo es de un solo hilo).
- **Por qué:** el FEN no distingue «deshice y rehice la misma jugada» ni conserva la historia
  (repeticiones); `version` aumenta en cada `apply`, `undo` y `reset`. Hoy un turno es
  síncrono, pero la comprobación protege cualquier ejecución futura en hilo o proceso.
- **Consecuencia:** prueba `test_stale_decision_is_discarded` con un agente que modifica el
  tablero real mientras «piensa».

#### G-08 · Política de Deshacer
- **Decisión:** humano contra agente: se deshace 1 ply y, si con eso le tocaría al agente, 1
  más (vuelve al turno del humano). Humano-humano y agente-agente: 1 ply. Prohibido mientras
  un agente busca o mientras el bucle automático está en marcha (hay que pausar primero).
- **Alternativas:** siempre 1 ply; siempre 2.
- **Por qué:** en humano contra agente, deshacer 1 ply tras la respuesta del agente deja el
  turno al agente, que respondería otra vez lo mismo: el humano nunca podría corregir su jugada.
- **Consecuencia:** el registro de decisiones se recorta junto con la pila de jugadas.

#### G-09 · Bucle cooperativo con asyncio para Iniciar/Pausar
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

#### G-10 · Humano contra agente: respuesta automática configurable
- **Decisión:** casilla «El agente responde solo» (activa por defecto). Tras una jugada humana
  válida, si le toca a un agente, se lanza el mismo bucle cooperativo, que se detiene solo al
  volver el turno humano. Desactivada, se usa «Jugar turno del agente».
- **Por qué:** reutiliza el bucle (la jugada humana se dibuja antes de que el agente piense) y
  permite también el modo paso a paso para la sustentación.
- **Consecuencia:** fuera de un kernel (pruebas) no hay bucle de eventos y la respuesta se juega
  de forma síncrona.

#### G-11 · Columnas `termination` y `official_result` del CSV
- **Decisión:** el CSV tiene exactamente `CSV_FIELDS` del enunciado. Por defecto
  (`export_csv(final=True)`) esas dos columnas llevan el estado de la partida al exportar, en
  todas las filas, como `game_id` o `white_agent`. Con `final=False`, el estado tras cada jugada.
- **Por qué:** son columnas de nivel partida; el análisis del torneo agrupa por resultado.
- **Consecuencia:** una partida truncada exporta `truncated` y `*` (no tablas). `elapsed_s` es
  el tiempo medido por el controlador; el que reporta el agente queda aparte (`agent_elapsed_s`).

#### G-12 · Jugadas humanas también se registran
- **Decisión:** cada jugada humana crea un `MoveRecord` con agente «Humano» y métricas en cero.
- **Por qué:** el registro queda alineado con la pila de jugadas (deshacer recorta ambos) y el
  CSV de una partida humano-agente está completo.

---

#### ERROR CORREGIDO G-E1 · El botón seguía en «Pausar» después de parar el bucle
- **Qué pasó:** la prueba `test_gui_start_pause_inside_event_loop` falló: tras pausar, el bucle
  se detuvo (motivo `paused`) pero el botón seguía diciendo «Pausar».
- **Diagnóstico:** `render()` decidía si el bucle estaba activo con `not self._task.done()`. El
  último `render()` se ejecuta en el `finally` de la propia tarea, y en ese momento la tarea
  todavía no ha terminado, así que `done()` es `False`.
- **Corrección:** bandera explícita `_loop_active`, que se pone en `True` al Iniciar y en
  `False` en el `finally`, antes del último `render()`.
- **Lección:** una tarea no puede preguntarse a sí misma si ya terminó; el estado de la vista
  debe salir de banderas que el código controla, no del estado interno de asyncio.

---

## Etapa 2 — Agentes aleatorio y voraz; mejora: ajuste de pesos (prefijos E- y T-)

---

### E — Agentes básicos (`chess_ai/agents_basic.py`)

#### E-01 · Ordenar las jugadas por UCI antes de muestrear o desempatar
- **Decisión:** ambos agentes trabajan sobre `sorted(board.legal_moves, key=uci)`.
- **Alternativas:** usar el orden del generador de `python-chess` tal cual.
- **Por qué:** ese orden es determinista hoy, pero es un detalle interno de la biblioteca. Con la
  lista ordenada, la jugada elegida depende solo de (posición, semilla).
- **Consecuencia:** reproducibilidad exacta (misma semilla → misma jugada; prueba
  `test_same_seed_same_move`). La partida Voraz–Aleatorio de la semilla 0 se repitió idéntica
  (`1-0`, mate en el ply 81).

#### E-02 · `random.Random(seed)` local en cada llamada
- **Decisión:** cada `choose` crea su propio generador con la semilla recibida; no se usa el
  estado global de `random`.
- **Alternativas:** un generador por agente que avanza entre llamadas.
- **Por qué:** con un generador persistente la jugada dependería de cuántas veces se llamó antes
  al agente (p. ej. tras un «deshacer»). Así la decisión es una función pura de la posición y la
  semilla; el controlador decide qué semilla pasa en cada ply.
- **Consecuencia:** si el controlador pasara la misma semilla en todos los plies, el aleatorio no
  dejaría de ser uniforme por posición, pero sería el mismo «sorteo» repetido; el controlador o el
  torneo deben derivar la semilla del ply.

#### E-03 · Estados terminales: `move=None` con la utilidad exacta
- **Decisión:** si `search_outcome(board)` no es `None`, ambos agentes devuelven `move=None` y
  `score = perspective_sign(turno) · terminal_value_white(outcome, 0)`.
- **Alternativas:** `score=None` también en terminales.
- **Por qué:** el enunciado pide «sin decisión nueva, utilidad de derrota para negras» en la
  posición de mate. Con la utilidad exacta el controlador puede mostrarla.
- **Consecuencia:** en `checkmate` ambos agentes devuelven `-MATE_SCORE`; en `stalemate`, 0. En
  estados no terminales el Aleatorio devuelve `score=None` (no evalúa).

#### E-04 · Voraz: terminal antes que E, a distancia 1
- **Decisión:** cada sucesor se valora con `terminal_value_white(outcome, 1)` si es terminal y con
  `E` solo si no lo es. El valor desde blancas se multiplica por `perspective_sign` del que decide.
- **Alternativas:** consultar solo `E` (no distingue mate de «mucho material»).
- **Por qué:** D-06 y D-07: los terminales dominan y la perspectiva es única.
- **Consecuencia:** en `mate_in_one` elige `Dg7#` con `score = 99999`; en la posición propia
  `4k3/p7/8/3Q4/8/2n5/7P/4K3 b` (negras) elige `Cxd5` con `score > 0`. Los peones de esa posición
  están para que tras la captura no quede material insuficiente (que sería tablas = 0 y haría la
  prueba ambigua).

#### E-05 · Desempate aleatorio con la semilla, con tolerancia 1e-9
- **Decisión:** entre las jugadas a menos de `1e-9` del máximo se elige con `Random(seed)`.
- **Alternativas:** la primera jugada empatada; la última.
- **Por qué:** en posiciones tranquilas muchas jugadas valen lo mismo; tomar siempre la primera
  introduce un sesgo sistemático (p. ej. siempre jugadas de la columna a). La tolerancia evita que
  dos sumas de flotantes iguales en teoría se traten como distintas.
- **Consecuencia:** reproducible por semilla y sin sesgo de orden. Se usa también en el autojuego
  del ajuste, donde da variedad a las partidas.

#### E-06 · Métricas del voraz y del aleatorio
- **Decisión:** voraz: `nodes` = sucesores generados (push), `leaves` = sucesores valorados,
  `completed_depth` = 1 si valoró todos. Aleatorio: todo en 0 salvo `elapsed_s`.
- **Por qué:** la raíz no se cuenta como nodo para que «nodos» del voraz coincida con el número de
  jugadas legales; los demás agentes deben declarar su definición para que el torneo no compare
  números incomparables (sección 9).
- **Consecuencia:** en la posición inicial `nodes = leaves = 20`. En 10 partidas contra el
  aleatorio el voraz generó en promedio 42 sucesores por decisión en 11,1 ms.

#### E-07 · Plazo cooperativo también en el voraz
- **Decisión:** se revisa `Deadline.expired()` después de cada sucesor; si vence, se devuelve la
  mejor jugada vista y `completed_depth = 0`.
- **Alternativas:** ignorar el plazo (el voraz es barato).
- **Por qué:** el contrato pide devolver la mejor jugada legal disponible al vencer el plazo, nunca
  `None`. Siempre se valora al menos un sucesor.
- **Consecuencia:** con `time_limit_s = 1e-9` devuelve una jugada legal tras 1 nodo (prueba).

#### E-08 · El evaluador es cualquier invocable
- **Decisión:** `GreedyAgent(evaluator)` acepta un `Evaluator` o una función `board -> cp`.
- **Por qué:** el ajuste de pesos necesita un voraz «solo material» y la ablación necesita un voraz
  con `E*`, sin subclases nuevas.
- **Consecuencia:** el autojuego de `tuning.py` usa `GreedyAgent(_tune_material_white)`.

#### E-09 · Tablero intacto aunque falle el evaluador
- **Decisión:** `push` y `pop` en `try/finally`.
- **Consecuencia:** la prueba `test_greedy_restores_board_even_if_evaluator_fails` usa un evaluador
  que lanza `RuntimeError`: la excepción sale, pero FEN y `move_stack` quedan iguales.

#### E-10 · Posición donde el voraz falla (pregunta 1): `GREEDY_TRAP_FEN`
- **Decisión:** `4r1k1/1p3ppp/1Q6/8/8/8/5PPP/6K1 w - - 0 1`. Negras amenazan `...Te1#` (mate del
  pasillo). El voraz juega `Dxb7` (+430 cp desde blancas con E0; la siguiente mejor era `De6`,
  +368) y tras `...Te1` hay mate.
- **Alternativas:** una dama que captura un peón defendido (el voraz también cae, pero «minimax
  encuentra una defensa» queda menos claro).
- **Por qué:** la pregunta pide una posición donde minimax encuentre una **defensa**. Con un
  minimax-2 de comprobación (script desechable, no forma parte del paquete) `Dxb7` vale
  `-99998` y la mejor jugada es `Db4` (+324), que cubre e1; siguen `Db5`, `f3`, `f4`, `h3`, `g3`.
- **Consecuencia:** la prueba `test_greedy_falls_into_back_rank_trap` verifica que el voraz cae con
  cinco semillas y que `Te1` da mate. La parte de minimax la verifica el módulo de búsqueda.

#### E-11 · Observación: tablas por reclamo automático en una partida ganada
- **Qué se vio:** en 10 partidas Voraz (E0) contra Aleatorio (0,2 s, 160 plies) hubo 9 victorias
  del voraz por mate y 1 tablas (semilla 5, voraz con negras). En la posición final negras tenían
  `E = −3414` (dos caballos, dos alfiles y torre contra torre y peones), pero el rey negro iba y
  venía (`Kd7`, `Ke7`, `Ke6`…).
- **Diagnóstico:** el voraz no ve mates a más de un ply; todas esas jugadas de rey valían igual.
  La partida terminó porque la política del taller `outcome(claim_draw=True)` da tablas en cuanto
  el bando al turno **puede** reclamar una repetición triple, aunque el voraz nunca habría elegido
  la jugada que repite (para él vale 0, frente a +3414).
- **Consecuencia:** no es un error del agente ni del entorno: es la convención experimental
  explícita de la sección 2, combinada con el horizonte de un ply. Se usa en `05a_basicos.md` como
  ejemplo del sesgo de corto plazo.

---

### T — Ajuste de pesos por búsqueda local (`chess_ai/tuning.py`, mejora adicional y 7C)

#### T-01 · Etiqueta estilo Texel: resultado final de la partida
- **Decisión:** cada posición se etiqueta con el resultado de la partida de la que sale, desde
  blancas: 1, 0,5 o 0. El objetivo es `J(w) = media[(σ(E_w/K) − y)²]`.
- **Alternativas:** (a) etiquetar con el valor de una búsqueda alfa-beta más profunda con solo
  material; (b) etiquetas de un motor externo (prohibido).
- **Por qué:** (a) mediría qué tan bien E imita a otra búsqueda nuestra (que además usa material,
  así que favorece a wm) y no qué tan bien predice ganar. El resultado no depende de ningún motor
  ni de E0.
- **Consecuencia (límite):** etiquetas ruidosas: una posición buena se pierde por una jugada
  aleatoria posterior y las tablas por material insuficiente son frecuentes. El ruido se promedia
  con muchas posiciones, no desaparece: J nunca baja de ~0,044 (ver T-09).

#### T-02 · Autojuego ε-voraz con solo material
- **Decisión:** en cada ply el jugador juega al azar con probabilidad ε y, si no, juega el Voraz
  con SOLO material. Cada bando de cada partida sortea ε en [0; 0,5]. Límite: 200 plies.
- **Alternativas:** Aleatorio puro (casi nunca hay mate: resultados casi siempre tablas o
  truncadas); Voraz con E0 (los datos ya «presupondrían» los pesos que se van a ajustar);
  un jugador más fuerte (minimax-2 con material: ~10 veces más caro por partida).
- **Por qué:** ε distinto en cada bando crea desequilibrios reales y resultados decisivos; usar solo
  material evita la circularidad. Medido: 900 partidas en 75,9 s (≈ 0,084 s por partida).
- **Consecuencia (límite):** las posiciones vienen de juego débil. Los pesos quedan ajustados para
  predecir resultados de ESE juego, no del juego de alfa-beta: hay un cambio de distribución que
  solo la ablación en partidas (agente de experimentos) puede medir.

#### T-03 · Separación entrenamiento/prueba por partida y por FEN
- **Decisión:** generadores de semillas distintos (`train_seed = 31`, `test_seed = 7919`); una
  partida va entera a un lado; se eliminan duplicados por clave «colocación, turno, enroques, al
  paso» dentro de cada conjunto y se descarta de prueba toda posición que esté en entrenamiento.
- **Alternativas:** mezclar todas las posiciones y partirlas al azar.
- **Por qué:** las posiciones de una misma partida comparten etiqueta y son casi iguales; partirlas
  al azar filtra información de prueba al entrenamiento y hace que prueba parezca mejor de lo que es.
- **Consecuencia:** en la corrida real 23 duplicados eliminados en entrenamiento, 3 en prueba y 1
  posición de prueba descartada por estar en entrenamiento. Prueba de pytest: ningún FEN ni
  `game_id` compartido.

#### T-04 · Qué posiciones se muestrean
- **Decisión:** desde el ply 8, una cada 3 plies; se descartan partidas truncadas (sin resultado
  oficial), posiciones terminales, en jaque, o cuya última jugada fue una captura.
- **Por qué:** truncada no es tablas (D-09), así que no tiene etiqueta. E es estática: a mitad de un
  cambio de piezas mide mal el material (filtro de quietud barato, sin búsqueda de quietud).
- **Consecuencia:** 127 de 600 partidas de entrenamiento y 54 de 300 de prueba se truncaron y se
  descartaron. Sesgo asumido: las partidas largas e indecisas quedan subrepresentadas.

#### T-05 · wm fijo = 100 y K calibrado una sola vez
- **Decisión:** wm no se ajusta; K se calibra con los pesos iniciales y solo con entrenamiento
  (sección dorada sobre log K en [20; 5000], 30 evaluaciones de J) y queda fijo.
- **Alternativas:** dejar wm libre; reajustar K en cada paso.
- **Por qué:** con wm y K libres, multiplicar todos los pesos y K por la misma constante da el mismo
  J: la escala no está identificada. Fijar wm mantiene la unidad «centipeón».
- **Consecuencia:** K = 1789,5 cp. Es grande: con E = +900 (una dama) la probabilidad predicha
  es solo σ(0,50) ≈ 0,62. Así de débil es la relación entre ventaja y resultado en juego débil.

#### T-06 · Hill climbing por coordenadas con reducción de paso
- **Decisión:** vecinos `w_i ± paso_i` de cada peso libre (wp, wk, wa), pasos iniciales 8/8/2; se
  evalúan todos los vecinos y se acepta el mejor si mejora estrictamente; si ninguno mejora, los
  pasos se reducen a la mitad; se para al bajar de paso/64 o al agotar el presupuesto. Cotas:
  wp, wk ∈ [0; 100], wa ∈ [0; 30].
- **Alternativas:** primera mejora; gradiente numérico.
- **Por qué:** es el HC del Taller 2 con otra vecindad: el estado es un vector de pesos en vez de
  una ruta y el vecino cambia una coordenada en vez de invertir un tramo (2-opt). Con 3 pesos la
  vecindad completa cuesta ≤ 6 evaluaciones.
- **Consecuencia:** el presupuesto cuenta TODAS las evaluaciones de J, incluida la inicial; la
  prueba con un objetivo que cuenta sus llamadas lo verifica con presupuestos 1, 7, 60 y 500.
  Las cotas son una decisión previa: ningún término posicional vale más de un peón por unidad.

#### T-07 · Recocido simulado como segundo método, elección por entrenamiento
- **Decisión:** SA con semilla 2026: perturba un peso al azar con U(−paso, paso), Metropolis,
  enfriamiento geométrico hasta T0·10⁻³ al agotar 300 evaluaciones; T0 = −mediana(Δ>0)/ln(0,5)
  con 20 vecinos de calibración que SÍ cuentan en el presupuesto (como en el Taller 2). Regla fijada
  antes de mirar prueba: gana el de menor J de entrenamiento; empate → HC.
- **Por qué:** permite contrastar ambos métodos con el mismo presupuesto, y la regla impide elegir
  con datos de prueba.
- **Consecuencia:** HC llegó a J = 0,0444185 en 135 evaluaciones (óptimo local); SA a 0,0444185
  (ligeramente peor en el 9.º decimal) usando las 300. Ganó HC.

#### T-08 · Qué se reporta
- **Decisión:** J de entrenamiento y prueba antes/después, J de referencia (solo material y
  predicción constante), historial por evaluación (`tuning_historial.csv`), ablación por peso
  (devolver UN peso del ajustado al inicial) y una comparación pareada en prueba **agrupada por
  partida** (media de la diferencia de error y su error estándar entre partidas).
- **Por qué:** la partida es la unidad independiente (sus posiciones comparten etiqueta); tratar
  6690 posiciones como independientes exageraría la significancia.

#### T-09 · Resultado de la corrida real y lectura honesta
- **Datos:** 13 019 posiciones de entrenamiento (473 partidas terminadas) y 6690 de prueba (246).
- **Pesos:** (100, 15, 10, 4) → **(100, 100, 53,375, 0)**.
- **J:** entrenamiento 0,045206 → 0,044418 (−1,7 %); prueba 0,050634 → 0,049990 (−1,3 %).
  Referencias en prueba: solo material 0,051034; predicción constante 0,071802.
- **Ablación (J de prueba al devolver un peso a su valor inicial):** wp → 0,050788 (empeora: el
  aumento de wp generaliza); wk → 0,049955 y wa → 0,049944 (mejoran levemente: esos dos cambios
  NO generalizan).
- **Pareada por partida en prueba:** diferencia media −0,00028 con error estándar 0,00056 (240
  partidas con posiciones), y mejora en el 48,75 % de las partidas: la mejora no es significativa.
- **Lectura:** la mejora de prueba existe pero es pequeña y se debe casi toda a wp (los peones
  pasados deciden partidas de jugadores que no saben frenarlos). wa = 0 aunque A tiene correlación
  0,40 con el resultado: A es casi colineal con el material (más piezas → más casillas atacadas) y,
  dado el material, no aporta. wp quedó en su cota superior (100): la restricción está activa.
- **Qué NO hicimos:** cambiar los pesos a la variante «solo wp ajustado», aunque un cálculo
  posterior da J de prueba 0,049890 (menor que E*): elegirla mirando prueba sería usar prueba para
  ajustar. Queda como evidencia de sobreajuste leve de wk y wa (pregunta 9) y como mejora futura
  (separar una validación dentro de entrenamiento y decidirlo de antemano).

#### T-10 · `TUNED_WEIGHTS` sale del archivo, no del código
- **Decisión:** `TUNED_WEIGHTS = load_tuned_weights(missing_ok=True)` lee
  `resultados/pesos_ajustados.json` (None si no existe); `load_tuned_evaluator()` devuelve
  `Evaluator(pesos, "E*")`. La ruta es relativa al paquete si existe `__file__` y al directorio de
  trabajo si no (cuaderno).
- **Por qué:** los pesos los produce la corrida real; escribirlos a mano en el código ocultaría de
  dónde salen.
- **Consecuencia:** repetir `run_tuning(TuningConfig())` regenera exactamente los mismos pesos
  (verificado con una segunda corrida completa).

#### T-11 · Tiempo de pared vs CPU en el reporte
- **Qué pasó:** la primera corrida real registró `timing_s.data = 34 192 s` (9,5 h) para algo que
  cuesta poco más de un minuto: el equipo se suspendió durante la corrida y `perf_counter` midió el tiempo de
  pared, incluida la suspensión.
- **Decisión:** el JSON guarda ahora también `cpu_data` y `cpu_total` (`time.process_time()`), y se
  repitió la corrida: 78,3 s de pared y 76,7 s de CPU. Las posiciones (archivo idéntico byte a
  byte), los pesos y J coincidieron con la primera, lo que confirma la reproducibilidad.
- **Lección:** un tiempo de pared solo es evidencia si la máquina estuvo dedicada; para el costo
  real de cómputo se reporta CPU.

#### E-12 · Máscaras de peón pasado precalculadas (optimización sin cambio de valores)
- **Decisión:** `_PASSED_MASK[color][casilla]` se calcula una vez al importar (2 × 64 enteros)
  en vez de construir la máscara con bucles en cada llamada a E.
- **Alternativas:** dejar E como estaba; reescribir toda la estructura de peones con desplazamientos de bitboards.
- **Por qué:** el perfil del agente de búsqueda (S-13) mostró que esa construcción era la parte más
  cara de E, y E domina el costo de cada hoja en minimax y alfa-beta.
- **Verificación:** el vector de características es **idéntico** (comparación exacta, no aproximada)
  en 4000 posiciones del conjunto de ajuste antes y después del cambio, así que los pesos ajustados
  y todos los resultados previos siguen siendo válidos. Tiempo medido por llamada a `evaluate`
  (mejor de 3 sobre las mismas 4000 posiciones): **51.9 µs → 41.9 µs (−19 %)**. La ganancia es
  menor que la estimada en S-13 porque estas posiciones tienen pocos peones; en medio juego es mayor.

---

## Etapa 3 — Minimax, alfa-beta y alfa-beta mejorado (prefijo S-)

---

#### S-01 · MAX = blancas y MIN = negras, sobre valores desde blancas
- **Decisión:** minimax con dos ramas explícitas (`if board.turn == WHITE: max ... else: min ...`),
  tal como el pseudocódigo del enunciado. Todo valor del árbol (E y utilidades terminales) está
  desde blancas (D-06). Al final, `Decision.score = perspective_sign(turno_raíz) · valor_raíz`.
- **Alternativas:** (a) MAX = jugador de la raíz, con E multiplicada por el signo de ese jugador;
  (b) negamax (un solo `max` sobre `-valor`).
- **Por qué:** con MAX = blancas el mismo número significa lo mismo en cualquier nodo y en cualquier
  partida, lo que hace legible el registro de podas (pregunta 2) y coincide con D-06. Negamax es más
  corto pero esconde la alternancia MAX/MIN que piden el enunciado y la rúbrica.
- **Consecuencia:** cuando juegan negras la raíz es MIN: el agente minimiza E (= maximiza −E). Prueba
  `test_black_to_move_chooses_what_is_good_for_black` (negras capturan la dama colgada) y
  `test_mirrored_position_gets_same_score_for_the_side_to_move` (reflejar el tablero da el mismo score).

#### S-02 · Definiciones de nodo, hoja y poda (iguales en minimax y alfa-beta)
- **Decisión:** *nodo* = cada llamada recursiva sobre una posición, incluida la raíz, contada al
  entrar; *hoja* = nodo donde se devuelve utilidad terminal o se aplica E (profundidad 0);
  *poda* = **evento** de corte (`valor ≥ β` en MAX o `valor ≤ α` en MIN) con al menos un hermano sin
  explorar. Aparte se cuentan los hijos omitidos (`pruned_children`).
- **Alternativas:** contar solo hojas; contar como poda cada hijo omitido; contar un corte aunque no
  quede ningún hermano.
- **Por qué:** el enunciado exige no comparar «nodos» con definiciones distintas. Si el corte ocurre con
  el último hijo no se ahorra nada, así que no se cuenta como poda.
- **Consecuencia:** minimax a profundidad 2 desde la inicial da exactamente 1 + 20 + 400 = 421 nodos y
  400 hojas (`test_minimax_counts_every_node_of_the_full_tree`).

#### S-03 · Terminal en la raíz con la política de la partida; dentro del árbol, `search_outcome`
- **Decisión:** antes de buscar, el agente consulta `game_outcome` (reclamo automático, política de la
  partida). Si ya terminó devuelve `Decision(None, utilidad desde quien decide)`. Dentro del árbol usa
  `search_outcome` (D-08), siempre antes del corte de profundidad (D-07), con `MATE_SCORE − ply`.
- **Por qué:** `move=None` solo se permite si el estado YA es terminal según la política acordada.
- **Consecuencia:** en `checkmate` (juegan negras) el score es −100000 y en `stalemate` 0.

#### S-04 · Desempate: se conserva el primer mejor hijo
- **Decisión:** el mejor valor se reemplaza solo con `>` (MAX) o `<` (MIN).
- **Consecuencia (pregunta 3):** minimax en orden natural y alfa-beta ordenado pueden devolver jugadas
  distintas con el mismo valor. La prueba de equivalencia no solo compara valores con `==`: verifica
  que cada jugada devuelta alcanza exactamente el valor de la raíz (si difieren, es por empate).

#### S-05 · Alfa-beta «fail-soft» y ventana infinita en la raíz
- **Decisión:** cada nodo devuelve su mejor valor aunque salga de (α, β); en la raíz la ventana es
  (−∞, +∞), por lo que nunca hay corte en la raíz y su valor es exacto.
- **Consecuencia:** minimax, alfa-beta natural y alfa-beta ordenado dan **exactamente** el mismo número
  (comparado con `==`, no aproximado) en 13 posiciones × profundidades 1, 2 y 3. Es así porque las
  hojas, E y el orden de suma dentro de E son los mismos; solo cambia cuáles hojas se visitan.

#### S-06 · La jugada de la raíz sale de la variante principal (`pv[0][0]`)
- **Decisión:** cada nodo guarda su mejor línea en `ctx.pv[ply]` (tabla triangular); la jugada de la
  raíz es `pv[0][0]`. Así la raíz usa la misma función recursiva que el resto (sin código duplicado).
- **Consecuencia:** la PV completa sirve para ordenar la siguiente iteración (S-07) y para mostrarla.

#### S-07 · Ordenación: PV previa > promociones > capturas MVV-LVA > killers > resto
- **Decisión:** `_search_order_moves` puntúa cada jugada y hace un `sort` estable (dentro de cada grupo
  se conserva el orden de generación). Killers: dos jugadas tranquilas por ply que ya causaron un
  corte. El tiempo de ordenar se acumula aparte (`sort_time`).
- **Alternativas:** incluir jaques (`board.gives_check`), historia, ordenar la raíz por los valores
  de la iteración anterior.
- **Por qué:** MVV-LVA y killers son baratos; `gives_check` hace un push/pop por jugada y E ya es el
  cuello de botella. Ordenar cuesta 5–11 % del tiempo total a profundidad 3 (p. ej. 0.0108 s de
  0.157 s en la inicial) y deja entre 32 % y 62 % menos nodos que el alfa-beta natural (inicial
  1 538 → 841; italiana 4 294 → 1 643; piezas menores 1 468 → 995; final de torres 1 430 → 743).
- **Consecuencia:** `AlphaBetaAgent(ordering=True)` es el «alfa-beta ordenado» de profundidad fija del
  Experimento 1 (sin PV previa); el mejorado usa además la PV de la iteración anterior.

#### S-08 · Profundización iterativa: dónde se mira el plazo y qué se devuelve
- **Decisión:** `Deadline(time_limit_s)` se consulta al **entrar a cada nodo** (antes de mirar si es
  terminal) y antes de empezar cada iteración. Antes de iterar se guarda una jugada de respaldo (la
  primera según la ordenación). Una iteración solo reemplaza (jugada, valor, `completed_depth`) si
  termina; si salta `SearchTimeout`, los `finally` deshacen todos los `push` y se conserva la última
  iteración completa. Si el valor es de mate se para (más profundidad no lo cambia).
- **Alternativas:** mirar el plazo solo en la raíz (podría pasarse mucho); mirar cada N nodos (menos
  llamadas a `perf_counter`, pero con nodos de ~200 µs el costo de mirar siempre es despreciable);
  predecir si la siguiente iteración cabe.
- **Consecuencia (pregunta 5):** si vence el plazo durante la iteración d se devuelve la jugada y el
  valor de la iteración d−1 con `completed_depth = d−1`; si ni la profundidad 1 terminó, la jugada de
  respaldo con `score=None` y `completed_depth=0`. Ejemplo real (inicial, 0.2 s): iteraciones 1, 2 y 3
  completas (21, 68 y 543 nodos), la 4 abortada tras 596 nodos → devuelve e3 con valor +62 y
  `completed_depth=3`. `stats.nodes` suma todas las iteraciones, incluida la abortada (trabajo real).

#### S-09 · Los agentes de profundidad fija ignoran `time_limit_s`
- **Decisión:** `MinimaxAgent` y `AlphaBetaAgent` recorren siempre el árbol completo de su profundidad.
- **Por qué:** su objeto de estudio es el árbol fijo (Experimento 1). El enunciado pide registrar el
  exceso y aplicar una política uniforme: eso lo hace el controlador con `elapsed_s` (D-10).
- **Consecuencia:** hay que elegir su profundidad para el torneo con las mediciones de S-12.

#### S-10 · Registro de podas activable (`log_prunes=True`)
- **Decisión:** cada poda guarda un `PruneEvent`: tipo de nodo, ruta SAN desde la raíz, FEN, α y β del
  nodo en el momento del corte, hijos explorados con su valor, jugada causante y hermanos podados.
  `format_prune_event` lo imprime. Apagado por defecto (calcular SAN cuesta).
- **Consecuencia:** el ejemplo trazado a mano de `05b_busqueda.md` sale de este registro. La prueba
  `test_prune_log_events_are_valid_cutoffs` comprueba que cada evento cumple su condición de corte, que
  hay un evento por cada `cutoff` y que activar el registro no cambia valor, jugada ni nodos.

#### S-11 · Quietud: opción apagada, no es la mejora oficial
- **Decisión:** `AlphaBetaImprovedAgent(quiescence=True)` extiende las hojas con capturas y promociones
  (stand pat = E). Por defecto `False`. La mejora oficial del grupo es el ajuste de pesos (prefijo T-).
- **Consecuencia:** con quietud el árbol ya no es el de profundidad fija: sus valores no se comparan con
  minimax. Medición real (posición `knight_capture`, profundidad 2): sin quietud elige Cxc6 (−107.5, 89
  nodos); con quietud elige Cf5 (−102.5, 95 nodos). Cada nodo de quietud cuenta como nodo y como hoja.

#### S-12 · Rendimiento y profundidad alcanzable en ~0.2 s (dato para el torneo)
E(s) cuesta ~165–205 µs por llamada y casi todos los nodos son hojas, así que la búsqueda corre a
**~4 500–6 000 nodos/s** en medio juego y ~8 000–10 000 en finales de torres.

| Posición | Minimax d=2 | Minimax d=3 | AB natural d=2 | AB natural d=3 | AB ordenado d=3 | Mejorado 0.2 s |
|---|---|---|---|---|---|---|
| Inicial | 0.082 s · 421 n | 1.90 s · 9 323 n | 0.027 s · 155 n | 0.313 s · 1 538 n | 0.157 s · 841 n | prof. 3 (5/5) |
| Italiana (medio juego) | 0.231 s · 1 184 n | (no medido: >15 s) | 0.166 s · 812 n | 0.954 s · 4 294 n | 0.356 s · 1 643 n | prof. 2 (5/5) |
| Piezas menores | 0.107 s · 650 n | 2.74 s · 15 849 n | 0.014 s · 85 n | 0.240 s · 1 468 n | 0.165 s · 995 n | prof. 2 (5/5) |
| Final de torres | 0.033 s · 358 n | 0.78 s · 6 190 n | 0.009 s · 81 n | 0.191 s · 1 430 n | 0.085 s · 743 n | prof. 3 (5/5) |

- **Recomendación para el torneo (0.2 s):** Minimax a profundidad **2** (en medio juego cargado puede
  pasar un poco: 0.231 s en la italiana; el controlador registrará `time_exceeded`); Alfa-beta a
  profundidad **2** (la 3 tarda 0.19–0.95 s); Alfa-beta mejorado con `time_limit_s=0.2` completa 2–3.
  El mejorado respeta el plazo con un exceso de ~1–3 ms (máximo medido 0.203 s).

#### S-13 · Propuesta (no aplicada: `evaluation.py` no es de este módulo) para acelerar E
- `_pawn_structure` cuesta ~44 µs por color (~88 de ~165 µs de E): construye la máscara de «peón
  pasado» con bucles anidados en cada llamada. Precomputar `PASSED_MASK[color][casilla]` (128
  bitboards) la dejaría en pocos µs y casi duplicaría los nodos/s.
- `search_outcome` genera las jugadas legales y luego el nodo las genera otra vez (~40–70 µs). Se podría
  reutilizar la lista, pero se mantuvo `search_outcome` por ser la política común (D-08).

#### S-14 · Ejemplo de la pregunta 1: `MINIMAX_DEFENSE_FEN`
- `4r1k1/ppp2pp1/8/4p2p/3N4/8/PPP2PPP/3Q2K1 w - - 0 1`: el peón e5 ataca al caballo d4 y el peón h5
  está sin defensa. Minimax de profundidad 1 (= voraz) juega Dxh5 (+786.7); a profundidad 2 ve que
  Dxh5 exd4 vale +432.8 y elige Cf5 (+673.4), poniendo el caballo a salvo. Además se cruzó con
  `GREEDY_TRAP_FEN` del módulo voraz: `MinimaxAgent(depth=1)` da la misma jugada y el mismo score que
  `GreedyAgent` (Dxb7, +430.2) y la profundidad 2 la evita (Db4, +323.7).

#### S-15 · Posiciones propias de prueba (sección 8)
- **Mate en dos** `k7/8/2K5/8/8/8/8/7R w`: profundidad 2 no ve mate; profundidad 3 da exactamente
  `MATE_SCORE − 3` y tras la jugada elegida toda defensa permite mate inmediato.
- **Pieza «colgada» defendida** `6k1/pp3ppp/4p3/3n4/8/8/PP3PPP/3Q2K1 w`: el voraz toma Dxd5 (+3.2) y
  pierde la dama tras exd5; minimax de profundidad 2 no la toma.
- **Evasión** `k3r3/8/8/7Q/8/8/8/4K3 w`: en jaque, la mejor evasión es capturar la torre (Dxe8+).
- **Perspectiva** `7k/7p/8/8/Q7/2n5/7P/4K3 b`: negras capturan la dama (Cxa4).

---

#### S-16 · ERROR CORREGIDO — la posición de perspectiva daba tablas, no ventaja de negras
- **Qué pasó:** la primera versión de la posición de perspectiva era `7k/8/8/8/Q7/2n5/8/4K3 b`
  (negras capturan una dama con el caballo). Minimax daba Cxa4 pero con valor **−0.0** a toda
  profundidad: la prueba de «negras eligen lo bueno para negras» no tenía con qué discriminar.
- **Diagnóstico:** tras Cxa4 queda rey y caballo contra rey: `search_outcome` lo declara material
  insuficiente (tablas, 0) **antes** de consultar E, como manda D-07. El programa tenía razón.
- **Corrección:** se añadieron peones (h7 y h2): `7k/7p/8/8/Q7/2n5/7P/4K3 b`. Ahora Cxa4 vale +336.5
  desde negras.
- **Lección:** los terminales se resuelven antes que E también en las posiciones de prueba; una
  posición de prueba debe verificarse con el propio programa antes de fijar la expectativa.

#### S-17 · ERROR CORREGIDO — expectativa de score mal calculada y prueba dependiente del reloj
- **Qué pasó:** `test_black_to_move_chooses_what_is_good_for_black` fallaba con `assert 336.5 > 500`.
  Otro agente la vio fallar una vez en una corrida completa y pasar al repetirla.
- **Diagnóstico:** (1) confundimos «lo que gana la jugada» (una dama, 9) con el valor de la posición
  resultante: antes de capturar, blancas tenían 5.8 peones de ventaja, así que tras Cxa4 negras quedan
  solo +3.2 (≈ +336 cp). El agente estaba bien; la expectativa no. (2) Además, las pruebas de
  comportamiento llamaban al mejorado con `time_limit_s=0.2`: su profundidad, y por tanto su jugada,
  podía depender de la carga de la máquina.
- **Corrección:** umbral `> 200` con la explicación en el comentario; todas las pruebas de
  comportamiento usan `time_limit_s=0` (sin plazo) y el mejorado con `max_depth=2`, de modo que el
  resultado no depende de la velocidad. Las pruebas de plazo solo afirman invariantes (jugada legal,
  tablero intacto, `completed_depth` coherente con las iteraciones). Verificado: 3 corridas seguidas y 4
  en paralelo (máquina cargada), 76/76 cada una.
- **Lección:** `Decision.score` es el valor de la posición, no la ganancia de la jugada; y una prueba
  con plazo de reloj no debe afirmar nada que dependa de cuánto alcanzó a buscar.

#### S-18 · ERROR CORREGIDO — doble conteo del nodo de entrada en la quietud (detectado en revisión)
- **Qué pasó:** la primera versión de `_search_quiescence` contaba el nodo «si `ply > 0`», pensando en
  la raíz. Pero la quietud se llama desde una hoja de alfa-beta (que ya contó el nodo y ya miró si era
  terminal), y esa hoja nunca está en `ply` 0: el nodo frontera se contaba dos veces y se miraba dos
  veces si era terminal.
- **Diagnóstico:** revisando el código contra la definición de S-02 antes de ejecutarlo.
- **Corrección:** parámetro `entry=True` en la llamada desde alfa-beta; solo las llamadas recursivas de
  quietud cuentan nodo y miran terminal.
- **Lección:** el conteo de nodos es parte del contrato del experimento; cada función que cuente nodos
  debe revisarse contra la definición escrita.

---

## Etapa 4 — Integración: torre, búsqueda informada, AND-OR, expectiminimax (prefijo I-)

---

### Apartado A: torre y búsqueda no informada

#### I-01 · La torre se programa desde cero, con reglas simplificadas explícitas
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

#### I-02 · Orden fijo de acciones: N, E, S, O y k creciente
- **Decisión:** las acciones se generan en el orden N, E, S, O (el mismo del Taller 1, D-14) y,
  dentro de cada dirección, con k creciente. `long_moves_first=True` invierte el orden de k.
- **Alternativas:** k decreciente por omisión (DFS hallaría a1→a8→h8 de inmediato).
- **Por qué:** el orden no cambia el costo óptimo de BFS, UCS ni A*, pero sí la ruta de DFS y los
  desempates. Dejamos el orden «natural» como base y medimos cuánto cambia DFS con otros órdenes.
- **Consecuencia (medido):** con N,E,S,O y k creciente DFS devuelve una escalera de 14
  movimientos (a1→a2→b2→…→g8→h8). Con k decreciente devuelve a1→a8→h8 (2 movimientos, 2
  expandidos). Con E,N,O,S devuelve otra escalera de 14 movimientos. El óptimo (2) no cambia
  (`test_dfs_route_depends_on_action_order`).

#### I-03 · Mismas convenciones de métricas que el Taller 1
- **Decisión:** la prueba de objetivo se hace al **extraer**. BFS y DFS marcan al **generar**.
  «Expandido» significa que se generaron sus sucesores, así que el objetivo extraído no cuenta.
  «Generado» es todo sucesor construido, incluidos los repetidos descartados; la raíz no cuenta.
  La frontera máxima incluye las entradas obsoletas del montículo.
- **Alternativas:** probar el objetivo al generar en BFS (ahorra un nivel).
- **Por qué:** son las convenciones de D-19/D-20 del Taller 1. Así las cifras se pueden comparar
  con las de aquel taller y entre los cinco algoritmos.
- **Consecuencia:** BFS expande 63 de 64 casillas en a1→h8, aunque la meta esté a profundidad 2.
  Todas las casillas están a lo sumo a 2 movimientos y h8 sale de la cola de última.

#### I-04 · Un solo núcleo primero-el-mejor para UCS, A* y voraz
- **Decisión:** `_rook_best_first` implementa BEST-FIRST-SEARCH con `best_g` y eliminación
  perezosa. Las prioridades son: UCS `(g, orden)`, A* `(g+h, h, orden)` y voraz `(h, orden)`.
- **Alternativas:** tres funciones separadas.
- **Por qué:** igual que la frontera inyectada del Taller 1 (D-17), la diferencia entre los tres
  algoritmos queda en una sola línea, la prioridad, y el resto (repetidos, métricas) es común. El
  desempate `(f, h, orden)` es el de A-04 del Taller 2.
- **Consecuencia:** con costo unitario y desempate FIFO, UCS expande exactamente en el mismo
  orden que BFS en los tres escenarios. Es la predicción D-22 del Taller 1, comprobada de nuevo
  (`test_ucs_unit_reproduces_bfs_expansion_order`).

#### I-05 · Escenario con obstáculos donde longitud ≠ costo, hallado por muestreo
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

#### I-06 · HALLAZGO: con costo por distancia, UCS expande más que BFS
- En d4→h8, BFS expande 39 nodos y UCS con costo por distancia expande 63. El costo óptimo es 8 y
  casi todas las casillas del tablero están a distancia (Manhattan) ≤ 8 de d4. UCS tiene que
  sacar de la cola todas las de costo < 8 y, por los empates, muchas de costo 8 antes que h8. Más
  costo no implica más trabajo para BFS, porque BFS solo mira los movimientos.

---

### Apartado B: búsqueda informada

#### I-07 · Admisibilidad verificada exhaustivamente con un oráculo independiente
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

#### I-08 · Contraejemplo: Manhattan con costo unitario hace que A* no sea óptimo
- **Decisión:** `rook_unit_manhattan_counterexample` recorre en orden fijo muros horizontales con
  un hueco y devuelve el primero donde A*(Manhattan) da más movimientos que BFS.
- **Resultado:** muro en la fila 3 con hueco en b3. BFS da a1→b1→b8→h8 (3 movimientos);
  A*(Manhattan) da a1→a2→b2→b8→h8 (4 movimientos). A* con la h de la consigna da 3. Mostrar que
  h(a1)=14 > h*(a1)=2 no basta: hace falta ver que la sobreestimación cambia la respuesta.
  Esto también lo aprendimos en el Taller 1, D-39.

#### I-09 · Voraz: rápido, pero no óptimo en costo
- En el escenario con obstáculos y costo por distancia, el voraz con Manhattan expande 6 nodos y
  devuelve una ruta de 16 casillas, mientras que el óptimo es 14
  (`test_greedy_is_not_optimal_in_distance_cost_with_obstacles`). En el tablero vacío coincide
  con A*, porque la heurística ya lleva directo a la meta.

---

### Apartado D: incertidumbre

#### I-10 · El plan AND-OR es un diccionario anidado `{jugada: {respuesta: subplan}}`
- **Decisión:** un nodo OR del plan tiene exactamente una jugada del atacante. Su valor es un nodo
  AND con **todas** las respuestas legales del defensor. Una hoja de mate es `{jugada: {}}`.
- **Alternativas:** la lista con `if-then-else` de AIMA; clases propias.
- **Por qué:** se puede imprimir y verificar con un recorrido simple, y la condición «cubre todas
  las defensas» queda como `set(sub) == set(board.legal_moves)`.
- **Consecuencia:** `verify_mate_plan` recorre el plan con las reglas de python-chess, sin usar el
  buscador, y rechaza las secuencias lineales («defensas sin cubrir: a5a4, h6h5») y los planes
  que repiten la misma jugada contra todas las defensas.

#### I-11 · Un nodo AND sin respuestas NO es éxito si no hay mate (desviación de AIMA)
- **Decisión:** el éxito solo se declara cuando la jugada del atacante da **jaque mate**. Si el
  defensor queda sin jugadas y no está en jaque (ahogado), o si se llega a tablas, es fracaso
  (`failures_by_draw`).
- **Alternativas:** el AND-SEARCH literal de AIMA, que con un conjunto vacío de estados devuelve
  el plan vacío, es decir, éxito.
- **Por qué:** aplicado sin más, AIMA contaría el ahogado como un «objetivo». En
  `7k/8/8/6K1/8/8/8/5Q2 w` la jugada 1.Qf7 ahoga. Nuestra búsqueda la registra como fracaso y
  no devuelve ningún plan de 1 jugada (`test_stalemate_is_not_success`).

#### I-12 · Jaques y capturas primero en los nodos OR
- **Decisión:** las jugadas del atacante se ordenan con los jaques primero, luego las capturas y
  luego el UCI.
- **Por qué:** el orden no cambia si existe un plan, solo cuánto se explora hasta hallarlo. Es la
  misma idea que ordenar jugadas en alfa-beta (apartado B). Sirve de puente entre los dos
  apartados.

#### I-13 · ERROR CORREGIDO: la búsqueda devolvía un plan, pero no el más corto
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

#### I-14 · ERROR CORREGIDO: la primera posición de «mate del pasillo» no era mate en 2
- **Qué pasó:** escribimos `2r3k1/5ppp/8/8/8/8/5PPP/3RR1K1 w` (torres en d1 y e1) creyendo que
  1.Re8+ Rxe8 2.Rxe8# era mate en 2. `and_or_mate_search(…, 2)` devolvió fracaso (29 nodos OR,
  26 AND).
- **Diagnóstico:** tras 1.Re8+ Rxe8, la torre que queda está en d1 y no llega a e8. Para
  recapturar en la misma columna, las torres tienen que estar dobladas.
- **Corrección:** `2r3k1/5ppp/8/8/8/8/3R1PPP/3R2K1 w` (torres en d1 y d2): 1.Rd8+ Rxd8 2.Rxd8#.
  La búsqueda lo confirma y también confirma que no hay mate en 1.
- **Lección:** una posición «conocida» copiada de memoria también hay que verificarla. Aquí fue
  el propio buscador AND-OR el que detectó el error de la posición.

#### I-15 · Mate en 2 con jugada tranquila y respuestas distintas por defensa
- **Decisión:** además del pasillo (1 sola defensa), usamos `8/4K3/7k/p7/8/8/6Q1/8 w`: 1.Kf6 y
  luego Kh5 Qg5#, Kh7 Qg7#, a4 Qg6#.
- **Por qué:** el pasillo no muestra la ramificación AND. Buscamos posiciones K+D contra R+P con
  un generador aleatorio de posiciones (no fijamos la semilla en un archivo, así que la búsqueda
  no es reproducible). Elegimos esta porque cada defensa exige un mate distinto. La posición está
  fija en el código y se verifica en las pruebas: el plan cubre las 3 defensas, termina en mate
  en cada hoja y no existe mate en 1.

#### I-16 · Minimax sobre el árbol con azar = el azar como adversario
- **Decisión:** `worst_case_minimax` trata los nodos de azar como nodos MIN (peor caso).
  `expectiminimax` calcula la esperanza.
- **Alternativas:** minimax que asume el resultado más probable; eliminar los nodos de azar.
- **Por qué:** es lo que haría nuestro agente minimax si nadie le dijera que el azar no es un
  rival. Así queda claro el contraste entre una garantía (peor caso) y el promedio.
- **Consecuencia:** en el árbol «segura/arriesgada», expectiminimax elige la arriesgada (3.5
  contra 2.75) y minimax la segura (2 contra −4).

#### I-17 · Transformación monótona no lineal u → 4^u
- **Decisión:** en el árbol de escala aplicamos u → 4^u. Es creciente, así que conserva el orden
  de las hojas (lo verifica la prueba).
- **Consecuencia:** expectiminimax cambia de a1 (2.1 contra 1.3) a a2 (20.8 contra 29.2), y
  minimax sigue en a1 (2 contra 1; 16 contra 4). Es AIMA 5.5: con azar, las utilidades tienen
  que ser una **escala** con significado (utilidad esperada), no solo un orden.

#### I-18 · Estado de creencia de Kriegspiel como conjunto de tableros
- **Decisión:** el estado de creencia es un diccionario `{epd: tablero}`. El árbitro anuncia
  `(casilla de captura o None, da jaque)` de cada jugada rival. Nuestros intentos de jugada parten
  el estado de creencia en «legal» e «ilegal».
- **Simplificación declarada:** el árbitro real también anuncia la dirección del jaque y los
  intentos ilegales del rival. No los modelamos.
- **Consecuencia (medido, desde la posición inicial):** 1 mundo → tras 1.e4 y una respuesta no
  observada, 20 → tras 2.Nf3 y otra respuesta no observada, 266. Si blancas intentan e4–e5 después
  de 1.e4, el árbitro dice «ilegal» en 1 mundo (…e5) y «legal» en 19.

---

## Etapa 5 — MCTS-UCT (prefijo M-)

---

#### M-01 · W de cada nodo desde el jugador que movió para llegar a él
- **Decisión:** `_MCTSNode.wins` acumula la recompensa desde `node.mover` (el color que jugó
  `node.move`). La retropropagación calcula una sola recompensa desde blancas y cada nodo suma
  `_reward_for(mover, r)`: `r` si `mover` es blanco, `1 − r` si es negro.
- **Alternativas:** (a) guardar W desde blancas y alternar max/min en la selección; (b) guardar W
  desde el jugador raíz; (c) negar la recompensa en cada nivel.
- **Por qué:** con esta convención UCT es siempre un `argmax` y, en cada nodo, maximiza para el
  jugador al turno en ese nodo (los hijos son sus jugadas). No hay signos que alternar en la
  selección; la perspectiva vive en un único método (`_reward_for`) y se puede probar aislada.
- **Consecuencia:** el valor medio de un hijo de la raíz es directamente la probabilidad estimada de
  ganar del jugador raíz. Responde la pregunta 6 (ver M-07).

#### M-02 · Recompensa en [0, 1]; rollout truncado = sigmoide(E/400), contado como truncado
- **Decisión:** terminal (vía `search_outcome`): 1 / 0.5 / 0 desde blancas. Rollout que alcanza
  `rollout_limit` sin terminar: `1/(1+e^(−E/400))`, con E la evaluación común desde blancas. Se cuenta
  en `last_info["truncated_rollouts"]`; los que terminan, en `terminal_rollouts`.
- **Alternativas:** puntuar el truncado como tablas (0.5); escala 200 cp o 800 cp; escala Elo `10^(E/400)`.
- **Por qué:** 0.5 descartaría la información de E y confundiría «no sé» con «tablas» (lo prohíbe el
  enunciado). Con 400 cp: +1 peón → 0.56, +caballo → 0.69, +dama → 0.905; una ventaja enorme sigue
  siendo menor que una victoria real (1.0). La forma natural (base e) tiene inversa exacta, que se usa
  para `Decision.score` (M-06).
- **Consecuencia:** prueba `test_truncated_rollout_is_counted_as_truncated_not_draw` (30 de 30 rollouts
  de 2 plies desde la posición inicial son truncados, ninguno terminal).

#### M-03 · Constante de exploración c = √2
- **Decisión:** `exploration=math.sqrt(2)` por defecto.
- **Alternativas:** ajustar c con las tácticas del benchmark.
- **Por qué:** es la constante de UCB1 para recompensas en [0, 1] (Kocsis y Szepesvári, 2006). Ajustarla
  con las mismas 10 tácticas con las que medimos sería sobreajustar el experimento.
- **Consecuencia:** es un parámetro para modificar en vivo (ver `estudio/M_teoria.md`). M-07 muestra su
  costo: con c = √2 y ~40 respuestas, la refutación se visita poco.

#### M-04 · Rollout: sesgo a capturas, límite de 4 plies (decidido por medición)
- **Decisión:** `rollout_policy="captures"` (con probabilidad 0.75 se elige al azar entre las capturas
  si existen; si no, uniforme) y `rollout_limit=4`. También se ofrecen `"uniform"` y `rollout_limit=0`
  (sin rollout: la hoja se puntúa con la sigmoide de E).
- **Alternativas medidas** (10 tácticas × 5 semillas, 200 simulaciones, tasa de acierto):
  uniforme L0 0.80 · capturas L2 0.80 · uniforme L2 0.70 · capturas L4 0.80 · uniforme L4 0.76.
  Antes, con las 8 primeras tácticas y 50/200/800 simulaciones: uniforme L0 1.00/1.00/1.00,
  uniforme L8 0.825/0.95/0.90, uniforme L20 0.625/0.80/0.85, capturas L8 0.675/0.80/1.00.
- **Por qué:** los rollouts aleatorios largos meten ruido (la partida al azar pierde material sin
  sentido) y cuestan tiempo; el sesgo a capturas hace que las piezas colgadas se cobren dentro del
  rollout, así E al final refleja mejor el material «real». Con L4 + capturas se conserva un rollout
  de verdad (lo pide el enunciado).
- **Consecuencia (benchmark final, `resultados/mcts_tacticas.csv`):** con 200, 800 y 2000 simulaciones
  `captures_L4` y `eval_L0` aciertan lo mismo (0.80); con 50, `eval_L0` acierta más (0.80 frente a 0.70) y
  es entre 1.6× (tiempos del benchmark) y 2× (medición de simulaciones/s) más rápido. Es decir, en ESTAS tácticas el rollout no aporta sobre evaluar la
  hoja con E; lo conservamos por defecto porque el enunciado pide rollout, y dejamos `rollout_limit=0`
  como opción medida (el torneo puede usarla si lo justifica). `uniform_L8` es la peor: 0.66–0.80 y
  ~2–3× más lenta. Ver también el ERROR CORREGIDO M-E1.

#### M-05 · Jugada final: más visitas; desempate por valor medio y luego menor UCI
- **Alternativas:** mayor valor medio; «robust-max» (visitas y valor a la vez).
- **Por qué:** el promedio de un hijo con pocas visitas es poco fiable; las visitas resumen lo que UCT
  aprendió. El desempate en dos niveles hace la decisión determinista.
- **Consecuencia:** `last_info["root_visits"]` permite ver la distribución de visitas que justificó la jugada.

#### M-06 · `Decision.score` en centipeones desde el jugador raíz (logit inverso)
- **Decisión:** `score = 400 · ln(q/(1−q))`, q = valor medio del hijo elegido (recortado a ±EVAL_BOUND,
  con q limitado a [1e−6, 1 − 1e−6]). Si el hijo elegido es terminal se reporta su valor exacto:
  `MATE_SCORE − 1` si gana el jugador raíz (mate inmediato), 0 si es tablas. q queda en
  `last_info["win_probability"]`.
- **Alternativas:** reportar q directamente (escala distinta a la de los demás agentes).
- **Por qué:** el controlador y el CSV comparan `score` entre agentes; en centipeones la escala coincide
  con minimax/alfa-beta. Ver ERROR CORREGIDO M-E3.

#### M-07 · Prueba de perspectiva y un hallazgo: «todo desde la raíz» no se nota con ≤ 800 simulaciones
- **Decisión:** la prueba de la pregunta 6 compara el agente con una subclase defectuosa que guarda W
  siempre desde blancas (`_WhitePerspectiveMCTS`). Con negras al turno, en T3 (mate Ta1#) y T6 (capturar
  la dama colgada) el agente correcto acierta y el defectuoso falla, con las mismas 3 semillas. Otra
  prueba recorre el árbol y verifica que cada hijo pertenece al jugador al turno en el padre y que el
  hijo a8a1 de T3 tiene valor medio 1.0 desde negras.
- **Alternativa probada:** subclase «todo desde el jugador raíz» (supone que el rival colabora).
- **Hallazgo:** en las 10 tácticas con 400 simulaciones y en dos posiciones «cebo» con 200/400/800
  simulaciones, esa variante eligió **exactamente las mismas jugadas** que el agente correcto. Diagnóstico:
  con ~30 jugadas en la raíz y ~30–47 respuestas por hijo, casi ningún hijo de la raíz llega a tener
  todas sus respuestas expandidas, y UCT solo *selecciona* entre hijos de un nodo totalmente expandido;
  así que los valores de los nietos nunca deciden nada. Inspeccionando el árbol en la posición cebo
  `r1bqkbnr/pppp1ppp/2n5/4p2Q/2BNP3/8/PPPP1PPP/RNB1K2R b` (negras pueden capturar en d4 pero
  Dxf7# sigue amenazado): con 3000 simulaciones c6d4 tenía 264 visitas y la respuesta Dxf7# (valor 1.0
  para blancas) solo 21; con 10000, 137 de 719. UCT promedia: la refutación pesa poco frente a ~40
  respuestas que no lo son, y el agente siguió eligiendo c6d4 hasta 3000 simulaciones (con 10000 eligió
  e5d4, otra captura que tampoco evita el mate).
- **Consecuencia:** un acierto en el benchmark no prueba que la perspectiva esté bien; por eso la prueba
  usa una variante que falla de forma determinista. El límite de MCTS ante amenazas de mate con mucha
  ramificación queda documentado (también explica T9/T10, mates en dos).

#### M-08 · Restaurar el tablero con push/pop contados (`finally`)
- **Decisión:** cada simulación cuenta sus `push` (selección, expansión y rollout) y los deshace en un
  `finally`. Opción `restore="copy"` trabaja sobre `board.copy(stack=True)` por simulación.
- **Medición** (1000 simulaciones, 3 semillas, simulaciones/s medias): posición inicial push/pop 3220 vs
  copia 3114; medio juego de 14 plies 1752 vs 1737. Diferencia ≤ 3 %, dentro del ruido.
- **Por qué push/pop:** es igual o algo más rápido y no crece con la longitud de la historia; la copia
  copia la pila entera en cada simulación (más cara en partidas largas). Con `finally` el invariante
  se mantiene aunque haya excepción (prueba con un evaluador que lanza error a mitad de un rollout).

#### M-09 · Presupuesto: simulaciones fijas (reproducible) o plazo (dependiente de la máquina)
- **Decisión:** `simulations=N` ignora el plazo (N exactas, mismo árbol con la misma semilla);
  `simulations=None` usa `Deadline(time_limit_s)` y se revisa antes de cada simulación; sin ninguno de
  los dos se usan 200 simulaciones. Si el plazo vence antes de la primera simulación se devuelve la
  siguiente jugada del orden barajado (legal) con E como puntaje.
- **Alternativas:** cortar también las simulaciones fijas al vencer el plazo.
- **Por qué:** el enunciado pide simulaciones fijas para reproducibilidad exacta; un plazo depende de la
  máquina. Igual que en D-10, el exceso de un presupuesto fijo lo mide y registra el controlador.
- **Consecuencia:** en el torneo (plazo 0.2 s) MCTS no es reproducible jugada a jugada: con la misma
  semilla hizo entre 339 y 510 simulaciones en la posición inicial (10 corridas).

#### M-10 · Orden de expansión: UCI ordenado y barajado con la semilla
- **Decisión:** las jugadas no expandidas se ordenan por UCI (independiente de cómo las genere
  python-chess) y luego se barajan con `random.Random(seed)`; se expande sacándolas del final.
- **Por qué:** sin barajar, las primeras expansiones serían siempre las mismas (sesgo por orden alfabético);
  con la semilla, el resultado sigue siendo reproducible. Prueba: misma semilla → mismas visitas;
  otra semilla → visitas distintas.

#### M-11 · Terminales detectados una vez por nodo
- **Decisión:** al crear un nodo se llama a `search_outcome`; si es terminal se guarda la recompensa en
  `node.terminal` y no se generan jugadas. Las visitas posteriores reutilizan ese valor sin rollout
  (se cuentan como `terminal_rollouts`).
- **Consecuencia:** un mate en uno, una vez expandido, devuelve 1 en cada visita y acapara las visitas
  (prueba `test_mate_in_one_with_enough_budget`, 200 simulaciones, 3 semillas).

#### M-12 · Conjunto de tácticas verificado por reglas (Experimento 4)
- **Decisión:** `MCTS_TACTICS` tiene 10 posiciones (blancas y negras al turno): 4 mates en uno, 2 damas
  colgadas, 2 «evitar mate en uno» (8 de 28 jugadas correctas en cada una) y 2 mates en dos con
  sacrificio de torre. El conjunto correcto se recalcula con las reglas de python-chess
  (`mcts_tactic_solutions`: dar mate, capturar la dama, no permitir mate en uno, o forzar mate en la
  siguiente jugada contra toda respuesta) y una prueba exige que coincida con el declarado.
- **Por qué:** «no asumir una única mejor jugada» (sección 8): en «evitar mate» hay 8 defensas válidas y
  todas cuentan.

---

### Errores corregidos

#### M-E1 · ERROR CORREGIDO — el rollout aleatorio de 8 plies empeoraba la táctica
- **Qué pasó:** la primera versión usaba `rollout_limit=8` por defecto. En la primera corrida del
  benchmark (8 tácticas, 5 semillas) la configuración uniforme L8 acertó 0.825 / 0.95 / **0.90** con
  50 / 200 / 800 simulaciones, mientras que puntuar la hoja directamente con E (L0) acertó 1.00 en los
  tres presupuestos. Los fallos se concentraban en «evitar mate» (T7: 2 de 5 semillas con 800).
- **Diagnóstico:** 8 jugadas al azar cambian el material de forma arbitraria; la señal de la jugada
  candidata se pierde en el ruido, y además cada simulación cuesta ~2× más que con L4.
- **Corrección:** sesgo a capturas y límite 4 (M-04); medido de nuevo: 0.80 a 200 simulaciones, igual que
  L0 sobre las 10 tácticas (con 50 simulaciones L0 sigue siendo mejor: 0.80 frente a 0.70).
- **Lección:** «más rollout» no es «mejor rollout»; la política y el límite se eligen midiendo.

#### M-E2 · ERROR CORREGIDO — una prueba de perspectiva que pasaba por suerte
- **Qué pasó:** la prueba de la pregunta 6 incluía T7 (negras deben evitar Dxf7#) y esperaba que la
  variante defectuosa fallara. Con el rollout por defecto (capturas, L4) la variante defectuosa eligió
  d8h4, que es una de las 8 defensas válidas: la prueba falló.
- **Diagnóstico:** con 8 respuestas correctas de 28, un agente equivocado acierta con probabilidad
  apreciable. En una exploración previa la variante defectuosa incluso acertó 5/5 en T10 (mate en dos de
  negras) mientras el agente correcto acertaba 0/5: el sacrificio d6d1 «parece bueno para blancas».
- **Corrección:** la prueba usa solo T3 y T6 (una única solución, el defecto falla con las 3 semillas) y
  se añadió una prueba estructural que recorre el árbol y verifica el dueño de cada nodo.
- **Lección:** un acierto aislado no demuestra corrección; la prueba debe fallar de forma determinista
  cuando el defecto existe.

#### M-E3 · ERROR CORREGIDO — el mate inmediato se reportaba como +5526 cp
- **Qué pasó:** con el logit inverso, un hijo con q = 1.0 (mate en uno) daba
  `400·ln((1−1e−6)/1e−6) ≈ 5526` cp: menos que EVAL_BOUND y muy por debajo de `MATE_SCORE`, mientras los
  agentes de minimax reportan `MATE_SCORE − 1` para la misma jugada. Se detectó al escribir la prueba de
  mate en uno (¿qué `score` esperar?), cuando ya estaba corriendo la primera versión del benchmark.
- **Diagnóstico:** la sigmoide nunca llega a 1, así que su inversa no puede representar una victoria
  demostrada.
- **Corrección:** si el hijo elegido es terminal, `score` usa el valor exacto de la escala común
  (M-06). La prueba de legalidad, que exigía `|score| ≤ EVAL_BOUND`, falló en `mate_in_one` tras el
  cambio y se corrigió para aceptar el valor de mate; esa corrida del benchmark se detuvo y se repitió
  completa con el código final.
- **Lección:** al convertir entre escalas hay que revisar los extremos (terminales), no solo el centro.

#### M-13 · Hallazgo del benchmark: los «aciertos» del mate en dos con 50 simulaciones son un desempate
- **Qué se observó:** con `captures_L4`, T9/T10 (mate en dos con sacrificio de torre) aciertan 3/5 y 4/5
  semillas con 50 simulaciones y **0/5 con 200, 800 y 2000**. Son los 7 casos no monótonos de esa
  configuración (`mcts_non_monotonic_cases`).
- **Diagnóstico (árbol inspeccionado, T9, semilla 0):** con 50 simulaciones y 25 jugadas legales cada hijo
  de la raíz recibe exactamente 2 visitas (`visit_share` = 0.04 para todos); decide el desempate por valor
  medio, y el sacrificio d3d8 tiene 1.0 porque, tras la única respuesta c8d8, el rollout con sesgo a
  capturas juega Txd8# con probabilidad alta. Al crecer el presupuesto el árbol expande las 20 jugadas de
  blancas tras c8d8 y promedia todas: con 2000 simulaciones d3d8 tiene 41 visitas, el nodo c8d8 40 visitas
  repartidas en 20 hijos (~2 cada uno) y valor medio 0.52, así que pierde frente a jugadas tranquilas
  (d2d1 con 105 visitas y 0.755).
- **Consecuencia:** el acierto con 50 no indica que el agente «vea» el mate; es un artefacto de la regla
  final con visitas empatadas. Se informa así en `apuntes/05c_mcts.md`.

---

## Etapa 7 — Cuaderno, README y entrega (prefijo N-)

---

#### N-01 · El cuaderno se construye desde el enunciado del primer commit
- **Decisión:** `tools/construir_cuaderno.py` lee el `.ipynb` del primer commit con `git show`, conserva sus 28 celdas (falla si no son 28) e inserta módulos, celdas propias y apuntes según un `PLAN` por índice de celda.
- **Alternativas:** editar el cuaderno a mano; partir del cuaderno ya construido.
- **Por qué:** es idempotente (reconstruir no duplica nada) y garantiza que el enunciado y el pseudocódigo siguen intactos. Es el esquema del Taller 2.
- **Consecuencia:** cualquier cambio se hace en `chess_ai/`, `celdas/` o `apuntes/` y se reconstruye.

#### N-02 · Choques de nombres: módulo contra módulo y celda propia contra módulo
- **Decisión:** el constructor falla si dos módulos definen el mismo nombre de nivel superior **o** si una celda de `celdas/` redefine uno. Las variables de las celdas propias llevan prefijo `_`.
- **Por qué:** al concatenar en un solo espacio de nombres, una redefinición tapa a otra en silencio (una demo podría cambiar lo que usa el torneo).
- **Consecuencia:** también se eliminan los bloques `if __name__ == "__main__":`, que en un cuaderno sí se ejecutarían.

#### N-03 · Arquitectura después del contrato, no antes
- **Decisión:** `04_arquitectura.md` y `environment` van después de la celda 8 (contrato) y no después de la 7, como sugería el plan inicial.
- **Por qué:** el texto dice que `SearchStats`, `Decision` y `Agent` son «los de la celda anterior»; así es verdad.

#### N-04 · Celdas de demostración que solo afirman invariantes
- **Decisión:** las demos de cada implementación y las 7 pruebas de §8 usan `time_limit_s=0` o simulaciones fijas para todo lo que se afirma con `assert`. Lo que depende del reloj (profundidad alcanzada con 0,2 s) solo se imprime.
- **Por qué:** lección de S-17: una prueba de reloj falla según la carga de la máquina.
- **Consecuencia:** el cuaderno pasa igual con la máquina cargada (el torneo corría en paralelo).

#### N-05 · Experimentos largos: se cargan; Exp. 1 y una partida se repiten en vivo
- **Decisión:** el Exp. 1 se re-ejecuta y se compara fila a fila (valor y nodos) con `resultados/exp1_ahorro.csv`. Torneo, ablación y Exp. 4 se cargan de `resultados/`, y se repite en vivo una muestra del Exp. 4 y una partida corta. `EJECUTAR_COMPLETO = False` permite repetir el torneo en el cuaderno.
- **Alternativas:** repetir todo (horas); solo mostrar imágenes PNG.
- **Por qué:** el cuaderno debe correr en minutos y demostrar que los archivos salen de este mismo código. Las figuras se regeneran desde los CSV, no desde imágenes.
- **Consecuencia:** si faltan los archivos, las celdas avisan en vez de fallar; basta reconstruir y ejecutar cuando existan.

#### N-06 · Cifras que el constructor calcula en vez de escribirse a mano
- **Decisión:** el número de pruebas de la suite (`{{N_PRUEBAS}}`) se cuenta con `pytest --collect-only` al construir; `{{Q10}}` se reemplaza por `apuntes/12_q10.md` si existe.
- **Por qué:** un número escrito a mano queda desactualizado cuando se agregan pruebas.

#### N-07 · El constructor no aborta si falta un archivo del plan
- **Decisión:** los faltantes (resultados del otro frente de trabajo) se avisan al final.
- **Por qué:** el torneo se corría en paralelo; el cuaderno se tiene que poder construir y probar antes.

#### N-08 · Las celdas no muestran rutas personales
- **Decisión:** la celda de entorno imprime solo el nombre del entorno virtual (`sys.prefix`), no la ruta completa; README y apuntes usan `<usuario>`.
- **Consecuencia:** queda una ruta personal en `apuntes/bitacora_D.md` (D-03), y por eso también en `BITACORA.md`; se reportó para corregirla en esa bitácora.

#### N-09 · Posiciones de prueba propias verificadas por el programa antes de fijarlas
- **Decisión:** las dos posiciones de reglas (captura al paso ilegal por clavada; enroque corto prohibido) se comprueban con `is_valid()` y con `legal_moves` dentro de la celda.
- **Por qué:** lección de S-16 e I-14: una posición «conocida» también se verifica.
