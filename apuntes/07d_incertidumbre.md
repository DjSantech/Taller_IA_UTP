### 7.D · Incertidumbre y garantías

#### D1. Mate forzado como búsqueda AND-OR

En la torre (7.A), la solución era una secuencia porque nosotros movíamos siempre. En una
táctica de mate, el defensor elige entre jugada y jugada. Por eso lo modelamos como AND-OR (AIMA
4.3, `AND-OR-SEARCH`) sobre posiciones **reales** de python-chess:

- **Nodo OR (atacante):** basta **una** jugada que funcione. Probamos las jugadas legales (jaques
  primero, luego capturas, luego el resto) hasta que una tenga plan.
- **Nodo AND (defensor):** el plan tiene que funcionar contra **todas** las respuestas legales. Si
  una sola respuesta no tiene plan, la jugada que llevó a ese nodo no sirve.
- **Éxito:** solo cuando la jugada del atacante da jaque mate. A diferencia del AND-SEARCH literal
  de AIMA, un nodo AND **sin respuestas y sin mate** (ahogado) o una posición de tablas cuentan
  como **fracaso**. Si no lo hiciéramos, el ahogado contaría como «objetivo alcanzado».
- **Profundidad:** `and_or_mate_search(board, n)` profundiza con 1, 2, …, n jugadas del atacante,
  como la profundización iterativa del Taller 1. Así el plan devuelto es el del **mate más
  corto**. Sin profundizar, en el mate en 1 del enunciado y con límite 3, la búsqueda devolvía un
  plan válido pero de 3 jugadas (1.Qe8+ Kh7 2.Qd7+ … 3.Qg7#/Qh3#). Ver ERROR CORREGIDO I-13.

El resultado es un **plan condicional** `{jugada: {respuesta: subplan}}`. Lo comprobamos con
`verify_mate_plan`, que no usa el buscador: recorre el plan con las reglas, exige que cada nivel
AND tenga **exactamente** las respuestas legales y que cada hoja sea jaque mate.

| Posición | FEN | Plan con n=1 | Plan con n=2 | Nodos OR / AND (n=2) | Hojas (mates) |
|---|---|---|---|---:|---:|
| Mate en 1 (sección 8 del enunciado) | `7k/8/5KQ1/8/8/8/8/8 w` | sí | (el de 1) | 1 / 0 | 1 |
| Mate del pasillo | `2r3k1/5ppp/8/8/8/8/3R1PPP/3R2K1 w` | no | sí | 3 / 1 | 1 |
| Rey y dama contra rey y peón | `8/4K3/7k/p7/8/8/6Q1/8 w` | no | sí | 18 / 14 | 3 |

Los nodos cuentan las dos iteraciones (n=1 y n=2). Planes obtenidos (SAN):

```
Mate del pasillo                         Rey y dama contra rey y peón
1. Rd8+   -> 1 defensa(s):               1. Kf6   -> 3 defensa(s):
    si 1... Rxd8:                            si 1... Kh5:
        2. Rxd8#   (mate)                        2. Qg5#   (mate)
                                             si 1... Kh7:
                                                 2. Qg7#   (mate)
                                             si 1... a4:
                                                 2. Qg6#   (mate)
```

**Por qué hay que cubrir todas las defensas.** El segundo plan lo muestra: cada defensa necesita
**un mate distinto**. Probamos dos «planes» incompletos con el verificador:

| Plan propuesto | Veredicto del verificador |
|---|---|
| Secuencia lineal 1.Kf6 Kh7 2.Qg7# | rechazado: «defensas sin cubrir: a5a4, h6h5» |
| 1.Kf6 y 2.Qg7 contra cualquier respuesta | rechazado: tras 1…Kh5, 2.Qg7 no es mate |

Una secuencia que gana contra la respuesta que **nosotros** imaginamos no es una garantía. Si el
rival tiene una sola defensa sin respuesta, el mate no está forzado, y un rival racional elegirá
precisamente esa defensa. Por eso el nodo AND es un «para todo» y el nodo OR un «existe». Es
la misma estructura que minimax con utilidades de solo dos valores (mate / no mate), pero aquí
la salida es el plan completo y no solo un valor.

Sobre la posición del pasillo: la primera versión, con las torres en d1 y e1, **no** era mate en
2, y lo descubrió nuestra propia búsqueda (I-14). La del rey y la dama la hallamos con un
generador aleatorio de posiciones. Que sea mate en 2 lo certifican las pruebas (plan válido con
n=2 y ningún plan con n=1).

#### D2. Un árbol pequeño con azar: expectiminimax frente a minimax

Este ejemplo está **separado del ajedrez**: no cambiamos ninguna regla del ajedrez para meter
dados. Estructura: MAX elige una acción → un nodo de azar (una moneda cargada) → MIN elige una
de dos respuestas → hoja. **Escala de utilidad:** puntos para MAX en [−10, 10] (positivo es bueno
para MAX). **Probabilidades:** resultado favorable 0.75 y desfavorable 0.25. *Minimax* trata el
nodo de azar como si fuera un adversario (peor caso). *Expectiminimax* calcula la esperanza
(AIMA 5.5).

| Acción | Favorable (p=0.75): MIN{…} | Desfavorable (p=0.25): MIN{…} | Expectiminimax | Minimax (peor caso) |
|---|---|---|---:|---:|
| segura | MIN{3, 4} = 3 | MIN{2, 5} = 2 | 0.75·3 + 0.25·2 = **2.75** | min(3, 2) = **2** |
| arriesgada | MIN{6, 8} = 6 | MIN{−4, 0} = −4 | 0.75·6 + 0.25·(−4) = **3.5** | min(6, −4) = **−4** |
| **Decisión** | | | **arriesgada** | **segura** |

Expectiminimax maximiza el resultado **promedio**: acepta un 25 % de perder 4 puntos porque en
promedio gana más. Minimax maximiza el **peor caso**: garantiza al menos 2 contra cualquier
resultado. Ninguno de los dos «se equivoca»: responden preguntas distintas. Si el azar es azar
de verdad, el promedio es lo racional. Si el «azar» es un rival, solo sirve la garantía (D1).

**La escala importa con azar y no importa sin él.** En un segundo árbol (probabilidades 0.9 y 0.1;
utilidades de 1 a 9) aplicamos la transformación monótona no lineal u → 4^u, que conserva el
orden de todas las hojas:

| Acción | Hojas (MIN de cada rama) | Expectiminimax, u original | Expectiminimax, 4^u | Minimax, u | Minimax, 4^u |
|---|---|---:|---:|---:|---:|
| a1 | 0.9 → MIN{2,5}=2; 0.1 → MIN{3,6}=3 | **2.1** | 20.8 | **2** | **16** |
| a2 | 0.9 → MIN{1,7}=1; 0.1 → MIN{4,9}=4 | 1.3 | **29.2** | 1 | 4 |
| **Decisión** | | **a1** | **a2** | **a1** | **a1** |

Minimax solo compara valores, así que una transformación que conserva el orden no cambia su
decisión. Expectiminimax **promedia** valores, y una transformación convexa como 4^u premia la
rama con la hoja alta poco probable. Por eso, con azar, la utilidad tiene que ser una escala con
significado (una utilidad esperada) y no solo un orden de preferencias (AIMA 5.5, fig. 5.12).

#### D3. Kriegspiel: percepción y estado interno

En Kriegspiel cada jugador ve **solo sus propias piezas**. Un árbitro, que ve los dos tableros,
anuncia: si un intento de jugada es «legal» o «ilegal» (si es ilegal, se intenta otra), si hubo
una **captura** y en qué casilla, y si hay **jaque** (y en qué dirección).

**Cómo cambiaría nuestro agente.**

| | Nuestros agentes actuales | Agente de Kriegspiel |
|---|---|---|
| Percepción | el `chess.Board` completo: todas las piezas, turno, enroques, al paso e historia | nuestras piezas + los anuncios del árbitro |
| Estado interno | el tablero exacto (estado físico) | un **estado de creencia**: el conjunto de tableros compatibles con todo lo percibido |
| Actualización | `push` de la jugada | predicción (expandir cada mundo con todas las jugadas rivales posibles) + filtrado (quedarse con los mundos compatibles con el anuncio) |
| Acción | una jugada legal | un **intento**: la respuesta «ilegal» también es información |
| Decisión | minimax / alfa-beta / MCTS sobre un estado | hay que planear sobre conjuntos de estados (AND-OR sobre estados de creencia, o muestrear mundos), con objetivos como «mate con alta probabilidad» |

**Información que nuestros agentes usan y que allí no podrían consultar.** En cada nodo MIN,
alfa-beta llama a `board.legal_moves` para **las jugadas del rival**, y eso exige saber dónde
está cada pieza rival. La evaluación común también lo usa: el término K mira
`board.is_attacked_by(not color, sq)` sobre la zona de nuestro rey. El material M cuenta las
piezas rivales con `board.pieces_mask(pt, color)`, y el término P decide si un peón es pasado
mirando `board.pieces_mask(chess.PAWN, not color)`, es decir, los peones del rival. En Kriegspiel nada de eso es observable: el agente no
sabe si la dama rival está en d8 o ya en h4 atacando f2. Lo mismo pasa con los *rollouts* de
MCTS, que simulan jugadas legales del rival sobre un tablero exacto.

**Cómo crece el estado de creencia** (`kriegspiel_belief_demo`, medido desde la posición inicial,
cuando el árbitro anuncia «sin captura, sin jaque» tras cada jugada negra):

| Paso | Tableros posibles |
|---|---:|
| Inicio | 1 |
| Blancas juegan 1.e4 (la conocen) | 1 |
| Negras responden sin que lo veamos | 20 |
| Blancas juegan 2.Nf3 | 20 |
| Negras responden sin que lo veamos | 266 |

Con solo dos jugadas negras no observadas ya hay 266 tableros posibles, y el crecimiento es
aproximadamente multiplicativo, como el árbol de juego. Los anuncios del árbitro sirven para
recortarlo: si tras 1.e4 y la respuesta oculta blancas **intentan** e4–e5, el árbitro dice
«ilegal» en exactamente 1 de los 20 mundos (cuando negras jugaron …e5) y «legal» en los otros 19.
Un intento fallido es una medición: deja el estado de creencia en un solo tablero.
