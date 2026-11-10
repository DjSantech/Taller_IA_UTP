# Bitácora M — MCTS-UCT (`chess_ai/mcts.py`)

Formato: **Decisión · Alternativas · Por qué · Consecuencia**. Los errores reales llevan la marca
**ERROR CORREGIDO** (*Qué pasó / Diagnóstico / Corrección / Lección*). Todos los números vienen de
ejecuciones en la máquina del equipo (Windows 11, Python 3.13.7, python-chess 1.11.2), con otros
procesos del taller ejecutándose a la vez: los tiempos tienen ruido apreciable.

---

### M-01 · W de cada nodo desde el jugador que movió para llegar a él
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

### M-02 · Recompensa en [0, 1]; rollout truncado = sigmoide(E/400), contado como truncado
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

### M-03 · Constante de exploración c = √2
- **Decisión:** `exploration=math.sqrt(2)` por defecto.
- **Alternativas:** ajustar c con las tácticas del benchmark.
- **Por qué:** es la constante de UCB1 para recompensas en [0, 1] (Kocsis y Szepesvári, 2006). Ajustarla
  con las mismas 10 tácticas con las que medimos sería sobreajustar el experimento.
- **Consecuencia:** es un parámetro para modificar en vivo (ver `estudio/M_teoria.md`). M-07 muestra su
  costo: con c = √2 y ~40 respuestas, la refutación se visita poco.

### M-04 · Rollout: sesgo a capturas, límite de 4 plies (decidido por medición)
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

### M-05 · Jugada final: más visitas; desempate por valor medio y luego menor UCI
- **Alternativas:** mayor valor medio; «robust-max» (visitas y valor a la vez).
- **Por qué:** el promedio de un hijo con pocas visitas es poco fiable; las visitas resumen lo que UCT
  aprendió. El desempate en dos niveles hace la decisión determinista.
- **Consecuencia:** `last_info["root_visits"]` permite ver la distribución de visitas que justificó la jugada.

### M-06 · `Decision.score` en centipeones desde el jugador raíz (logit inverso)
- **Decisión:** `score = 400 · ln(q/(1−q))`, q = valor medio del hijo elegido (recortado a ±EVAL_BOUND,
  con q limitado a [1e−6, 1 − 1e−6]). Si el hijo elegido es terminal se reporta su valor exacto:
  `MATE_SCORE − 1` si gana el jugador raíz (mate inmediato), 0 si es tablas. q queda en
  `last_info["win_probability"]`.
- **Alternativas:** reportar q directamente (escala distinta a la de los demás agentes).
- **Por qué:** el controlador y el CSV comparan `score` entre agentes; en centipeones la escala coincide
  con minimax/alfa-beta. Ver ERROR CORREGIDO M-E3.

### M-07 · Prueba de perspectiva y un hallazgo: «todo desde la raíz» no se nota con ≤ 800 simulaciones
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

### M-08 · Restaurar el tablero con push/pop contados (`finally`)
- **Decisión:** cada simulación cuenta sus `push` (selección, expansión y rollout) y los deshace en un
  `finally`. Opción `restore="copy"` trabaja sobre `board.copy(stack=True)` por simulación.
- **Medición** (1000 simulaciones, 3 semillas, simulaciones/s medias): posición inicial push/pop 3220 vs
  copia 3114; medio juego de 14 plies 1752 vs 1737. Diferencia ≤ 3 %, dentro del ruido.
- **Por qué push/pop:** es igual o algo más rápido y no crece con la longitud de la historia; la copia
  copia la pila entera en cada simulación (más cara en partidas largas). Con `finally` el invariante
  se mantiene aunque haya excepción (prueba con un evaluador que lanza error a mitad de un rollout).

### M-09 · Presupuesto: simulaciones fijas (reproducible) o plazo (dependiente de la máquina)
- **Decisión:** `simulations=N` ignora el plazo (N exactas, mismo árbol con la misma semilla);
  `simulations=None` usa `Deadline(time_limit_s)` y se revisa antes de cada simulación; sin ninguno de
  los dos se usan 200 simulaciones. Si el plazo vence antes de la primera simulación se devuelve la
  siguiente jugada del orden barajado (legal) con E como puntaje.
- **Alternativas:** cortar también las simulaciones fijas al vencer el plazo.
- **Por qué:** el enunciado pide simulaciones fijas para reproducibilidad exacta; un plazo depende de la
  máquina. Igual que en D-10, el exceso de un presupuesto fijo lo mide y registra el controlador.
- **Consecuencia:** en el torneo (plazo 0.2 s) MCTS no es reproducible jugada a jugada: con la misma
  semilla hizo entre 339 y 510 simulaciones en la posición inicial (10 corridas).

### M-10 · Orden de expansión: UCI ordenado y barajado con la semilla
- **Decisión:** las jugadas no expandidas se ordenan por UCI (independiente de cómo las genere
  python-chess) y luego se barajan con `random.Random(seed)`; se expande sacándolas del final.
- **Por qué:** sin barajar, las primeras expansiones serían siempre las mismas (sesgo por orden alfabético);
  con la semilla, el resultado sigue siendo reproducible. Prueba: misma semilla → mismas visitas;
  otra semilla → visitas distintas.

### M-11 · Terminales detectados una vez por nodo
- **Decisión:** al crear un nodo se llama a `search_outcome`; si es terminal se guarda la recompensa en
  `node.terminal` y no se generan jugadas. Las visitas posteriores reutilizan ese valor sin rollout
  (se cuentan como `terminal_rollouts`).
- **Consecuencia:** un mate en uno, una vez expandido, devuelve 1 en cada visita y acapara las visitas
  (prueba `test_mate_in_one_with_enough_budget`, 200 simulaciones, 3 semillas).

### M-12 · Conjunto de tácticas verificado por reglas (Experimento 4)
- **Decisión:** `MCTS_TACTICS` tiene 10 posiciones (blancas y negras al turno): 4 mates en uno, 2 damas
  colgadas, 2 «evitar mate en uno» (8 de 28 jugadas correctas en cada una) y 2 mates en dos con
  sacrificio de torre. El conjunto correcto se recalcula con las reglas de python-chess
  (`mcts_tactic_solutions`: dar mate, capturar la dama, no permitir mate en uno, o forzar mate en la
  siguiente jugada contra toda respuesta) y una prueba exige que coincida con el declarado.
- **Por qué:** «no asumir una única mejor jugada» (sección 8): en «evitar mate» hay 8 defensas válidas y
  todas cuentan.

---

## Errores corregidos

### M-E1 · ERROR CORREGIDO — el rollout aleatorio de 8 plies empeoraba la táctica
- **Qué pasó:** la primera versión usaba `rollout_limit=8` por defecto. En la primera corrida del
  benchmark (8 tácticas, 5 semillas) la configuración uniforme L8 acertó 0.825 / 0.95 / **0.90** con
  50 / 200 / 800 simulaciones, mientras que puntuar la hoja directamente con E (L0) acertó 1.00 en los
  tres presupuestos. Los fallos se concentraban en «evitar mate» (T7: 2 de 5 semillas con 800).
- **Diagnóstico:** 8 jugadas al azar cambian el material de forma arbitraria; la señal de la jugada
  candidata se pierde en el ruido, y además cada simulación cuesta ~2× más que con L4.
- **Corrección:** sesgo a capturas y límite 4 (M-04); medido de nuevo: 0.80 a 200 simulaciones, igual que
  L0 sobre las 10 tácticas (con 50 simulaciones L0 sigue siendo mejor: 0.80 frente a 0.70).
- **Lección:** «más rollout» no es «mejor rollout»; la política y el límite se eligen midiendo.

### M-E2 · ERROR CORREGIDO — una prueba de perspectiva que pasaba por suerte
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

### M-E3 · ERROR CORREGIDO — el mate inmediato se reportaba como +5526 cp
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

### M-13 · Hallazgo del benchmark: los «aciertos» del mate en dos con 50 simulaciones son un desempate
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
