### MCTS-UCT: diseño y Experimento 4

Implementamos MCTS-UCT en `chess_ai/mcts.py` (`MCTSAgent`). Cada simulación recorre los cuatro
pasos de AIMA: **selección** con UCT entre hijos de nodos totalmente expandidos, **expansión** de una
sola jugada no explorada, **simulación** (rollout) y **retropropagación**.

**Perspectiva.** Cada nodo acumula su recompensa W desde el jugador que hizo la jugada que lleva a él.
Así, cuando UCT elige entre los hijos de un nodo, maximiza `W/N + c·sqrt(ln N_padre / N_hijo)` para el
jugador que está al turno en ese nodo: blancas maximizan para blancas y negras para negras. La
recompensa se calcula una vez desde blancas y el método `_reward_for` la convierte para cada nodo
(`r` o `1 − r`). Lo comprobamos con una variante defectuosa que guarda todo desde blancas: con negras al
turno, en un mate en uno (Ta1#) y en una dama colgada, el agente correcto acierta y el defectuoso falla
con las mismas semillas. También observamos que la variante «todo desde el jugador raíz» (suponer que el
rival colabora) eligió las mismas jugadas que el agente correcto con ≤ 800 simulaciones: casi ningún hijo
de la raíz llega a tener todas sus respuestas expandidas, así que los valores de los nietos aún no deciden.
Por eso un acierto en el benchmark no basta para validar la perspectiva.

**Recompensa.** Terminal (con `search_outcome`): victoria 1, tablas 0.5, derrota 0. Si el rollout
llega al límite sin terminar, la recompensa es `1/(1 + e^(−E/400))`, con E la evaluación común desde
blancas: un peón de ventaja vale 0.56, una dama 0.905, y nunca 1, que se reserva para la victoria real.
Esos rollouts se cuentan como **truncados**, separados de las tablas (`last_info["truncated_rollouts"]`).

**Política y límite de rollout.** Por defecto, 4 plies con sesgo a capturas: con probabilidad 0.75 se
elige al azar entre las capturas disponibles; si no, una jugada legal uniforme. La elegimos midiendo:
el rollout uniforme de 8 plies acertaba menos y costaba el doble. También ofrecemos `rollout_limit=0`,
que puntúa la hoja directamente con la sigmoide de E.

**Regla final y puntaje.** Se juega el hijo de la raíz con más visitas; si hay empate, el de mayor valor
medio y, después, el de menor UCI. `Decision.score` convierte el valor medio q del hijo elegido (la
probabilidad estimada de ganar del jugador raíz) a centipeones con la inversa de la sigmoide,
`400·ln(q/(1−q))`, para usar la misma escala que minimax. Si el hijo elegido es un mate inmediato se
reporta `MATE_SCORE − 1`.

**Presupuesto y reproducibilidad.** Con `simulations=N` y la misma semilla, el árbol, las visitas y la
jugada son idénticos. Con `simulations=None` se usa el plazo del contrato, revisado antes de cada
simulación. Ese modo depende de la máquina y de su carga: con 0.2 s y la misma semilla hicimos entre 339
y 510 simulaciones en la posición inicial (10 corridas) y entre 221 y 460 en una posición de medio juego.
El tablero se restaura contando los `push` de cada simulación y deshaciéndolos en un `finally`. Esta
opción fue un poco más rápida que copiar el tablero en cada simulación (3220 frente a 3114
simulaciones/s en la posición inicial; 1752 frente a 1737 en medio juego), aunque la diferencia queda
dentro del ruido.

#### Rendimiento (simulaciones por segundo, 1000 simulaciones, media de 3 semillas)

| Configuración | Posición inicial | Medio juego (14 plies) |
|---|---:|---:|
| capturas, L4 (por defecto) | 3220 | 1752 |
| sin rollout, L0 | 6345 | 3497 |
| uniforme, L4 | 2764 | 1705 |
| uniforme, L8 | 1420 | 1423 |

Con el plazo del torneo (0.2 s) caben unas 380–415 simulaciones en promedio con la configuración por
defecto (rango observado 221–510). Las mediciones se hicieron con otros procesos del taller en
ejecución, así que el tiempo tiene ruido apreciable.

#### Experimento 4: tácticas × presupuesto × semilla

Diez tácticas (`MCTS_TACTICS`, con blancas o negras al turno), cuyo conjunto de jugadas correctas se
recalcula con las reglas de python-chess: 4 mates en uno, 2 damas colgadas, 2 posiciones de «evitar mate
en uno» (8 de 28 jugadas son correctas en cada una) y 2 mates en dos con sacrificio de torre.
Presupuestos de 50, 200, 800 y 2000 simulaciones; semillas 0 a 4; tres configuraciones. Las 600 filas
están en `resultados/mcts_tacticas.csv`.

| Configuración | Simulaciones | Tasa de acierto | Tiempo medio (s) | Desv. estándar (s) |
|---|---:|---:|---:|---:|
| capturas, L4 | 50 | 0.70 | 0.021 | 0.009 |
| capturas, L4 | 200 | 0.80 | 0.088 | 0.037 |
| capturas, L4 | 800 | 0.80 | 0.351 | 0.119 |
| capturas, L4 | 2000 | 0.80 | 0.840 | 0.304 |
| sin rollout, L0 | 50 | 0.80 | 0.017 | 0.024 |
| sin rollout, L0 | 200 | 0.80 | 0.053 | 0.023 |
| sin rollout, L0 | 800 | 0.80 | 0.242 | 0.127 |
| sin rollout, L0 | 2000 | 0.80 | 0.536 | 0.154 |
| uniforme, L8 | 50 | 0.66 | 0.054 | 0.039 |
| uniforme, L8 | 200 | 0.76 | 0.199 | 0.103 |
| uniforme, L8 | 800 | 0.72 | 0.796 | 0.369 |
| uniforme, L8 | 2000 | 0.80 | 1.841 | 0.807 |

Aciertos por táctica (de 5 semillas) con 50 / 200 / 800 / 2000 simulaciones:

| Táctica | capturas, L4 | sin rollout, L0 | uniforme, L8 |
|---|---|---|---|
| T1–T3 mates en uno (blancas y negras) | 5/5/5/5 | 5/5/5/5 | 5/5/5/5 |
| T4 mate en uno (Dxf7#) | 2/5/5/5 | 5/5/5/5 | 5/5/5/5 |
| T5 dama colgada (blancas) | 4/5/5/5 | 5/5/5/5 | 4/5/5/5 |
| T6 dama colgada (negras) | 1/5/5/5 | 5/5/5/5 | 5/5/5/5 |
| T7 evitar mate (negras) | 4/5/5/5 | 5/5/5/5 | 2/4/2/5 |
| T8 evitar mate (blancas) | 2/5/5/5 | 5/5/5/5 | 2/4/4/5 |
| T9 mate en dos (blancas) | 3/0/0/0 | 0/0/0/0 | 0/0/0/0 |
| T10 mate en dos (negras) | 4/0/0/0 | 0/0/0/0 | 0/0/0/0 |

**Lectura.**
- Las tácticas de un ply (mates en uno y damas colgadas) y las defensas contra un mate en uno se
  resuelven desde 200 simulaciones en las tres configuraciones, salvo el rollout uniforme de 8 plies, cuyo
  ruido hace fallar las defensas incluso con 800 simulaciones.
- En estas tácticas el rollout no mejora la evaluación directa de la hoja: L0 acierta igual o más con
  todos los presupuestos y es más rápido. Lo atribuimos a que el rollout aleatorio añade varianza y E ya
  mide el material.
- Ninguna configuración resuelve los mates en dos con 200 simulaciones o más. Tras el sacrificio de
  torre, el rival tiene una única respuesta y luego hay unas 20 jugadas posibles. UCT promedia esas ramas:
  con 2000 simulaciones el nodo posterior a la respuesta tenía 40 visitas repartidas entre 20 hijos y un
  valor medio de 0.52, por debajo del de jugadas tranquilas (0.755). Minimax tomaría el mínimo y vería el
  mate a profundidad 3.
- **Una curva media creciente no implica mejora monótona por semilla, y nuestros datos lo muestran.**
  Con capturas y L4, la tasa media sube de 0.70 a 0.80 y luego se mantiene. Sin embargo, 7 pares
  (táctica, semilla) acertaron con 50 simulaciones y fallaron con todos los presupuestos mayores (T9 y T10,
  secuencia 1→0→0→0). Además, los aciertos con 50 simulaciones son un artefacto del desempate: los 25
  hijos de la raíz tenían exactamente 2 visitas y ganó el de mayor valor medio, porque el rollout con
  sesgo a capturas encontraba Txd8# por casualidad. Con el rollout uniforme L8, T7 dio las secuencias
  0→1→0→1 (semilla 0) y 1→1→0→1 (semilla 1), y T8 dio 1→1→0→1 (semilla 4). En esa configuración la media
  baja de 0.76 (200) a 0.72 (800) antes de subir a 0.80.
