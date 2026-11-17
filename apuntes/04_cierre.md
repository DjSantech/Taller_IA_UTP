### Por qué no hay recorrido cerrado en un tablero impar × impar (Reto 3.3)

Pintamos el tablero como uno de ajedrez: la casilla (f, c) es **clara** si `f + c` es par y **oscura** si es impar. Un salto de caballo cambia la fila en 1 y la columna en 2, o al revés, así que `f + c` cambia en 3 o en 1: **siempre cambia de paridad**. Cada salto pasa de una casilla clara a una oscura o de una oscura a una clara.

Un recorrido cerrado en un tablero de `n²` casillas tiene **`n²` saltos** contando el de regreso. Para volver a la casilla inicial, que es del mismo color con el que empezamos, hace falta un número **par** de cambios de color. Si `n` es impar, `n²` es impar: después de `n²` saltos el caballo está en el color contrario al del inicio, así que no puede estar en el inicio. **Ningún recorrido cerrado es posible.**

**Caso 1×1 cerrado:** el camino `[(0, 0)]` ya cubre el tablero, pero el salto de (0, 0) a (0, 0) no es un salto de caballo, así que el resultado es **fracaso**. La prueba del profesor lo exige.

**Comprobación experimental:** en 5×5 cerrado, con un presupuesto amplio, nuestro solucionador **agota el árbol completo** en 1.735.079 expansiones y devuelve fracaso, como predice la paridad. En 6×6 sí existen recorridos cerrados: desde (1, 1), Warnsdorff encuentra uno en 36 expansiones.
