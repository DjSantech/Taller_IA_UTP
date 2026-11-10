### 5A. Agentes básicos: Aleatorio y Voraz de un ply

Implementamos los dos agentes básicos en `chess_ai/agents_basic.py`. Ambos cumplen el contrato
común `choose(board, *, time_limit_s, seed) -> Decision`, reciben una copia del tablero con su
historia y la devuelven intacta, y devuelven `move=None` **solo** cuando el estado ya es terminal
según `search_outcome` (en ese caso `score` es la utilidad exacta desde el jugador al turno: en la
posición `checkmate` del enunciado, negras reciben `-MATE_SCORE`).

**Aleatorio.** Elige uniformemente entre las jugadas legales con `random.Random(seed)`. Antes de
muestrear ordenamos las jugadas por su cadena UCI: así la jugada que sale depende solo de la
posición y de la semilla, y no del orden interno del generador de `python-chess`. No evalúa
posiciones, por eso su `score` es `None` y sus contadores de nodos y hojas son 0. Es la línea base
del torneo y la herramienta para estudiar el efecto de las semillas. Comprobamos que con 2000
semillas en la posición inicial aparecen las 20 jugadas y ninguna sale más del triple de veces que
la menos frecuente (prueba `test_random_agent_depends_on_seed_and_covers_all_moves`).

**Voraz de un ply.** Para cada jugada legal (en orden UCI) hacemos `push`, valoramos el sucesor y
hacemos `pop` dentro de un bloque `finally`. La valoración resuelve primero los terminales: un mate
inmediato vale `MATE_SCORE − 1` y domina a cualquier estimación; las tablas valen 0. Solo si el
sucesor no es terminal consultamos `E(s)`, que está desde blancas; el valor se multiplica por
`perspective_sign` del color que decide y se maximiza. Por eso, cuando juegan negras, el voraz
prefiere los valores de `E` más bajos, que son los buenos para negras (prueba con una posición
propia en la que negras ganan la dama con `Cxd5`). Los empates (valores a menos de `1e-9` del
máximo) se resuelven al azar con la semilla de la llamada: es reproducible y evita que en posiciones
tranquilas juegue siempre «la primera jugada de la lista». Métricas: `nodes` = sucesores generados,
`leaves` = sucesores valorados, `completed_depth = 1` si alcanzó a valorarlos todos. El plazo es
cooperativo: si vence, devuelve la mejor jugada vista hasta ese momento.

**Resultados.** En 10 partidas Voraz (E0) contra Aleatorio, cinco con cada color, semillas 0–9,
plazo de 0,2 s por decisión y límite de 160 plies, el voraz ganó 9 por mate y hubo 1 tablas por
repetición triple (duración media: 57,4 plies). El voraz tardó en promedio 11,1 ms por decisión
(máximo 87 ms) y generó en promedio 42 sucesores por decisión; el aleatorio, 0,13 ms. Repetir la
partida de la semilla 0 dio exactamente la misma partida (`1-0`, mate en el ply 81).

La partida en tablas es instructiva: negras (el voraz) tenían más de 34 peones de ventaja (dos
caballos, dos alfiles y una torre contra torre y peones), pero el voraz no sabe dar mate si el mate
está a más de un ply. Movía el rey de un lado a otro porque todas esas jugadas valían lo mismo para
`E`, y la política de reclamo automático del taller (`outcome(claim_draw=True)`) terminó la partida
en cuanto negras **podían** reclamar una repetición triple, aunque el voraz nunca habría elegido la
jugada que repite (para él valdría 0, mucho menos que su ventaja). Es el límite del horizonte de
un ply, no un error de las reglas.

**Dónde falla el voraz (pregunta 1 de la sustentación).** Dejamos documentada la posición
`GREEDY_TRAP_FEN = "4r1k1/1p3ppp/1Q6/8/8/8/5PPP/6K1 w - - 0 1"`. Negras amenazan `...Te1#` (mate
del pasillo: el rey blanco está encerrado por sus propios peones). El voraz juega `Dxb7` porque
gana un peón (valor `+430` cp desde blancas) y no ve la respuesta `...Te1#`. Un minimax de
profundidad 2 genera esa respuesta, ve que tras `Dxb7` llega un mate y elige una defensa: con E0 un
minimax-2 de comprobación escogió `Db4`, que cubre e1. La prueba
`test_greedy_falls_into_back_rank_trap` verifica que el voraz cae con cinco semillas y que `Te1` da
mate.
