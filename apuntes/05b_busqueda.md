### Búsqueda adversaria: minimax, alfa-beta y alfa-beta mejorado (implementaciones B y C)

El código está en `chess_ai/search.py`. Implementamos los tres agentes de búsqueda sobre el mismo núcleo y con las mismas convenciones que el resto del taller (bitácora D-06 a D-10 y S-01 a S-18).

**Perspectiva.** Implementamos minimax con MAX = **blancas** y MIN = **negras**, con dos ramas explícitas como en el pseudocódigo (no negamax). Todos los valores del árbol están desde blancas: la evaluación E(s) y las utilidades terminales `±(100000 − ply)`. Solo al final convertimos el valor de la raíz a la perspectiva de quien decide (`Decision.score`). Cuando juegan negras, la raíz es un nodo MIN y el agente minimiza E, que es lo mismo que maximizar −E: por eso «la evaluación de negras favorece a negras».

**Qué contamos.** Usamos las mismas definiciones en minimax y en alfa-beta, para que los números se puedan comparar:

| Término | Definición |
|---|---|
| Nodo | cada llamada recursiva sobre una posición, incluida la raíz (se cuenta al entrar) |
| Hoja | nodo donde se devuelve una utilidad terminal exacta o se aplica E porque la profundidad llegó a 0 |
| Poda (`cutoffs`) | **evento** de corte: en MAX `valor ≥ β`, en MIN `valor ≤ α`, con al menos un hermano sin explorar; aparte contamos los hijos omitidos |

**Orden de cada nodo.** (1) contar el nodo; (2) consultar el plazo, si lo hay; (3) comprobar si es terminal **antes** del corte de profundidad; (4) si la profundidad es 0, aplicar E; (5) expandir con `push` y deshacer con `pop` dentro de `finally`, de modo que el tablero recibido queda con el mismo FEN y la misma pila de jugadas aunque salte una excepción o venza el plazo.

#### Minimax y alfa-beta
`MinimaxAgent(depth)` recorre el árbol completo hasta la profundidad fija. `AlphaBetaAgent(depth, ordering)` recorre **el mismo árbol, con las mismas hojas y la misma E**, pero mantiene α (lo mejor que MAX ya tiene asegurado en la ruta) y β (lo mejor para MIN) y deja de explorar los hermanos restantes cuando la rama ya no puede influir en la raíz. En la raíz la ventana es (−∞, +∞), por eso su valor es exacto: en las pruebas, minimax, alfa-beta natural y alfa-beta ordenado dan **exactamente el mismo número** (comparado con `==`) en 13 posiciones a profundidades 1, 2 y 3.

**¿Por qué pueden elegir jugadas distintas con el mismo valor?** En cada nodo conservamos el *primer* hijo que alcanza el mejor valor. Si dos jugadas empatan, el orden de recorrido decide cuál aparece primero; alfa-beta ordenado recorre en otro orden y puede devolver la otra. Además, alfa-beta devuelve solo cotas para las ramas podadas, así que nunca «ve» el valor exacto de una alternativa que no puede superar a la que ya tiene. Las pruebas comprueban que, cuando las jugadas difieren, cada una alcanza exactamente el valor de la raíz.

**Voraz frente a minimax (pregunta 1).** En `MINIMAX_DEFENSE_FEN = 4r1k1/ppp2pp1/8/4p2p/3N4/8/PPP2PPP/3Q2K1 w` el peón e5 ataca al caballo d4 y el peón h5 está sin defensa. Un voraz de un ply (que es minimax de profundidad 1) elige **Dxh5** (+786.7): gana un peón y no mira la respuesta. Minimax de profundidad 2 calcula que tras Dxh5 negras juegan exd4 (+432.8) y elige **Cf5** (+673.4), que salva el caballo.

#### Una poda real, trazada a mano (pregunta 2)
Registro de `AlphaBetaAgent(depth=2, log_prunes=True)` en orden natural sobre `MINIMAX_DEFENSE_FEN`. Los valores están desde blancas (MAX). La raíz es MAX; sus hijos son nodos MIN de profundidad 1 cuyas respuestas se evalúan con E.

1. La raíz explora sus primeras jugadas en el orden de python-chess: Ce6 vale +330.2 (lo toma la torre) → α = 330.2; Cc6 vale +398.2 (bxc6) → α = 398.2; **Cf5 vale +673.4** → **α = 673.4**. Hasta aquí no hay podas: en la raíz β = +∞.
2. Siguiente hijo de la raíz: **Cf3**, un nodo MIN que recibe α = 673.4, β = +∞. Su primera respuesta, **Rh8**, vale **+669.4**. El registro dice:
   ```
   [MIN ply=1 prof=1] ruta: Nf3
     ventana alfa=+673.4 beta=+inf; explorados: Kh8=+669.4
     corte por Kh8 (valor <= alfa: +669.4); podados (21): Kf8 Kh7 Rf8 Rd8 Rc8 ... a5
   ```
   (El registro usa la notación SAN inglesa de python-chess: K = rey, Q = dama, R = torre, N = caballo; en el texto usamos la española: R, D, T, C.)
3. **Por qué es válida:** el nodo es MIN, así que su valor final será el mínimo de sus hijos, y ya tiene uno de +669.4: valor(Cf3) ≤ 669.4. En la raíz, MAX ya tiene asegurado +673.4 con Cf5. Como 669.4 ≤ 673.4, MAX nunca preferirá Cf3, sin importar lo que valgan las 21 respuestas que no miramos: si alguna vale menos, Cf3 empeora; si vale más, MIN no la elegiría. El valor de la raíz no cambia. De hecho, el valor exacto de Cf3 (calculado aparte con minimax) es +650.7 (tras Td8), todavía menor que 673.4.
4. Otro corte del mismo registro, tras **Dxh5**: el nodo MIN explora Rf8 +785.4, Tf8 +794.7, Td8 +778.7, … y la novena respuesta, **exd4**, vale **+432.8 ≤ α = 673.4** → se podan las 11 jugadas restantes. Este corte es justo la «defensa» que el voraz no ve.

Resultado: la misma jugada (Cf5) y el mismo valor (+673.375) que minimax, con **190 nodos frente a 757**, 29 podas y 567 hijos omitidos.

#### Alfa-beta mejorado: ordenación y profundización iterativa
`AlphaBetaImprovedAgent(max_depth, time_limit_s)` combina:

- **Ordenación de jugadas** (`_search_order_moves`): primero la jugada de la variante principal de la iteración anterior en ese ply; después promociones, capturas por MVV-LVA (víctima más valiosa con el atacante menos valioso), *killers* (dos jugadas tranquilas por ply que ya causaron un corte) y el resto en el orden de generación. Medimos aparte el tiempo de ordenar: entre 5 % y 11 % del total a profundidad 3, a cambio de 32–62 % menos nodos que el alfa-beta natural.
- **Profundización iterativa con plazo**: guardamos primero una jugada legal de respaldo; luego buscamos a profundidad 1, 2, 3… El plazo (`Deadline`) se consulta al **entrar a cada nodo** y antes de empezar cada iteración; si vence, se lanza `SearchTimeout`, los `finally` deshacen todas las jugadas y la iteración incompleta se descarta.

**¿Qué devuelve el programa si vence el plazo durante una iteración? (pregunta 5)** La jugada y el valor de la **última iteración completa**, con `completed_depth` igual a esa profundidad. Si ni siquiera la profundidad 1 terminó, devuelve la jugada de respaldo (la primera según la ordenación), con `score=None` y `completed_depth=0`. Nunca devuelve `None` en una posición no terminal. Ejemplo medido desde la posición inicial con 0.2 s: las iteraciones 1, 2 y 3 terminan (21, 68 y 543 nodos); la 4 se interrumpe tras 596 nodos; el agente devuelve e3 con el valor de la profundidad 3 (+62) y `completed_depth=3`. Los nodos reportados suman todas las iteraciones, incluida la interrumpida, porque es el trabajo realmente gastado.

**Rendimiento.** E cuesta ~165–205 µs por llamada y casi todos los nodos son hojas, así que buscamos a unos 4 500–6 000 nodos/s en medio juego. Con 0.2 s por jugada, minimax y alfa-beta alcanzan profundidad 2, y el mejorado completa 2 (medio juego) o 3 (inicial y finales). Las tablas completas están en la bitácora S-12.

**Quietud (opcional).** Dejamos un parámetro `quiescence=False`. Si se activa, las hojas siguen explorando capturas y promociones antes de aplicar E. No es nuestra mejora oficial (la oficial es el ajuste de pesos) y, si se usa en una ablación, el árbol ya no es el de profundidad fija.
