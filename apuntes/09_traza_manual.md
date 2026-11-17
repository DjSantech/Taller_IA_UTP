## Traza manual anotada

Este es un fragmento de la traza de **nuestra** ejecución del 5×5 desde (0, 0) con el orden base, del evento 18 al 33. El orden de prueba es `(-1,2) (1,2) (2,1) (2,-1) (1,-2) (-1,-2) (-2,-1) (-2,1)`. «Lista del marco» son los destinos libres de esa casilla en el momento en que se calculan, en ese orden.

| Evento | Tipo | Casilla | Largo | Qué pasa |
|---:|---|---|---:|---|
| 18 | avance | (4, 2) | 19 | El marco de (3, 4) tiene la lista `[(4,2), (2,2)]`: toma la primera. |
| 19 | avance | (3, 0) | 20 | El marco de (4, 2) tiene `[(3,0), (2,1)]`: toma (3, 0). |
| 20 | avance | (2, 2) | 21 | El marco de (3, 0) tiene `[(2,2), (1,1)]`: toma (2, 2). |
| 21 | avance | (0, 3) | 22 | El marco de (2, 2) tiene `[(0,3)]`. |
| 22 | avance | (1, 1) | 23 | El marco de (0, 3) tiene `[(1,1)]`. |
| 23 | retroceso | (1, 1) | 22 | (1, 1) tiene la lista **vacía** y faltan 2 casillas: fracaso. El marco de (0, 3) quita (1, 1); no tiene otra opción. |
| 24 | retroceso | (0, 3) | 21 | El marco de (2, 2) quita (0, 3); su lista se acabó. |
| 25 | retroceso | (2, 2) | 20 | El marco de (3, 0) quita (2, 2). El camino vuelve a tener **las mismas 20 casillas en el mismo orden** que antes del evento 20. |
| 26 | avance | (1, 1) | 21 | El mismo marco de (3, 0) pasa a la **siguiente alternativa** de su lista: (1, 1), que en el evento 23 se había liberado. |
| 27 | avance | (0, 3) | 22 | El marco de (1, 1) tiene `[(0,3)]`. |
| 28 | avance | (2, 2) | 23 | El marco de (0, 3) tiene `[(2,2)]`, y desde (2, 2) no queda nada libre. |
| 29–31 | retroceso ×3 | (2,2), (0,3), (1,1) | 20 | Callejón sin salida otra vez; la lista de (3, 0) ya no tiene más destinos. |
| 32 | retroceso | (3, 0) | 19 | El marco de (4, 2) quita (3, 0). |
| 33 | avance | (2, 1) | 20 | El marco de (4, 2) prueba su segunda alternativa: (2, 1). |

**Invariante comprobado a mano:** en los eventos 25 y 32, el camino es idéntico, en contenido y en orden, al que había antes del avance correspondiente (eventos 20 y 19). `visitadas` coincide con `set(camino)` porque cada `pop` va acompañado de su `remove`.

**Pila:**
- antes del evento 23: `… → (4,2) → (3,0) → (2,2) → (0,3) → (1,1)`;
- después del evento 25: `… → (4,2) → (3,0)`; es el marco de (3, 0) el que elige el siguiente destino.

> Cada integrante rehace a mano un fragmento de la traza durante el laboratorio.
