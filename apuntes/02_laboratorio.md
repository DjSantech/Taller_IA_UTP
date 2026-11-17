### Nuestras respuestas al laboratorio de observación

**Predicción, antes de ver la animación.** Cuando el caballo retrocede, **desaparece el número más alto del tablero**: el camino pierde su último elemento y la casilla vuelve a estar libre. El caballo queda en la casilla que tenía el número anterior. La celda siguiente lo comprueba sobre `TRAZA_DEMO`.

1. **Primer retroceso: evento 23.**
   - Se libera **(1, 1)** y el caballo vuelve a **(0, 3)**.
   - Antes había **23** casillas visitadas; después hay **22**. El número 23 desaparece del tablero.
2. **Pila de llamadas.** Cada marco es una llamada a BUSCAR, identificada por la última casilla de su camino.
   - **Antes:** `… → (2, 2) → (0, 3) → (1, 1)`. El marco de (1, 1) recorrió sus destinos y no encontró ninguno libre, así que devuelve fracaso.
   - **Después:** `… → (3, 0) → (2, 2) → (0, 3)`. El marco de **(0, 3)** quita (1, 1) del camino y del conjunto, y es el que **elige el siguiente destino** de su lista. Como no le queda ninguno libre, también retrocede (evento 24).
3. **Casilla liberada que reaparece.** (1, 1) se libera en el evento 23 y vuelve a ser destino en el evento 26. Esa segunda visita es válida porque:
   - al retroceder se **desmarcó**, así que ya no pertenece al camino actual;
   - ahora el camino es distinto: se llega a (1, 1) desde (3, 0) y no desde (0, 3).

   Un nodo del árbol es un **camino parcial**, no una casilla. La misma casilla puede aparecer en ramas diferentes.
