### 7.A · Microproblema de la torre: búsqueda no informada

**Reglas simplificadas explícitas.** Tablero 8×8 vacío, una sola torre, sin reyes, sin rival y
sin turnos. Opcionalmente hay casillas bloqueadas que la torre no puede ocupar ni saltar. No es
una posición legal de ajedrez, y por eso no usamos python-chess: implementamos el movimiento
desde cero en `chess_ai/rook_problem.py`.

**Formulación (AIMA, cap. 3).**

| Componente | Definición |
|---|---|
| Estado | Casilla de la torre, tupla `(columna, fila)` en 0..7 (a1 = (0,0), h8 = (7,7)) |
| Estado inicial | a1 (también probamos d4) |
| Acciones | `(d, k)`: avanzar k ≥ 1 casillas en la dirección d ∈ {N, E, S, O} sin salir del tablero ni atravesar obstáculos. Orden fijo: N, E, S, O y k creciente |
| Transición | RESULT(s, (d, k)) = s + k·δ(d) |
| Prueba objetivo | la torre está en h8 |
| Costo unitario | c(s, a, s') = 1: cuenta **movimientos** |
| Costo por distancia | c(s, a, s') = k: cuenta **casillas recorridas** |

**Longitud y costo no son lo mismo.** La *longitud* de una ruta es su número de movimientos. El
*costo* es la suma de los c según el modelo que adoptemos. Con costo unitario coinciden; con costo
por distancia no. a1→a8→h8 tiene longitud 2, costo unitario 2 y costo por distancia 14. BFS
optimiza la longitud y UCS optimiza el costo que le demos.

Como en el Taller 1, BFS y DFS comparten un núcleo con la frontera inyectada (FIFO o LIFO),
marcan los estados al generarlos y prueban el objetivo al extraerlos. En DFS los hijos se apilan
invertidos, para que salga primero el de la primera acción (D-17, D-18 y D-19 de aquel taller). UCS
usa un montículo con `best_g` y entradas obsoletas, igual que en el Taller 1 (D-21).

**Resultados reales, a1 → h8 en tablero vacío.** BFS y DFS no usan el costo, así que su ruta es
la misma en los dos modelos.

| Algoritmo | Costo con el que busca | Ruta | Longitud | Costo unit. | Costo dist. | Expandidos | Generados | Frontera máx. |
|---|---|---|---:|---:|---:|---:|---:|---:|
| BFS | — | a1→a8→h8 | 2 | 2 | 14 | 63 | 882 | 56 |
| DFS | — | a1→a2→b2→b3→c3→…→g7→g8→h8 | 14 | 14 | 14 | 14 | 196 | 50 |
| UCS | unitario | a1→a8→h8 | 2 | 2 | 14 | 63 | 882 | 56 |
| UCS | distancia | a1→a8→h8 | 2 | 2 | 14 | 63 | 882 | 43 |

**d4 → h8 (otro origen).**

| Algoritmo | Costo | Ruta | Longitud | Costo unit. | Costo dist. | Expandidos | Generados | Frontera máx. |
|---|---|---|---:|---:|---:|---:|---:|---:|
| BFS | — | d4→d8→h8 | 2 | 2 | 8 | 39 | 546 | 52 |
| DFS | — | d4→d5→e5→e6→f6→f7→g7→g8→h8 | 8 | 8 | 8 | 8 | 112 | 44 |
| UCS | unitario | d4→d8→h8 | 2 | 2 | 8 | 39 | 546 | 52 |
| UCS | distancia | d4→d8→h8 | 2 | 2 | 8 | 63 | 882 | 46 |

**a1 → h8 con 9 obstáculos** (a2, b4, c2, d3, d8, e3, f3, g2, h5). Este es el caso donde
longitud y costo se separan:

```
8 . . . # . . . X        ruta de UCS unitario        ruta de UCS por distancia
7 . . . . . . . .        a1→h1→h3→g3→g8→h8           a1→b1→b3→c3→c4→e4→e8→h8
6 . . . . . . . .        5 movimientos, 16 casillas  7 movimientos, 14 casillas
5 . . . . . . . #
4 . # . . . . . .
3 . . . # # # . .
2 # . # . . . # .
1 T . . . . . . .
  a b c d e f g h
```

| Algoritmo | Costo | Ruta | Longitud | Costo unit. | Costo dist. | Expandidos | Generados | Frontera máx. |
|---|---|---|---:|---:|---:|---:|---:|---:|
| BFS | — | a1→h1→h3→g3→g8→h8 | 5 | 5 | 16 | 54 | 451 | 26 |
| DFS | — | a1→b1→b3→c3→c4→d4→…→g8→h8 | 13 | 13 | 14 | 14 | 119 | 33 |
| UCS | unitario | a1→h1→h3→g3→g8→h8 | 5 | 5 | 16 | 54 | 451 | 26 |
| UCS | distancia | a1→b1→b3→c3→c4→e4→e8→h8 | 7 | 7 | 14 | 54 | 451 | 25 |

Con estas tablas observamos lo siguiente:

- **BFS es óptimo en longitud, no en costo por distancia:** con obstáculos, su ruta de 5
  movimientos recorre 16 casillas, y la más barata recorre 14 con 7 movimientos. Es el mismo
  fenómeno «menos pasos ≠ menor costo» que en el Taller 1 construimos con barro (D-39). Aquí
  aparece sin cambiar los costos de las aristas, solo cambiando lo que medimos.
- **UCS con costo unitario es BFS:** expande los mismos nodos en el mismo orden en los tres
  escenarios (lo comprueba la prueba). Ya lo habíamos predicho y comprobado en el Taller 1 (D-22).
- **DFS no es óptimo y su ruta depende del orden de las acciones.** Con control de repetidos es
  completo, porque solo hay 64 estados, pero devuelve una escalera de 14 movimientos.

| Orden de acciones en DFS | Ruta | Longitud | Expandidos |
|---|---|---:|---:|
| N, E, S, O; k creciente (base) | a1→a2→b2→b3→…→g8→h8 | 14 | 14 |
| N, E, S, O; k decreciente | a1→a8→h8 | 2 | 2 |
| E, N, O, S; k creciente | a1→b1→b2→c2→…→h7→h8 | 14 | 14 |
| S, O, N, E; k creciente | a1→a2→b2→b3→…→g8→h8 | 14 | 14 |

  El óptimo sigue siendo 2 en los cuatro casos. Ordenar distinto cambia **qué** encuentra DFS,
  no lo que existe. La misma idea vuelve a aparecer en 7.B con la ordenación de jugadas en
  alfa-beta.
- **Más costo no significa más trabajo para BFS:** en d4→h8, UCS por distancia expande 63 nodos
  y BFS 39. El costo óptimo es 8 y casi todo el tablero está a distancia ≤ 8, así que UCS tiene
  que vaciar casi toda la cola antes de sacar h8.

#### Por qué una secuencia al objetivo no garantiza mate contra un rival (pregunta 8)

En el microproblema **controlamos todos los movimientos**. El entorno es determinista, de un solo
agente y estático, así que la solución es una **secuencia fija** de acciones: si a1→a8→h8 lleva a
h8, lleva siempre. Con un rival deja de servir lo siguiente:

1. **La solución como secuencia.** Entre cada par de jugadas nuestras, el rival elige su jugada.
   La solución tiene que ser un **plan contingente**: «si responde x, juego y». Eso es la búsqueda
   AND-OR (7.D) o, cuando no podemos llegar a terminales, minimax.
2. **La prueba objetivo «llegar a una casilla».** El mate no es una casilla. Es una propiedad de
   **todas** las respuestas del rival: ninguna jugada legal le saca del jaque. Una ruta que llega
   bien a la meta contra una respuesta puede fallar contra otra. En la posición
   `8/4K3/7k/p7/8/8/6Q1/8`, la secuencia 1.Kf6 Kh7 2.Qg7# es correcta contra Kh7, pero no cubre
   Kh5 ni a4, y nuestro verificador la rechaza.
3. **El costo como suma de pasos.** Lo que se optimiza deja de ser un costo acumulado y pasa a
   ser el **valor minimax**. Una ruta corta no sirve si el rival la puede refutar.
4. **El modelo de transición.** Con un rival, RESULT(s, a) ya no determina el siguiente estado en
   el que volvemos a decidir. Las casillas también pueden quedar bloqueadas o atacadas por las
   piezas del rival, y la torre podría ser capturada.

Lo que **sí** se conserva: la formulación (estados, acciones, prueba terminal), el control de
estados repetidos (en ajedrez con la historia, no con un FEN aislado) y la idea de ordenar para
explorar menos.
