# Bitácora X — experimentos y torneo (`chess_ai/tournament.py`, `chess_ai/experiments.py`)

Formato: **Decisión · Alternativas · Por qué · Consecuencia**. Todos los números salen de
ejecuciones reales del 10-11-2026 en el portátil del grupo (Windows 11, Python 3.13.7,
python-chess 1.11.2, 12 hilos lógicos), registradas en `experimentos.log` (no versionado) y en
`resultados/*_config.json`.

---

### X-01 · Cada partida del torneo se juega con `GameController`
- **Decisión:** `play_game` crea un `ChessEnvironment`, aplica la apertura con `env.apply` y juega con
  `GameController.play_until_stop()`. Las filas del CSV salen de `MoveRecord.csv_row` con el estado final.
- **Alternativas:** un bucle propio más simple que llame `agent.choose` directamente.
- **Por qué:** así el torneo usa la misma validación de legalidad, `env.version`, semilla por jugada
  (`base + ply`, G-04), medición de tiempo y marca de exceso (G-05) que la interfaz. Un bucle propio
  sería una segunda implementación de las mismas reglas.
- **Consecuencia:** `torneo_decisiones.csv` tiene exactamente `CSV_FIELDS`; no hubo ninguna partida
  con estado `error` en las 336 partidas jugadas (torneo + ablación).

### X-02 · Aperturas desde la posición inicial, no desde un FEN
- **Decisión:** 16 líneas teóricas (`OPENINGS`, 6–10 plies, todas con blancas al turno); el torneo usa
  las 8 primeras, la ablación las 16. Se juegan desde la posición inicial.
- **Alternativas:** arrancar desde el FEN final de la apertura.
- **Por qué:** con un FEN aislado la historia se pierde (pregunta 7) y el PGN no mostraría la
  apertura. `verify_openings` comprueba legalidad jugada a jugada, `is_valid()` y que la partida siga
  abierta; E0 de las 16 posiciones está entre −28 y +24 cp.
- **Consecuencia:** la columna `ply` incluye la apertura (el ply 1 es de blancas), lo que permite
  deducir quién movió (`decision_mover`). El límite de 160 plies cuenta solo plies de los agentes, para
  que todas las partidas tengan el mismo presupuesto de juego sea cual sea la apertura.
- Se descartó la Petrov (4…Cxe4): alfa-beta a profundidad 3 le daba +364 a blancas (5.De2 clava el
  caballo); no es una posición «equilibrada» para agentes de poca profundidad.

### X-03 · Presupuesto 0.2 s por decisión, tolerancia 0.05 s
- **Decisión:** `time_limit_s = 0.2`, tolerancia del controlador 0.05 s (`DEFAULT_TIME_TOLERANCE_S`).
- **Por qué:** en el piloto (16 aperturas) Minimax d=2 tardó 0.053–0.156 s, Alfa-beta natural d=2
  0.018–0.068 s, el mejorado completó 2–3 plies y MCTS hizo 329–589 simulaciones con 0.2 s. Con ese
  plazo los agentes de profundidad fija casi nunca exceden y el mejorado sí aprovecha el plazo.
- **Consecuencia (torneo):** excesos Minimax 19/1673 jugadas (1.1 %, máx 0.334 s), Alfa-beta 1/1708
  (0.06 %), MCTS 44/2194 (2.0 %, máx 0.353 s: la simulación en curso no se corta), mejorado 0/1718
  (máx 0.2037 s), Voraz y Aleatorio 0.

### X-04 · Minimax y Alfa-beta a profundidad 2; MCTS y mejorado por plazo
- **Decisión:** profundidad 2 para ambos agentes fijos; MCTS con `simulations=None` (plazo); el
  mejorado con profundización iterativa en el plazo.
- **Alternativas:** Alfa-beta a profundidad 3 (aprovecharía la poda, pero tarda 0.04–0.42 s ordenado y
  hasta 0.84 s sin ordenar en el Exp. 1, con muchos excesos); MCTS con simulaciones fijas.
- **Por qué:** el enunciado pide comparar fuerza con presupuesto temporal. A igual profundidad Minimax y
  Alfa-beta devuelven el mismo valor: el torneo comprueba que la poda solo ahorra tiempo
  (Minimax–Alfa-beta 8/16) y deja al mejorado como el agente que convierte ese ahorro en profundidad.
- **Consecuencia:** MCTS no es reproducible jugada a jugada (sus simulaciones dependen del reloj); sí
  lo son las semillas. Se reporta la distribución de simulaciones.

### X-05 · Política uniforme de excesos: aplicar y registrar
- **Decisión:** la del controlador (G-05): si `choose` tarda más de 0.25 s la jugada se aplica igual y
  la fila lleva `time_exceeded = 1`. Se reporta la proporción por agente en la clasificación.
- **Alternativas:** derrota por tiempo; descartar la jugada.
- **Por qué:** cualquier otra política inventaría un resultado; con el plazo cooperativo no se puede
  interrumpir a un agente bloqueado (D-10). Las proporciones medidas (≤ 2 %) muestran que la política
  casi no influyó.

### X-06 · Truncadas fuera de los puntos, sin adjudicación
- **Decisión:** 160 plies de agentes → `truncated`, resultado `*`, sin puntos. `standings` cuenta
  truncadas aparte y reporta cobertura (terminadas/partidas). El material final se guarda
  (`material_white_final`) solo como dato descriptivo, rotulado «no oficial».
- **Consecuencia:** en el torneo no hubo ninguna truncada (216 mates y 24 repeticiones triples), así
  que la clasificación tiene cobertura completa. En la ablación hubo 1 truncada de 96.

### X-07 · Semillas: partida k → 1000·k; jugada → base + ply
- **Decisión:** `seed_base + 1000·k` (torneo base 0, ablación base 500 000). Con el paso 1000 ninguna
  semilla por jugada se repite entre partidas. Todas quedan en `torneo_config.json` (`games_seeds`), en
  el CSV (`seed`) y en el PGN (`SeedBase`, `SeedPolicy`).

### X-08 · Paralelismo medido y descartado para la corrida oficial
- **Decisión:** la corrida oficial se jugó EN SERIE (`--workers 1`); `--workers 4` queda disponible.
- **Qué medimos (`parallel_load_check`, 8 aperturas, 0.2 s):** en serie el mejorado completó 2.56 plies
  de media (2 en 7 casos, 3 en 9) y MCTS 477 simulaciones; con 4 procesos simultáneos, 2.45 plies y
  391 simulaciones (−18 %). El torneo con 4 procesos (120 partidas, 4 aperturas) tardó 135 s y su
  clasificación tuvo el mismo orden de los tres primeros grupos (guardado en
  `resultados/tmp/torneo_paralelo_4w/`, no versionado).
- **Por qué:** la caída de 18 % en simulaciones de MCTS no es grave, pero perjudica solo a los agentes
  por plazo; como la corrida en serie de 240 partidas tarda ~17 min, no hacía falta el paralelismo.
- **Consecuencia:** la clasificación oficial no tiene sesgo de carga; el tiempo es de pared en una
  máquina compartida (otro proceso del taller podía estar activo).

### X-09 · Más partidas que el mínimo: 240 en el torneo
- **Decisión:** 15 pares × 8 aperturas × 2 colores = 240 (mínimo del enunciado 60).
- **Por qué:** el piloto de 120 partidas duró 135 s con 4 procesos; con 16 partidas por par el
  intervalo de un cruce se estrecha (por ejemplo, mejorado contra Minimax 0.66, IC 95 % 0.44–0.84).
- **Duración real:** 1007 s (16.8 min) en serie.

### X-10 · Ablación oficial: E0 contra E* en el mismo agente mejorado
- **Decisión:** `AlphaBetaImprovedAgent` con E0 y con E* (`load_tuned_evaluator()`), 0.2 s, 16 aperturas ×
  2 colores = 32 partidas directas, y ambos contra Minimax d=2 (32 partidas cada uno). 96 partidas,
  1014 s en serie.
- **Rival común:** Minimax, porque en el piloto empataba ~50 % con el mejorado; MCTS habría dado un techo
  (el mejorado le ganó 16/16 en el torneo) y no distinguiría E0 de E*.
- **Resultado:** E* contra E0: 14/31 terminadas (10 V, 8 T, 13 D), puntuación 0.45, IC 95 %
  0.31–0.61. Contra Minimax: E0 0.73 (0.59–0.86), E* 0.67 (0.55–0.78). E* hizo más tablas (15 frente a
  5) y menos derrotas (3 frente a 6).
- **Lectura honesta:** no hay evidencia de que E* juegue mejor; la diferencia directa está dentro del
  ruido y el punto estimado favorece levemente a E0. Coincide con T-09 (mejora de J en prueba 1.3 %,
  no significativa) y con la sospecha de que wa = 0 empobrece el juego.

### X-11 · Ablación de la ordenación con plazo: profundización sin ordenar
- **Decisión:** `_exp_iterative_depth(ordering=False)` repite el bucle del mejorado sin PV previa,
  MVV-LVA ni killers (importa `_search_alphabeta` y `SearchContext`, sin modificar `search.py`).
- **Resultado (9 posiciones):** profundidad media completada con/sin ordenación: 0.05 s 2.00/1.67;
  0.1 s 2.11/2.11; 0.2 s 2.78/2.11; 0.5 s 3.33/2.78; 1.0 s 3.78/3.00.

### X-12 · Las gráficas leen los CSV; el cuaderno no rejuega
- **Decisión:** `make_all_figures`, `load_tournament`, `ablation_load`, `exp4_load` y
  `depth_time_load` leen `resultados/`. Solo el Exp. 1 (12 s) se puede rejugar en vivo; el
  `--rapido` del guion corre todo en 11 s en `resultados/tmp/`.
- **Restricción del cuaderno:** con el código en `__main__`, `run_games` juega en serie aunque se pidan
  procesos (lo avisa).

### X-13 · Hallazgo: la mayoría de las tablas son repeticiones reclamables por el que pierde
- En el torneo hubo 24 tablas, todas por repetición triple (política `claim_draw=True`, E-11). En la
  ablación, 27 de 96. Con agentes de profundidad 2–3 el bando que va perdiendo suele poder repetir;
  esto reduce la diferencia entre agentes fuertes y explica parte de las tablas de E*.

### Observaciones sobre módulos ajenos (no modificados)
- No encontramos errores en `environment`, `evaluation`, `search`, `mcts`, `controller` ni `registry`.
- El mejorado reporta en `SearchStats.nodes` el trabajo de todas las iteraciones, incluida la
  abortada (documentado en `search.py`); por eso sus «nodos medios» en el torneo (2216) no se comparan con
  los de un árbol de profundidad fija.
