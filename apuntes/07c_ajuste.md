### 7C. Búsqueda local para ajustar la evaluación (y mejora adicional elegida)

Elegimos como mejora adicional la **evaluación con pesos ajustados por búsqueda local**, así que
esta implementación (`chess_ai/tuning.py`) cuenta para el apartado 7C y para la mejora con
ablación. La ablación en partidas (alfa-beta con E0 contra alfa-beta con E\*) está en los
experimentos; aquí reportamos el ajuste y la ablación a nivel de la función objetivo.

**Vector de pesos.** $w = (w_m, w_p, w_k, w_a)$ de $E(s)=w_mM(s)+w_pP(s)+w_kK(s)+w_aA(s)$.
Mantenemos $w_m = 100$ fijo: fija la unidad (centipeones). Si $w_m$ también fuera libre,
multiplicar todos los pesos y la escala $K$ por la misma constante daría la misma función
objetivo, y el problema no tendría una solución única. Ajustamos $w_p, w_k, w_a$ dentro de cotas
fijadas de antemano: $w_p, w_k \in [0, 100]$ y $w_a \in [0, 30]$ (ningún término posicional vale
más de un peón por unidad).

**Datos de entrenamiento y prueba.** No usamos ningún motor. Generamos partidas de autojuego
entre jugadores ε-voraces: en cada ply el jugador juega al azar con probabilidad ε (nuestro agente
Aleatorio) y, si no, juega nuestro Voraz de un ply con **solo material**. Cada bando de cada
partida sortea su ε en [0; 0,5], lo que produce desequilibrios y resultados decisivos. Usamos solo
material para que los datos no presupongan los pesos posicionales que vamos a ajustar.

- Entrenamiento: 600 partidas con el generador de semillas 31; prueba: 300 partidas con el
  generador 7919. Una partida va completa a un solo lado.
- Muestreamos una posición cada 3 plies desde el ply 8 y descartamos las partidas truncadas en
  200 plies (no tienen resultado oficial), las posiciones terminales, las posiciones en jaque y
  las que siguen a una captura (cambio de piezas a medias).
- Eliminamos duplicados por FEN (colocación, turno, enroques, al paso) y quitamos de prueba toda
  posición que también esté en entrenamiento.
- Resultado: **13 019 posiciones de entrenamiento** (473 partidas terminadas: 92 ganadas por
  blancas, 102 por negras, 279 tablas; 127 truncadas descartadas) y **6690 de prueba** (246
  partidas: 52, 53 y 141; 54 truncadas). Las posiciones con su etiqueta quedan en
  `resultados/tuning_posiciones.csv`.

**Etiqueta y función objetivo (estilo Texel).** La etiqueta $y$ es el resultado final de la
partida desde blancas (1, 0,5 o 0). Minimizamos sobre entrenamiento

$$J(w) = \frac{1}{n}\sum_i \left(\sigma\!\left(\frac{E_w(s_i)}{K}\right) - y_i\right)^2,$$

con $E_w$ recortada a ±10 000 igual que en `evaluate`. $K$ se calibra una sola vez con los pesos
iniciales y solo con entrenamiento (sección dorada sobre $\log K$, 30 evaluaciones): **K = 1789,5
cp**. Es una escala grande: una dama de ventaja (+900) predice solo un 62 % de puntos, lo que
muestra lo ruidosa que es la etiqueta en juego débil (una posición ganada puede perderse por una
jugada al azar posterior).

**Búsqueda local con presupuesto explícito.** Conectamos con el Taller 2: allí el estado era una
ruta del TSP y el vecino invertía un tramo (2-opt); aquí el estado es el vector de pesos y el
vecino cambia una coordenada.

- *Hill climbing por coordenadas:* evaluamos los vecinos $w_i \pm \text{paso}_i$ (pasos iniciales
  8, 8 y 2) y nos movemos al mejor si mejora estrictamente $J$; si ninguno mejora, reducimos los
  pasos a la mitad, hasta 1/64 del paso inicial.
- *Recocido simulado* (semilla 2026): perturba un peso al azar, acepta empeorar con probabilidad
  $e^{-\Delta/T}$, enfriamiento geométrico; $T_0 = -\text{mediana}(\Delta>0)/\ln 0{,}5$ calibrado
  con 20 vecinos.
- Presupuesto: **300 evaluaciones de J por método**, contando la evaluación inicial y la
  calibración de $T_0$. Regla fijada de antemano: el resultado final es el de menor $J$ de
  **entrenamiento**; los datos de prueba solo se miran después.

El hill climbing llegó a un óptimo local en 135 evaluaciones (22 movimientos aceptados); el
recocido usó las 300 y terminó en $J$ = 0,0444185, igual al del HC hasta el octavo decimal y apenas
peor después. Ganó el HC. El historial de ambos, evaluación por evaluación, está en
`resultados/tuning_historial.csv`.

| | $w_m$ | $w_p$ | $w_k$ | $w_a$ | $J$ entrenamiento | $J$ prueba |
|---|---:|---:|---:|---:|---:|---:|
| Pesos iniciales E0 | 100 | 15 | 10 | 4 | 0,045206 | 0,050634 |
| **Pesos ajustados E\*** (HC) | 100 | **100** | **53,375** | **0** | **0,044418** | **0,049990** |
| Recocido simulado | 100 | 100 | 53,681 | 0 | 0,044418 | 0,049991 |
| Solo material (referencia) | 100 | 0 | 0 | 0 | 0,045297 | 0,051034 |
| Predicción constante 0,487 (referencia) | — | — | — | — | 0,060761 | 0,071802 |

La mejora es de 1,7 % en entrenamiento y de 1,3 % en prueba. $w_p$ quedó en su cota superior: la
restricción está activa y el óptimo sin cotas estaría más arriba.

**Ablación a nivel de objetivo** (devolvemos UN peso del valor ajustado al inicial; el resto queda
ajustado):

| Peso devuelto | Ajustado → inicial | $J$ entrenamiento | $J$ prueba |
|---|---|---:|---:|
| ninguno (E\*) | — | 0,044418 | 0,049990 |
| $w_p$ | 100 → 15 | 0,045018 | 0,050788 |
| $w_k$ | 53,375 → 10 | 0,044435 | 0,049955 |
| $w_a$ | 0 → 4 | 0,044662 | 0,049944 |

En entrenamiento, devolver cualquier peso empeora $J$, como debe ser en un óptimo local. En
prueba solo $w_p$ se sostiene: devolver $w_k$ o $w_a$ a su valor inicial **mejora** levemente la
prueba. Es decir, la mejora que generaliza viene de los peones pasados (en juego débil nadie los
frena y deciden partidas), mientras que los cambios de $w_k$ y $w_a$ se ajustaron a peculiaridades
del entrenamiento. $w_a$ baja a 0 aunque la actividad tiene correlación 0,40 con el resultado,
porque está casi alineada con el material (más piezas implican más casillas atacadas) y, una vez
contado el material, aporta poco.

**¿Cómo sabemos si hubo sobreajuste? (pregunta 9).**
1. Separamos entrenamiento y prueba por partida y por FEN, y elegimos los pesos y el método solo con
   entrenamiento. La prueba nunca intervino en la elección.
2. La mejora aparece también en prueba (−1,3 %), así que no es un efecto exclusivo del
   entrenamiento. Pero es pequeña: en la comparación pareada por partida (la partida es la unidad
   independiente, porque sus posiciones comparten etiqueta) la diferencia media del error es
   −0,00028 con error estándar 0,00056 en 240 partidas, y E\* predice mejor en el 48,75 % de ellas.
   **No es estadísticamente distinguible de cero.**
3. La ablación en prueba muestra un sobreajuste leve de $w_k$ y $w_a$. Calculamos después la
   variante «solo $w_p$ ajustado» (100, 100, 10, 4), que da $J$ de prueba 0,049890, mejor que E\*.
   **No la adoptamos**: elegirla mirando prueba sería justamente usar prueba para ajustar. Para
   hacerlo bien habría que separar una validación dentro de entrenamiento y decidir la regla de
   antemano.
4. Con solo 3 parámetros libres y 13 019 posiciones, el riesgo de memorizar es bajo. El riesgo
   mayor es el **cambio de distribución**: los pesos predicen resultados de partidas entre
   jugadores ε-voraces, no de partidas de alfa-beta. Por eso la evidencia que decide si E\* es
   mejor es la ablación en partidas con presupuesto fijo (experimento 3), no esta tabla.

**Reproducibilidad.** `run_tuning(TuningConfig())` repite toda la corrida (78 s en nuestro
equipo, 76,7 s de CPU; la búsqueda local tarda 0,1 s porque las características se calculan una
vez). Una segunda corrida dio un archivo de posiciones idéntico byte a byte y los mismos pesos y
valores de $J$. Los pesos, la configuración completa, las semillas y las versiones (Python 3.13.7,
python-chess 1.11.2, numpy 2.5.4) quedan en `resultados/pesos_ajustados.json`;
`load_tuned_evaluator()` devuelve `Evaluator(pesos, "E*")` para la ablación en partidas.
