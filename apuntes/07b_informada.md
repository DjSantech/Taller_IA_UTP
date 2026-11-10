### 7.B · Búsqueda informada (A* y voraz) y su relación con la ordenación de jugadas

Implementamos UCS, A* y voraz primero-el-mejor sobre un solo núcleo (`_rook_best_first`), con
`best_g` y entradas obsoletas. Solo cambia la prioridad:

| Algoritmo | Prioridad del montículo |
|---|---|
| UCS | (g, orden de inserción) |
| A* | (g + h, h, orden): a igual f, menor h, como en el A* del Taller 2 (A-04) |
| Voraz | (h, orden) |

**Heurísticas y el costo para el que sirven.**

| Heurística | Definición | Costo unitario | Costo por distancia |
|---|---|---|---|
| `h_rook_lines` (consigna) | 0 en h8; 1 si comparte fila o columna; 2 si no | admisible y consistente | admisible y consistente, pero débil |
| `h_manhattan` | \|Δcol\| + \|Δfila\| | **no admisible** (sobreestima) | admisible y consistente |

*Por qué la de la consigna es admisible con costo unitario.* Un movimiento de torre cambia **una
sola** coordenada. Si la torre no está en h8 hace falta al menos 1 movimiento. Si no comparte
fila ni columna con h8, las dos coordenadas son distintas y hacen falta al menos 2. Entonces
h ≤ h\* en todas las casillas. Con obstáculos sigue valiendo, porque los obstáculos solo quitan
movimientos y nunca abaratan el costo real. *Consistencia:* el único caso en que podría fallar
h(s) ≤ 1 + h(s') sería h(s) = 2 y h(s') = 0, es decir, llegar a h8 en un movimiento desde una
casilla que no comparte fila ni columna con h8, y eso es imposible.

*Por qué Manhattan es admisible con costo por distancia.* Un movimiento de k casillas cambia la
distancia Manhattan en a lo sumo k (desigualdad triangular), así que h(s) ≤ k + h(s'). Es decir,
es **consistente** y, como h(h8) = 0, también admisible. Es el mismo argumento que usamos en el
Taller 2 para el MST (A-08): una cota consistente no puede bajar más de lo que cuesta el paso.

*Por qué Manhattan **no** sirve con costo unitario.* En a1, h = 14 y el costo real es 2 (dos
movimientos). Lo verificamos de forma exhaustiva contra h\*, que calculamos con Dijkstra hacia
atrás desde h8. El oráculo es independiente de los buscadores (D-07 del Taller 1).

| Verificación exhaustiva (todas las casillas alcanzables) | Estados | Casillas con h > h\* | Exceso máx. | Transiciones inconsistentes |
|---|---:|---:|---:|---:|
| consigna, costo unitario, tablero vacío | 64 | 0 | 0 | 0 |
| consigna, costo unitario, con obstáculos | 55 | 0 | 0 | 0 |
| Manhattan, costo por distancia, tablero vacío | 64 | 0 | 0 | 0 |
| Manhattan, costo por distancia, con obstáculos | 55 | 0 | 0 | 0 |
| **Manhattan, costo unitario, tablero vacío** | 64 | **60** | **12** | **336** |
| **Manhattan, costo unitario, con obstáculos** | 55 | **51** | **9** | **147** |

**Que sobreestime no basta: hay que ver que cambie la respuesta.** Pusimos un muro en la fila 3
con hueco en b3 (`rook_unit_manhattan_counterexample`):

```
8 . . . . . . . X     BFS / A*(consigna):  a1→b1→b8→h8       3 movimientos (óptimo)
7 . . . . . . . .     A*(Manhattan):       a1→a2→b2→b8→h8    4 movimientos
6 . . . . . . . .
5 . . . . . . . .     en la ruta de A*(Manhattan): h(a1)=14 frente a h*=3;
4 . . . . . . . .     h(a2)=13 frente a 3; h(b2)=12 frente a 2; h(b8)=6 frente a 1
3 # . # # # # # #
2 . . . . . . . .
1 T . . . . . . .
  a b c d e f g h
```

a2 y b1 empatan en f = 1 + 13 = 14, y el orden de las acciones (N antes que E) saca primero a2.
Desde a2, b2 tiene g = 2 y h = 12, así que f = 14 con menor h que b1, y sale antes. Desde b2, b8
tiene f = 3 + 6 = 9, y h8 sale con f = 4. b1, con f = 14, no se vuelve a mirar. La sobreestimación
hace que un paso de más (g + 1) pese menos que la caída de h, y A* se comporta casi como el voraz.
A* con la h de la consigna, en el mismo tablero, devuelve los 3 movimientos.

**Resultados reales: A* y voraz con la heurística adecuada a cada costo.**

| Escenario | Costo | Algoritmo | Ruta | Longitud | Costo unit. | Costo dist. | Expandidos | Generados | Frontera máx. |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| a1→h8 | unitario | A*(consigna) | a1→a8→h8 | 2 | 2 | 14 | 2 | 28 | 20 |
| a1→h8 | unitario | Voraz(consigna) | a1→a8→h8 | 2 | 2 | 14 | 2 | 28 | 20 |
| a1→h8 | distancia | A*(Manhattan) | a1→a8→h8 | 2 | 2 | 14 | 2 | 28 | 20 |
| a1→h8 | distancia | Voraz(Manhattan) | a1→a8→h8 | 2 | 2 | 14 | 2 | 28 | 20 |
| d4→h8 | unitario | A*(consigna) | d4→d8→h8 | 2 | 2 | 8 | 2 | 28 | 20 |
| d4→h8 | distancia | A*(Manhattan) | d4→d8→h8 | 2 | 2 | 8 | 2 | 28 | 20 |
| obstáculos | unitario | A*(consigna) | a1→h1→h3→g3→g8→h8 | 5 | 5 | 16 | 18 | 108 | 13 |
| obstáculos | unitario | Voraz(consigna) | a1→h1→h3→g3→g8→h8 | 5 | 5 | 16 | 13 | 93 | 16 |
| obstáculos | distancia | A*(Manhattan) | a1→b1→b3→c3→c7→h7→h8 | 6 | 6 | 14 | 19 | 127 | 24 |
| obstáculos | distancia | Voraz(Manhattan) | a1→h1→h4→g4→g8→h8 | 5 | 5 | **16** | 6 | 47 | 18 |

![Nodos expandidos](resultados/torre_expansiones.png)

Lectura de la tabla y de la figura:

- **A* expande mucho menos que UCS y da el mismo costo:** en el tablero vacío, 2 nodos frente a
  63 con los dos modelos de costo. Con obstáculos, 18 frente a 54 (unitario) y 19 frente a 54
  (distancia). Con obstáculos y costo por distancia, A* devuelve una ruta distinta de la de UCS
  (6 movimientos frente a 7), pero del mismo costo, 14: hay empates. Las pruebas comprueban que
  A* nunca expande más que UCS.
- **El voraz es el que menos expande, pero no es óptimo:** con obstáculos y costo por distancia
  expande 6 nodos y devuelve 16 casillas cuando el óptimo es 14. En el tablero vacío acierta
  porque la heurística ya lleva directo a la meta.
- **Una heurística admisible más informada expande menos.** Con costo por distancia también es
  admisible la h de la consigna, pero es mucho más débil. En a1→h8 expanden 63 nodos con h = 0,
  60 con la de la consigna y 2 con Manhattan; con obstáculos, 54, 51 y 19. Manhattan **domina** a
  la de la consigna (es ≥ en cada casilla). Es el mismo patrón que vimos en el Taller 2, donde el
  A* con MST expandía entre 2.5 y 300 veces menos que con h = 0, con el mismo costo final.

#### Analogía y diferencias con ordenar jugadas en alfa-beta

**Lo que se parece.** En los dos casos usamos conocimiento del dominio para decidir **qué mirar
primero**. A* saca de la frontera el nodo de menor g + h. Alfa-beta mejorado (`_search_order_moves`)
prueba primero la jugada de la variante principal de la iteración anterior, luego las
promociones, las capturas MVV-LVA y las *killer moves*. En los dos,
una buena guía reduce el trabajo sin cambiar la respuesta, siempre que se respeten las
condiciones de cada algoritmo: el costo óptimo en A*, el valor minimax en alfa-beta. En el
AND-OR de 7.D también ordenamos los jaques primero, por la misma razón.

**Lo que es distinto.**

1. **En A*, la heurística decide qué nodos se expanden.** Los nodos con g + h > C\* no se
   expanden nunca, y por eso la corrección **depende** de que h sea admisible: con Manhattan y
   costo unitario, A* devolvió 4 movimientos en lugar de 3. **En alfa-beta, el orden nunca
   compromete el resultado:** cualquier orden da el mismo valor en la raíz. Un mal orden solo
   poda menos (en el mejor caso se exploran del orden de b^(m/2) nodos; en el peor, b^m).
2. **Ordenar no altera el conjunto de respuestas del rival.** En un nodo MIN, las respuestas
   legales del rival son las que dan las reglas, en el orden que sea. Alfa-beta solo deja de
   mirar una rama cuando las cotas α y β **demuestran** que no puede cambiar la decisión. Es una
   poda exacta, no una estimación. En cambio, A* «descarta» lo que h estima caro, y si h miente
   el descarte es un error.
3. **Alcance de la ordenación.** A* ordena una frontera **global**, con nodos de cualquier
   profundidad. Alfa-beta ordena **localmente** a los hermanos dentro de un recorrido en
   profundidad.
4. **Qué se puede cambiar.** Ordenar en alfa-beta puede cambiar **qué jugada** se devuelve entre
   varias de igual valor (pregunta 3 de la sustentación), pero no el valor. En A*, el desempate
   entre nodos de igual f cambia la ruta, pero no el costo. En el escenario con obstáculos, A* y
   UCS devolvieron rutas distintas del mismo costo, 14.
