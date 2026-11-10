# Bitácora E y T — Agentes básicos y ajuste de pesos (Taller 3)

Formato: **Decisión · Alternativas · Por qué · Consecuencia**. Los errores reales llevan
**ERROR CORREGIDO** (*Qué pasó / Diagnóstico / Corrección / Lección*). Todos los números vienen de
ejecuciones reales (Python 3.13.7, python-chess 1.11.2, numpy 2.5.4).

---

## E — Agentes básicos (`chess_ai/agents_basic.py`)

### E-01 · Ordenar las jugadas por UCI antes de muestrear o desempatar
- **Decisión:** ambos agentes trabajan sobre `sorted(board.legal_moves, key=uci)`.
- **Alternativas:** usar el orden del generador de `python-chess` tal cual.
- **Por qué:** ese orden es determinista hoy, pero es un detalle interno de la biblioteca. Con la
  lista ordenada, la jugada elegida depende solo de (posición, semilla).
- **Consecuencia:** reproducibilidad exacta (misma semilla → misma jugada; prueba
  `test_same_seed_same_move`). La partida Voraz–Aleatorio de la semilla 0 se repitió idéntica
  (`1-0`, mate en el ply 81).

### E-02 · `random.Random(seed)` local en cada llamada
- **Decisión:** cada `choose` crea su propio generador con la semilla recibida; no se usa el
  estado global de `random`.
- **Alternativas:** un generador por agente que avanza entre llamadas.
- **Por qué:** con un generador persistente la jugada dependería de cuántas veces se llamó antes
  al agente (p. ej. tras un «deshacer»). Así la decisión es una función pura de la posición y la
  semilla; el controlador decide qué semilla pasa en cada ply.
- **Consecuencia:** si el controlador pasara la misma semilla en todos los plies, el aleatorio no
  dejaría de ser uniforme por posición, pero sería el mismo «sorteo» repetido; el controlador o el
  torneo deben derivar la semilla del ply.

### E-03 · Estados terminales: `move=None` con la utilidad exacta
- **Decisión:** si `search_outcome(board)` no es `None`, ambos agentes devuelven `move=None` y
  `score = perspective_sign(turno) · terminal_value_white(outcome, 0)`.
- **Alternativas:** `score=None` también en terminales.
- **Por qué:** el enunciado pide «sin decisión nueva, utilidad de derrota para negras» en la
  posición de mate. Con la utilidad exacta el controlador puede mostrarla.
- **Consecuencia:** en `checkmate` ambos agentes devuelven `-MATE_SCORE`; en `stalemate`, 0. En
  estados no terminales el Aleatorio devuelve `score=None` (no evalúa).

### E-04 · Voraz: terminal antes que E, a distancia 1
- **Decisión:** cada sucesor se valora con `terminal_value_white(outcome, 1)` si es terminal y con
  `E` solo si no lo es. El valor desde blancas se multiplica por `perspective_sign` del que decide.
- **Alternativas:** consultar solo `E` (no distingue mate de «mucho material»).
- **Por qué:** D-06 y D-07: los terminales dominan y la perspectiva es única.
- **Consecuencia:** en `mate_in_one` elige `Dg7#` con `score = 99999`; en la posición propia
  `4k3/p7/8/3Q4/8/2n5/7P/4K3 b` (negras) elige `Cxd5` con `score > 0`. Los peones de esa posición
  están para que tras la captura no quede material insuficiente (que sería tablas = 0 y haría la
  prueba ambigua).

### E-05 · Desempate aleatorio con la semilla, con tolerancia 1e-9
- **Decisión:** entre las jugadas a menos de `1e-9` del máximo se elige con `Random(seed)`.
- **Alternativas:** la primera jugada empatada; la última.
- **Por qué:** en posiciones tranquilas muchas jugadas valen lo mismo; tomar siempre la primera
  introduce un sesgo sistemático (p. ej. siempre jugadas de la columna a). La tolerancia evita que
  dos sumas de flotantes iguales en teoría se traten como distintas.
- **Consecuencia:** reproducible por semilla y sin sesgo de orden. Se usa también en el autojuego
  del ajuste, donde da variedad a las partidas.

### E-06 · Métricas del voraz y del aleatorio
- **Decisión:** voraz: `nodes` = sucesores generados (push), `leaves` = sucesores valorados,
  `completed_depth` = 1 si valoró todos. Aleatorio: todo en 0 salvo `elapsed_s`.
- **Por qué:** la raíz no se cuenta como nodo para que «nodos» del voraz coincida con el número de
  jugadas legales; los demás agentes deben declarar su definición para que el torneo no compare
  números incomparables (sección 9).
- **Consecuencia:** en la posición inicial `nodes = leaves = 20`. En 10 partidas contra el
  aleatorio el voraz generó en promedio 42 sucesores por decisión en 11,1 ms.

### E-07 · Plazo cooperativo también en el voraz
- **Decisión:** se revisa `Deadline.expired()` después de cada sucesor; si vence, se devuelve la
  mejor jugada vista y `completed_depth = 0`.
- **Alternativas:** ignorar el plazo (el voraz es barato).
- **Por qué:** el contrato pide devolver la mejor jugada legal disponible al vencer el plazo, nunca
  `None`. Siempre se valora al menos un sucesor.
- **Consecuencia:** con `time_limit_s = 1e-9` devuelve una jugada legal tras 1 nodo (prueba).

### E-08 · El evaluador es cualquier invocable
- **Decisión:** `GreedyAgent(evaluator)` acepta un `Evaluator` o una función `board -> cp`.
- **Por qué:** el ajuste de pesos necesita un voraz «solo material» y la ablación necesita un voraz
  con `E*`, sin subclases nuevas.
- **Consecuencia:** el autojuego de `tuning.py` usa `GreedyAgent(_tune_material_white)`.

### E-09 · Tablero intacto aunque falle el evaluador
- **Decisión:** `push` y `pop` en `try/finally`.
- **Consecuencia:** la prueba `test_greedy_restores_board_even_if_evaluator_fails` usa un evaluador
  que lanza `RuntimeError`: la excepción sale, pero FEN y `move_stack` quedan iguales.

### E-10 · Posición donde el voraz falla (pregunta 1): `GREEDY_TRAP_FEN`
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

### E-11 · Observación: tablas por reclamo automático en una partida ganada
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

## T — Ajuste de pesos por búsqueda local (`chess_ai/tuning.py`, mejora adicional y 7C)

### T-01 · Etiqueta estilo Texel: resultado final de la partida
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

### T-02 · Autojuego ε-voraz con solo material
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

### T-03 · Separación entrenamiento/prueba por partida y por FEN
- **Decisión:** generadores de semillas distintos (`train_seed = 31`, `test_seed = 7919`); una
  partida va entera a un lado; se eliminan duplicados por clave «colocación, turno, enroques, al
  paso» dentro de cada conjunto y se descarta de prueba toda posición que esté en entrenamiento.
- **Alternativas:** mezclar todas las posiciones y partirlas al azar.
- **Por qué:** las posiciones de una misma partida comparten etiqueta y son casi iguales; partirlas
  al azar filtra información de prueba al entrenamiento y hace que prueba parezca mejor de lo que es.
- **Consecuencia:** en la corrida real 23 duplicados eliminados en entrenamiento, 3 en prueba y 1
  posición de prueba descartada por estar en entrenamiento. Prueba de pytest: ningún FEN ni
  `game_id` compartido.

### T-04 · Qué posiciones se muestrean
- **Decisión:** desde el ply 8, una cada 3 plies; se descartan partidas truncadas (sin resultado
  oficial), posiciones terminales, en jaque, o cuya última jugada fue una captura.
- **Por qué:** truncada no es tablas (D-09), así que no tiene etiqueta. E es estática: a mitad de un
  cambio de piezas mide mal el material (filtro de quietud barato, sin búsqueda de quietud).
- **Consecuencia:** 127 de 600 partidas de entrenamiento y 54 de 300 de prueba se truncaron y se
  descartaron. Sesgo asumido: las partidas largas e indecisas quedan subrepresentadas.

### T-05 · wm fijo = 100 y K calibrado una sola vez
- **Decisión:** wm no se ajusta; K se calibra con los pesos iniciales y solo con entrenamiento
  (sección dorada sobre log K en [20; 5000], 30 evaluaciones de J) y queda fijo.
- **Alternativas:** dejar wm libre; reajustar K en cada paso.
- **Por qué:** con wm y K libres, multiplicar todos los pesos y K por la misma constante da el mismo
  J: la escala no está identificada. Fijar wm mantiene la unidad «centipeón».
- **Consecuencia:** K = 1789,5 cp. Es grande: con E = +900 (una dama) la probabilidad predicha
  es solo σ(0,50) ≈ 0,62. Así de débil es la relación entre ventaja y resultado en juego débil.

### T-06 · Hill climbing por coordenadas con reducción de paso
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

### T-07 · Recocido simulado como segundo método, elección por entrenamiento
- **Decisión:** SA con semilla 2026: perturba un peso al azar con U(−paso, paso), Metropolis,
  enfriamiento geométrico hasta T0·10⁻³ al agotar 300 evaluaciones; T0 = −mediana(Δ>0)/ln(0,5)
  con 20 vecinos de calibración que SÍ cuentan en el presupuesto (como en el Taller 2). Regla fijada
  antes de mirar prueba: gana el de menor J de entrenamiento; empate → HC.
- **Por qué:** permite contrastar ambos métodos con el mismo presupuesto, y la regla impide elegir
  con datos de prueba.
- **Consecuencia:** HC llegó a J = 0,0444185 en 135 evaluaciones (óptimo local); SA a 0,0444185
  (ligeramente peor en el 9.º decimal) usando las 300. Ganó HC.

### T-08 · Qué se reporta
- **Decisión:** J de entrenamiento y prueba antes/después, J de referencia (solo material y
  predicción constante), historial por evaluación (`tuning_historial.csv`), ablación por peso
  (devolver UN peso del ajustado al inicial) y una comparación pareada en prueba **agrupada por
  partida** (media de la diferencia de error y su error estándar entre partidas).
- **Por qué:** la partida es la unidad independiente (sus posiciones comparten etiqueta); tratar
  6690 posiciones como independientes exageraría la significancia.

### T-09 · Resultado de la corrida real y lectura honesta
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

### T-10 · `TUNED_WEIGHTS` sale del archivo, no del código
- **Decisión:** `TUNED_WEIGHTS = load_tuned_weights(missing_ok=True)` lee
  `resultados/pesos_ajustados.json` (None si no existe); `load_tuned_evaluator()` devuelve
  `Evaluator(pesos, "E*")`. La ruta es relativa al paquete si existe `__file__` y al directorio de
  trabajo si no (cuaderno).
- **Por qué:** los pesos los produce la corrida real; escribirlos a mano en el código ocultaría de
  dónde salen.
- **Consecuencia:** repetir `run_tuning(TuningConfig())` regenera exactamente los mismos pesos
  (verificado con una segunda corrida completa).

### T-11 · Tiempo de pared vs CPU en el reporte
- **Qué pasó:** la primera corrida real registró `timing_s.data = 34 192 s` (9,5 h) para algo que
  cuesta poco más de un minuto: el equipo se suspendió durante la corrida y `perf_counter` midió el tiempo de
  pared, incluida la suspensión.
- **Decisión:** el JSON guarda ahora también `cpu_data` y `cpu_total` (`time.process_time()`), y se
  repitió la corrida: 78,3 s de pared y 76,7 s de CPU. Las posiciones (archivo idéntico byte a
  byte), los pesos y J coincidieron con la primera, lo que confirma la reproducibilidad.
- **Lección:** un tiempo de pared solo es evidencia si la máquina estuvo dedicada; para el costo
  real de cómputo se reporta CPU.
