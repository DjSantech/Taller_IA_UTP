# Bitácora S — minimax, alfa-beta y alfa-beta mejorado (`chess_ai/search.py`)

Formato: **Decisión · Alternativas · Por qué · Consecuencia**. Los errores reales llevan la marca
**ERROR CORREGIDO** (*Qué pasó / Diagnóstico / Corrección / Lección*). Todos los números salen de
ejecuciones reales en el portátil del grupo (Windows 11, Python 3.13.7, python-chess 1.11.2, 12 hilos),
con otros procesos del taller corriendo en paralelo; los tiempos absolutos pueden variar ±30 %.

---

### S-01 · MAX = blancas y MIN = negras, sobre valores desde blancas
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

### S-02 · Definiciones de nodo, hoja y poda (iguales en minimax y alfa-beta)
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

### S-03 · Terminal en la raíz con la política de la partida; dentro del árbol, `search_outcome`
- **Decisión:** antes de buscar, el agente consulta `game_outcome` (reclamo automático, política de la
  partida). Si ya terminó devuelve `Decision(None, utilidad desde quien decide)`. Dentro del árbol usa
  `search_outcome` (D-08), siempre antes del corte de profundidad (D-07), con `MATE_SCORE − ply`.
- **Por qué:** `move=None` solo se permite si el estado YA es terminal según la política acordada.
- **Consecuencia:** en `checkmate` (juegan negras) el score es −100000 y en `stalemate` 0.

### S-04 · Desempate: se conserva el primer mejor hijo
- **Decisión:** el mejor valor se reemplaza solo con `>` (MAX) o `<` (MIN).
- **Consecuencia (pregunta 3):** minimax en orden natural y alfa-beta ordenado pueden devolver jugadas
  distintas con el mismo valor. La prueba de equivalencia no solo compara valores con `==`: verifica
  que cada jugada devuelta alcanza exactamente el valor de la raíz (si difieren, es por empate).

### S-05 · Alfa-beta «fail-soft» y ventana infinita en la raíz
- **Decisión:** cada nodo devuelve su mejor valor aunque salga de (α, β); en la raíz la ventana es
  (−∞, +∞), por lo que nunca hay corte en la raíz y su valor es exacto.
- **Consecuencia:** minimax, alfa-beta natural y alfa-beta ordenado dan **exactamente** el mismo número
  (comparado con `==`, no aproximado) en 13 posiciones × profundidades 1, 2 y 3. Es así porque las
  hojas, E y el orden de suma dentro de E son los mismos; solo cambia cuáles hojas se visitan.

### S-06 · La jugada de la raíz sale de la variante principal (`pv[0][0]`)
- **Decisión:** cada nodo guarda su mejor línea en `ctx.pv[ply]` (tabla triangular); la jugada de la
  raíz es `pv[0][0]`. Así la raíz usa la misma función recursiva que el resto (sin código duplicado).
- **Consecuencia:** la PV completa sirve para ordenar la siguiente iteración (S-07) y para mostrarla.

### S-07 · Ordenación: PV previa > promociones > capturas MVV-LVA > killers > resto
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

### S-08 · Profundización iterativa: dónde se mira el plazo y qué se devuelve
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

### S-09 · Los agentes de profundidad fija ignoran `time_limit_s`
- **Decisión:** `MinimaxAgent` y `AlphaBetaAgent` recorren siempre el árbol completo de su profundidad.
- **Por qué:** su objeto de estudio es el árbol fijo (Experimento 1). El enunciado pide registrar el
  exceso y aplicar una política uniforme: eso lo hace el controlador con `elapsed_s` (D-10).
- **Consecuencia:** hay que elegir su profundidad para el torneo con las mediciones de S-12.

### S-10 · Registro de podas activable (`log_prunes=True`)
- **Decisión:** cada poda guarda un `PruneEvent`: tipo de nodo, ruta SAN desde la raíz, FEN, α y β del
  nodo en el momento del corte, hijos explorados con su valor, jugada causante y hermanos podados.
  `format_prune_event` lo imprime. Apagado por defecto (calcular SAN cuesta).
- **Consecuencia:** el ejemplo trazado a mano de `05b_busqueda.md` sale de este registro. La prueba
  `test_prune_log_events_are_valid_cutoffs` comprueba que cada evento cumple su condición de corte, que
  hay un evento por cada `cutoff` y que activar el registro no cambia valor, jugada ni nodos.

### S-11 · Quietud: opción apagada, no es la mejora oficial
- **Decisión:** `AlphaBetaImprovedAgent(quiescence=True)` extiende las hojas con capturas y promociones
  (stand pat = E). Por defecto `False`. La mejora oficial del grupo es el ajuste de pesos (prefijo T-).
- **Consecuencia:** con quietud el árbol ya no es el de profundidad fija: sus valores no se comparan con
  minimax. Medición real (posición `knight_capture`, profundidad 2): sin quietud elige Cxc6 (−107.5, 89
  nodos); con quietud elige Cf5 (−102.5, 95 nodos). Cada nodo de quietud cuenta como nodo y como hoja.

### S-12 · Rendimiento y profundidad alcanzable en ~0.2 s (dato para el torneo)
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

### S-13 · Propuesta (no aplicada: `evaluation.py` no es de este módulo) para acelerar E
- `_pawn_structure` cuesta ~44 µs por color (~88 de ~165 µs de E): construye la máscara de «peón
  pasado» con bucles anidados en cada llamada. Precomputar `PASSED_MASK[color][casilla]` (128
  bitboards) la dejaría en pocos µs y casi duplicaría los nodos/s.
- `search_outcome` genera las jugadas legales y luego el nodo las genera otra vez (~40–70 µs). Se podría
  reutilizar la lista, pero se mantuvo `search_outcome` por ser la política común (D-08).

### S-14 · Ejemplo de la pregunta 1: `MINIMAX_DEFENSE_FEN`
- `4r1k1/ppp2pp1/8/4p2p/3N4/8/PPP2PPP/3Q2K1 w - - 0 1`: el peón e5 ataca al caballo d4 y el peón h5
  está sin defensa. Minimax de profundidad 1 (= voraz) juega Dxh5 (+786.7); a profundidad 2 ve que
  Dxh5 exd4 vale +432.8 y elige Cf5 (+673.4), poniendo el caballo a salvo. Además se cruzó con
  `GREEDY_TRAP_FEN` del módulo voraz: `MinimaxAgent(depth=1)` da la misma jugada y el mismo score que
  `GreedyAgent` (Dxb7, +430.2) y la profundidad 2 la evita (Db4, +323.7).

### S-15 · Posiciones propias de prueba (sección 8)
- **Mate en dos** `k7/8/2K5/8/8/8/8/7R w`: profundidad 2 no ve mate; profundidad 3 da exactamente
  `MATE_SCORE − 3` y tras la jugada elegida toda defensa permite mate inmediato.
- **Pieza «colgada» defendida** `6k1/pp3ppp/4p3/3n4/8/8/PP3PPP/3Q2K1 w`: el voraz toma Dxd5 (+3.2) y
  pierde la dama tras exd5; minimax de profundidad 2 no la toma.
- **Evasión** `k3r3/8/8/7Q/8/8/8/4K3 w`: en jaque, la mejor evasión es capturar la torre (Dxe8+).
- **Perspectiva** `7k/7p/8/8/Q7/2n5/7P/4K3 b`: negras capturan la dama (Cxa4).

---

### S-16 · ERROR CORREGIDO — la posición de perspectiva daba tablas, no ventaja de negras
- **Qué pasó:** la primera versión de la posición de perspectiva era `7k/8/8/8/Q7/2n5/8/4K3 b`
  (negras capturan una dama con el caballo). Minimax daba Cxa4 pero con valor **−0.0** a toda
  profundidad: la prueba de «negras eligen lo bueno para negras» no tenía con qué discriminar.
- **Diagnóstico:** tras Cxa4 queda rey y caballo contra rey: `search_outcome` lo declara material
  insuficiente (tablas, 0) **antes** de consultar E, como manda D-07. El programa tenía razón.
- **Corrección:** se añadieron peones (h7 y h2): `7k/7p/8/8/Q7/2n5/7P/4K3 b`. Ahora Cxa4 vale +336.5
  desde negras.
- **Lección:** los terminales se resuelven antes que E también en las posiciones de prueba; una
  posición de prueba debe verificarse con el propio programa antes de fijar la expectativa.

### S-17 · ERROR CORREGIDO — expectativa de score mal calculada y prueba dependiente del reloj
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

### S-18 · ERROR CORREGIDO — doble conteo del nodo de entrada en la quietud (detectado en revisión)
- **Qué pasó:** la primera versión de `_search_quiescence` contaba el nodo «si `ply > 0`», pensando en
  la raíz. Pero la quietud se llama desde una hoja de alfa-beta (que ya contó el nodo y ya miró si era
  terminal), y esa hoja nunca está en `ply` 0: el nodo frontera se contaba dos veces y se miraba dos
  veces si era terminal.
- **Diagnóstico:** revisando el código contra la definición de S-02 antes de ejecutarlo.
- **Corrección:** parámetro `entry=True` en la llamada desde alfa-beta; solo las llamadas recursivas de
  quietud cuentan nodo y miran terminal.
- **Lección:** el conteo de nodos es parte del contrato del experimento; cada función que cuente nodos
  debe revisarse contra la definición escrita.
